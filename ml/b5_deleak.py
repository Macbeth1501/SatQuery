"""Leak-neutral resampling of BigEarthNet.txt choice questions, so the text alone cannot give the answer away.

WHY RESAMPLING, NOT REWRITING. The wrong options of a choice question are not drawn like the right one: the
right option follows the dataset's label frequencies and the wrong ones look evenly drawn (see the progress
log), so an option's identity, or a question's wording, predicts the answer without any image. Filtering on
"the text model got it wrong" would invert that prior (a different shortcut, and a metric that cannot be read).
Rewriting the wrong options needs ground truth we do not hold, because the captions are lossy prose. So this
module keeps the published questions verbatim and only decides WHICH ONES to keep, by raking:

  * every example gets a weight; the weights are adjusted, round after round, until
      - each (category, option text) of a multiple-choice question is correct 1 time in 4 when it is offered,
        and each answer letter is correct 1 time in 4;
      - each (category, word or word pair) of a binary question is answered "yes" half the time when present,
        and each category is half yes;
  * examples are then drawn with probability proportional to their weight.
The chosen set has no first-order lexical signal left for a text-only model to collect. Options that are never
correct (a count of "0", "More than five") get weight near zero, so questions offering them drop out: they are
free wrong answers that no image is needed to eliminate.

The one text edit is "Autumn" -> "Fall" in season options. The dataset's answer key says "Fall" while its wrong
options say "Autumn", so "Autumn" is never correct (a pure lexical leak); after the edit both read "Fall".

Raking removes only the leaks it is told about (single options and single n-grams), so it can leave
interactions. The acceptance gate (`gate`) refits the text-only baseline on the RESAMPLED set with patch-grouped
cross-validation and checks it sits at chance; passing the gate is the claim, not the method.
"""
import re
from collections import defaultdict

import numpy as np
from scipy import sparse

from b5_text_only import answer_letter, is_yes, parse_options

AUTUMN = re.compile(r"\bAutumn\b")
MIN_MASS = 30  # a feature seen fewer times than this is too noisy to rake on
LETTERS = "abcd"


def normalise_season(example):
    """Maps the leaky 'Autumn' distractor to the answer key's 'Fall'. Only season multiple choice is touched."""
    if example["type"] == "mcq" and example.get("category") == "season" and AUTUMN.search(example["question"]):
        example = dict(example, question=AUTUMN.sub("Fall", example["question"]))
    return example


def rake(x, s, target, mask, iterations=250, eta=1.0):
    """Weights making every masked feature's success rate equal `target`.

    x[i, f] = 1 when feature f is present in example i; s[i, f] = 1 when it is present AND counts as a success.
    To lower a feature's rate the weights of its successes are scaled down, to raise it those of its failures
    are; weights only ever shrink, so a feature that is never a success (rate 0, target 0.25) sends its
    examples to weight ~0, which is the intent. An example's update is the MEAN over its features, not the sum:
    a question carries about twenty n-grams, and summing their corrections overshoots and collapses the weights
    onto one answer. Returns (weights in (0, 1], worst remaining |rate - target| among features that kept mass)."""
    x, s = x.tocsr(), s.tocsr()
    fail = x - s
    per_row = np.maximum(np.asarray(x.sum(axis=1)).ravel(), 1.0)
    logw = np.zeros(x.shape[0])
    worst = 1.0
    for _ in range(iterations):
        w = np.exp(logw)
        n = np.asarray(x.T @ w).ravel()
        c = np.asarray(s.T @ w).ravel()
        rate = c / np.maximum(n, 1e-12)
        live = mask & (n >= 5.0)  # a feature whose examples were all weighted away is settled, not unconverged
        worst = float(np.max(np.abs(rate - target)[live])) if live.any() else 0.0
        odds = (target / (1 - target)) * (np.maximum(n - c, 1e-9) / np.maximum(c, 1e-9))
        la = np.clip(np.log(odds), -8.0, 8.0)
        up = np.where(mask, eta * np.minimum(0.0, la), 0.0)   # successes too common -> shrink successes
        down = np.where(mask, eta * np.minimum(0.0, -la), 0.0)  # successes too rare -> shrink failures
        logw += (s @ up + fail @ down) / per_row
        logw -= logw.max()
    return np.exp(logw), worst


def _binary_matrices(examples):
    from sklearn.feature_extraction.text import CountVectorizer

    vec = CountVectorizer(ngram_range=(1, 2), min_df=MIN_MASS, binary=True)
    words = vec.fit_transform([e["question"] for e in examples]).tocsr()
    y = np.array([int(is_yes(e)) for e in examples], dtype=float)
    ones = sparse.csr_matrix(np.ones((len(examples), 1)))
    x = sparse.hstack([ones, words]).tocsr()
    s = x.multiply(y[:, None]).tocsr()
    mask = np.asarray(x.sum(axis=0)).ravel() >= MIN_MASS
    return x, s, mask


def _mcq_matrices(examples):
    keys, rows, cols, succ = {}, [], [], []
    for i, e in enumerate(examples):
        letter = answer_letter(e)
        feats = [(("letter", l), l == letter) for l in LETTERS]
        feats += [((e["category"], text), l == letter) for l, text in parse_options(e["question"])]
        for key, ok in feats:
            j = keys.setdefault(key, len(keys))
            rows.append(i)
            cols.append(j)
            succ.append(1.0 if ok else 0.0)
    shape = (len(examples), len(keys))
    x = sparse.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=shape)
    s = sparse.csr_matrix((succ, (rows, cols)), shape=shape)
    mask = np.asarray(x.sum(axis=0)).ravel() >= MIN_MASS
    return x, s, mask


def weights_for(examples):
    """Raking weights for one homogeneous group of examples (a single type and category). Returns (w, worst)."""
    if not examples:
        return np.array([]), 0.0
    if examples[0]["type"] == "binary":
        x, s, mask = _binary_matrices(examples)
        return rake(x, s, 0.5, mask)
    x, s, mask = _mcq_matrices(examples)
    return rake(x, s, 0.25, mask)


def sample_by_weight(examples, w, n_target, rng):
    """Bernoulli-draws about `n_target` examples, each with inclusion probability exactly proportional to `w`.

    The scale is capped so the heaviest example has probability 1. A group with too little weight to give
    therefore returns FEWER than `n_target` examples instead of topping up with near-zero-weight ones: those
    are the leaky examples raking removed, and letting a quota pull them back in kept `count` and `presence`
    questions at about 30% text-only accuracy in a first trial."""
    if len(examples) == 0:
        return []
    w = np.asarray(w, dtype=float)
    cap = 1.0 / w.max()
    if w.sum() * cap <= n_target:
        scale = cap
    else:
        lo, hi = 0.0, cap
        for _ in range(60):  # bisect the scale so the expected number kept is n_target
            mid = (lo + hi) / 2
            if (mid * w).sum() < n_target:
                lo = mid
            else:
                hi = mid
        scale = hi
    keep = rng.random(len(examples)) < scale * w
    return [e for e, k in zip(examples, keep) if k]


def resample(candidates, n_binary, n_mcq, seed):
    """Rakes each (type, category) group separately and draws its share of the requested sizes.

    Each group gets an equal quota, capped by how much weight it has to give. Returns (kept, report)."""
    rng = np.random.default_rng(seed)
    groups = defaultdict(list)
    for e in candidates:
        e = normalise_season(e)
        groups[(e["type"], e["category"])].append(e)
    per_type = {"binary": [k for k in groups if k[0] == "binary"], "mcq": [k for k in groups if k[0] == "mcq"]}
    kept, report = [], {}
    for qtype, n_total in (("binary", n_binary), ("mcq", n_mcq)):
        cats = sorted(per_type[qtype])
        quota = n_total // max(1, len(cats))
        for key in cats:
            exs = groups[key]
            w, worst = weights_for(exs)
            chosen = sample_by_weight(exs, w, quota, rng)
            kept.extend(chosen)
            report[f"{key[0]}/{key[1]}"] = {"in": len(exs), "effective_n": round(float(w.sum() ** 2 / (w ** 2).sum())),
                                            "kept": len(chosen), "worst_rate_error_after_raking": round(worst, 4)}
    rng.shuffle(kept)
    return kept, report


def gate(examples, tolerance=0.03):
    """Refits the text-only baseline on the resampled set, patch-grouped cross-validation. (passed, summary)."""
    from b5_text_only import out_of_fold

    _, summary = out_of_fold(examples)
    b, m = summary["by_type"]["binary"], summary["by_type"]["mcq"]
    passed = bool(b and m and abs(b["acc"] - 0.5) <= tolerance and abs(m["acc"] - 0.25) <= tolerance)
    return passed, summary

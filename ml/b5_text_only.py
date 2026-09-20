"""Text-only baselines for the BigEarthNet.txt choice questions: what a model can score WITHOUT the image.

    python ml/b5_text_only.py score --train data/b1_slice/train.jsonl --eval data/b1_slice/bench.jsonl \
        --out data/b5_eval/text_only_bench.json
    python ml/b5_text_only.py oof --train data/b1_slice/train.jsonl          # out-of-fold score on the training set

This is the pre-registered baseline for judging any adapter: an adapter has learned to read imagery only to
the extent that it beats these numbers, paired, on the same examples. Nothing here imports torch.

  * binary: logistic regression (C=1.0) on TF-IDF word 1-2-grams (min_df=2) of the question.
  * multiple choice: for each (category, option text), the smoothed rate at which it was the correct option in
    the training set, (times correct + 0.25) / (times offered + 1); the highest-scoring option wins. The margin
    between the best and second-best score is reported so an "unsure" filter can be built from it.

Both are quick baselines, not the best possible text-only model. A stronger one scores higher and shrinks any
lead measured against it. The logged 62.3% (binary) and 40.2% (multiple choice) on the 800-example bench sample
came from an earlier inline version; this script reproduces the binary figure and gives a slightly different
multiple-choice figure (see the progress log for the difference).
"""
import argparse
import collections
import json
import re
from pathlib import Path

OPTION = re.compile(r"(?:^|[,;]\s*|\s)([a-d])\)\s*")
SEED = 20260920


def load_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def parse_options(question):
    """[(letter, option text), ...] from 'Question: a) x, b) y, c) z, d) w'. Empty list if it does not parse."""
    hits = [(m.group(1), m.end(), m.start()) for m in OPTION.finditer(question)]
    out = []
    for i, (letter, start, _) in enumerate(hits):
        if i + 1 < len(hits):
            end = hits[i + 1][2]
        else:
            end = len(question)
        out.append((letter, question[start:end].strip().rstrip(",;").strip()))
    return out


def answer_letter(example):
    return example["answer"].strip().lower()[:1]


def is_yes(example):
    return example["answer"].strip().lower().startswith("y")


# ---- multiple choice ------------------------------------------------------------------------------------

def fit_mcq(train):
    """Counts of how often each (category, option text) was offered and how often it was the correct one."""
    correct, offered = collections.Counter(), collections.Counter()
    for ex in train:
        letter = answer_letter(ex)
        for opt_letter, text in parse_options(ex["question"]):
            offered[(ex["category"], text)] += 1
            if opt_letter == letter:
                correct[(ex["category"], text)] += 1
    return correct, offered


def predict_mcq(model, example, leave_one_out=False):
    """(predicted letter, margin between best and second-best score); (None, 0.0) if the options do not parse."""
    correct, offered = model
    options = parse_options(example["question"])
    if len(options) < 2:
        return None, 0.0
    letter = answer_letter(example)
    scored = []
    for opt_letter, text in options:
        key = (example["category"], text)
        c, n = correct[key], offered[key]
        if leave_one_out:  # the example being scored must not vote for itself
            n -= 1
            c -= int(opt_letter == letter)
        scored.append(((c + 0.25) / (n + 1), opt_letter))
    scored.sort(key=lambda t: (-t[0], t[1]))  # ties break to the earliest letter, deterministically
    return scored[0][1], scored[0][0] - scored[1][0]


# ---- binary ---------------------------------------------------------------------------------------------

def fit_binary(train):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2)
    x = vec.fit_transform([ex["question"] for ex in train])
    clf = LogisticRegression(C=1.0, max_iter=2000).fit(x, [int(is_yes(ex)) for ex in train])
    return vec, clf


def predict_binary(model, examples):
    """Probability of 'yes' for each example."""
    vec, clf = model
    return clf.predict_proba(vec.transform([ex["question"] for ex in examples]))[:, 1]


# ---- scoring --------------------------------------------------------------------------------------------

def score(train, evaluate, leave_one_out=False):
    """Fits on `train`, predicts every choice example in `evaluate`. Returns per-example records and a summary.

    `leave_one_out` (multiple choice only, training set scored against itself) is kept for the original
    inline-comparison numbers; use `out_of_fold` for anything else."""
    train_bin = [e for e in train if e["type"] == "binary"]
    train_mcq = [e for e in train if e["type"] == "mcq"]
    eval_bin = [e for e in evaluate if e["type"] == "binary"]
    eval_mcq = [e for e in evaluate if e["type"] == "mcq"]
    records = []
    if eval_bin:
        probs = predict_binary(fit_binary(train_bin), eval_bin)
        for ex, p in zip(eval_bin, probs):
            pred = "yes" if p >= 0.5 else "no"
            records.append({"id": ex["id"], "type": "binary", "category": ex["category"], "part": ex.get("part"), "pred": pred,
                            "margin": abs(float(p) - 0.5), "correct": pred == ("yes" if is_yes(ex) else "no")})
    if eval_mcq:
        model = fit_mcq(train_mcq)
        for ex in eval_mcq:
            pred, margin = predict_mcq(model, ex, leave_one_out=leave_one_out)
            records.append({"id": ex["id"], "type": "mcq", "category": ex["category"], "part": ex.get("part"), "pred": pred,
                            "margin": margin, "correct": pred == answer_letter(ex)})
    return records, summarise(records)


def out_of_fold(examples, folds=5):
    """Cross-validated score of the baseline on its own data: fit on 4/5 of the PATCHES, score the other 1/5.

    Grouped by patch so questions about one image never sit on both sides. Leave-one-out is deliberately not
    used for multiple choice: once the real signal is near zero it is anti-predictive (an example's own vote is
    removed from the very count that would have favoured it), which scored a balanced set at 0.0%."""
    from sklearn.model_selection import GroupKFold

    records = []
    groups = [e["patch_id"] for e in examples]
    for fit_idx, held_idx in GroupKFold(folds).split(examples, groups=groups):
        recs, _ = score([examples[i] for i in fit_idx], [examples[i] for i in held_idx])
        records.extend(recs)
    return records, summarise(records)


def summarise(records):
    def rate(items):
        return {"acc": sum(r["correct"] for r in items) / len(items), "n": len(items)} if items else None

    out = {"by_type": {}, "by_category": {}}
    for t in ("binary", "mcq"):
        out["by_type"][t] = rate([r for r in records if r["type"] == t])
    for key in sorted({(r["type"], r["category"]) for r in records}):
        out["by_category"][f"{key[0]}/{key[1]}"] = rate([r for r in records if (r["type"], r["category"]) == key])
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("score", help="fit on --train, score --eval")
    s.add_argument("--train", required=True)
    s.add_argument("--eval", required=True)
    s.add_argument("--out", required=True)
    o = sub.add_parser("oof", help="out-of-fold score of the training set against itself")
    o.add_argument("--train", required=True)
    o.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "score":
        records, summary = score(load_jsonl(a.train), load_jsonl(a.eval))
    else:
        records, summary = out_of_fold(load_jsonl(a.train))
    print(json.dumps(summary, indent=1))
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps({"summary": summary, "records": records}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()

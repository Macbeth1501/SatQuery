"""The CPU-side pieces of the ML track: option parsing, the text-only baseline, leak raking, paired testing.

`ml/` is not a package, so its modules are put on sys.path. scikit-learn, scipy and torch are not backend
dependencies; each group of tests skips cleanly when its libraries are missing (they are present in `.venv-ml`).
"""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))

import b5_compare as C  # noqa: E402
import b5_text_only as T  # noqa: E402


def mcq(qid, category, options, answer, patch=None):
    q = "Pick one: " + ", ".join(f"{l}) {t}" for l, t in zip("abcd", options))
    return {"id": qid, "patch_id": patch or f"p{qid}", "question": q, "answer": answer, "type": "mcq",
            "category": category}


# ---- option parsing --------------------------------------------------------------------------------------

def test_parse_options_keeps_commas_inside_an_option():
    q = ("Which climate? a) Cold, no dry season, warm summer, b) Temperate, dry summer, hot summer, "
         "c) Arid, steppe, cold, d) Polar, tundra")
    got = T.parse_options(q)
    assert [l for l, _ in got] == ["a", "b", "c", "d"]
    assert got[0][1] == "Cold, no dry season, warm summer"
    assert got[3][1] == "Polar, tundra"


def test_parse_options_returns_nothing_for_a_binary_question():
    assert T.parse_options("Does the image contain inland waters?") == []


# ---- the multiple-choice baseline ------------------------------------------------------------------------

def test_mcq_baseline_learns_an_option_that_is_always_correct():
    train = [mcq(i, "count", ["1", "2", "3", "4"], "a") for i in range(40)]
    model = T.fit_mcq(train)
    pred, margin = T.predict_mcq(model, mcq(999, "count", ["4", "3", "2", "1"], "d"))
    assert pred == "d" and margin > 0  # "1" sits in slot d here and is the learned favourite


def test_mcq_baseline_leave_one_out_removes_the_examples_own_vote():
    train = [mcq(0, "count", ["1", "2", "3", "4"], "a")]
    model = T.fit_mcq(train)
    _, with_vote = T.predict_mcq(model, train[0])
    _, without = T.predict_mcq(model, train[0], leave_one_out=True)
    assert with_vote > without == 0.0


# ---- the binary baseline and the scoring bookkeeping ------------------------------------------------------

def test_binary_baseline_learns_a_wording_cue():
    pytest.importorskip("sklearn")
    rng = random.Random(0)
    train = []
    for i in range(200):
        exactly = rng.random() < 0.5
        train.append({"id": i, "patch_id": f"p{i}", "type": "binary", "category": "count",
                      "question": "Is it exactly two?" if exactly else "Is it fewer than two?",
                      "answer": "no" if exactly else "yes"})
    records, summary = T.score(train, train)
    assert summary["by_type"]["binary"]["acc"] == 1.0
    assert all("part" in r for r in records)


# ---- raking ----------------------------------------------------------------------------------------------

def leaky_mcq(n, rng):
    """'1' is right 80% of the time it is offered; the other options are right at random."""
    out = []
    for i in range(n):
        opts = rng.sample(["1", "2", "3", "4", "5"], 4)
        ans = opts.index("1") if "1" in opts and rng.random() < 0.9 else rng.randrange(4)
        out.append(mcq(i, "count", opts, "abcd"[ans]))
    return out


def test_raking_removes_an_option_prior():
    pytest.importorskip("scipy")
    pytest.importorskip("sklearn")
    import numpy as np

    import b5_deleak as D

    rng = random.Random(1)
    examples = leaky_mcq(6000, rng)
    before = T.fit_mcq(examples)
    w, worst = D.weights_for(examples)
    assert worst < 0.05
    rate = lambda m: m[0][("count", "1")] / m[1][("count", "1")]  # noqa: E731
    assert rate(before) > 0.5
    kept = D.sample_by_weight(examples, w, 1500, np.random.default_rng(0))
    assert abs(rate(T.fit_mcq(kept)) - 0.25) < 0.06


def test_sampler_never_tops_up_with_zero_weight_examples():
    pytest.importorskip("scipy")
    import numpy as np

    import b5_deleak as D

    examples = [{"i": i} for i in range(100)]
    w = np.array([1.0] * 10 + [1e-9] * 90)
    kept = D.sample_by_weight(examples, w, 60, np.random.default_rng(0))
    assert len(kept) <= 10 + 1


def test_autumn_becomes_fall_only_in_season_questions():
    pytest.importorskip("scipy")
    import b5_deleak as D

    season = mcq(1, "season", ["Winter", "Autumn", "Spring", "Summer"], "a")
    other = mcq(2, "area", ["Autumn", "x", "y", "z"], "a")
    assert "Fall" in D.normalise_season(season)["question"]
    assert "Autumn" in D.normalise_season(other)["question"]


# ---- McNemar ---------------------------------------------------------------------------------------------

def test_mcnemar_matches_a_hand_worked_table():
    # b = 10, c = 2 -> 12 discordant pairs. P(X <= 2) for Binomial(12, .5) = (1 + 12 + 66) / 4096; two-sided doubles it.
    assert C.mcnemar_exact(10, 2) == pytest.approx(2 * 79 / 4096)
    assert C.mcnemar_exact(5, 5) == 1.0
    assert C.mcnemar_exact(0, 0) == 1.0


def test_paired_summary_counts_and_difference():
    a = {i: True for i in range(6)} | {i: False for i in range(6, 10)}
    b = {i: True for i in range(3)} | {i: False for i in range(3, 6)} | {i: True for i in range(6, 8)} | \
        {i: False for i in range(8, 10)}
    out = C.paired(a, b)
    assert (out["only_a_right"], out["only_b_right"], out["both_right"], out["neither_right"]) == (3, 2, 3, 2)
    assert out["diff_a_minus_b"] == pytest.approx(0.1)
    assert out["diff_ci95"][0] < out["diff_a_minus_b"] < out["diff_ci95"][1]


def test_compare_refuses_a_result_without_per_example_records(tmp_path):
    import json

    path = tmp_path / "old.json"
    path.write_text(json.dumps({"accuracy": {}}))
    with pytest.raises(SystemExit):
        C.load_correct(path)


# ---- the strict answer parser ---------------------------------------------------------------------------

def test_answer_parser_reads_bare_and_punctuated_answers_but_not_sentences():
    pytest.importorskip("torch")
    from b5_common import normalise_choice

    assert normalise_choice("Yes", "binary") == "yes"
    assert normalise_choice("  no.", "binary") == "no"
    assert normalise_choice("(b)", "mcq") == "b"
    assert normalise_choice("c) Finland", "mcq") == "c"
    # The evaluation is strict by design (see the progress log): a sentence is unreadable, so counts as wrong.
    assert normalise_choice("There is no instance of industrial areas.", "binary") is None
    assert normalise_choice("The answer is b", "mcq") is None

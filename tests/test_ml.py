"""The CPU-side pieces of the ML track: option parsing, the text-only baseline, leak raking, paired testing,
and the question handling of the model server.

`ml/` is not a package, so its modules are put on sys.path. scikit-learn, scipy and torch are not backend
dependencies; each group of tests skips cleanly when its libraries are missing (they are present in `.venv-ml`).
"""
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ml"))

import b1_v3 as V3  # noqa: E402
import b5_change_rate as R  # noqa: E402
import b5_compare as C  # noqa: E402
import b5_text_only as T  # noqa: E402
import serve_vqa as S  # noqa: E402  (its torch imports are deferred to model loading)


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


# ---- change rate between two runs -------------------------------------------------------------------------

def _result(tmp_path, name, rows):
    import json

    path = tmp_path / name
    path.write_text(json.dumps({"replies": [{"id": i, "type": t, "category": c, "parsed": p} for i, t, c, p in rows]}))
    return path


def test_change_rate_pairs_on_type_and_id_and_ignores_unshared_ids(tmp_path):
    a = _result(tmp_path, "a.json", [(1, "binary", "x", "yes"), (2, "binary", "x", "no"), (9, "binary", "x", "yes")])
    b = _result(tmp_path, "b.json", [(2, "binary", "x", "yes"), (1, "binary", "x", "yes"), (7, "binary", "x", "no")])
    out = R.change_rate(a, b)["all"]
    assert (out["changed"], out["unchanged"], out["pairs"]) == (1, 1, 2)


def test_change_rate_arithmetic_and_per_type_and_category_groups(tmp_path):
    a = _result(tmp_path, "a.json", [(i, "binary", "s", "yes") for i in range(4)] + [(10, "mcq", "t", "a"), (11, "mcq", "t", "b")])
    b = _result(tmp_path, "b.json", [(0, "binary", "s", "no"), (1, "binary", "s", "yes"), (2, "binary", "s", "yes"),
                                     (3, "binary", "s", "yes"), (10, "mcq", "t", "a"), (11, "mcq", "t", "c")])
    out = R.change_rate(a, b)
    assert out["binary"]["change_rate"] == pytest.approx(0.25)
    assert out["mcq/t"]["change_rate"] == pytest.approx(0.5)
    assert out["all"]["change_rate"] == pytest.approx(2 / 6)
    assert out["all"]["ci95"][0] < out["all"]["change_rate"] < out["all"]["ci95"][1]


def test_change_rate_keeps_unreadable_replies_in_their_own_bucket(tmp_path):
    a = _result(tmp_path, "a.json", [(1, "binary", "x", None), (2, "binary", "x", "yes"), (3, "binary", "x", "no")])
    b = _result(tmp_path, "b.json", [(1, "binary", "x", "yes"), (2, "binary", "x", None), (3, "binary", "x", "no")])
    out = R.change_rate(a, b)["all"]
    assert (out["changed"], out["unchanged"], out["unreadable_either_side"]) == (0, 1, 2)
    assert out["change_rate"] == 0.0


def test_change_rate_refuses_a_result_without_per_example_replies(tmp_path):
    import json

    old = tmp_path / "old.json"
    old.write_text(json.dumps({"accuracy": {}}))
    good = _result(tmp_path, "g.json", [(1, "binary", "x", "yes")])
    with pytest.raises(SystemExit):
        R.change_rate(old, good)


# ---- resumable training state -----------------------------------------------------------------------------

def test_training_state_restores_optimiser_batch_order_and_parameters(tmp_path):
    torch = pytest.importorskip("torch")
    import b5_train_lora as L

    def build():
        torch.manual_seed(0)
        model = torch.nn.Linear(3, 1)
        return model, torch.optim.AdamW(model.parameters(), lr=0.1), torch.amp.GradScaler("cuda", enabled=False)

    def train(model, opt, order, cursor, steps):
        for _ in range(steps):
            i = order[cursor]
            cursor += 1
            x = torch.tensor([[float(i), 1.0, 2.0]]) + torch.randn(1, 3) * 0.01  # consumes torch RNG
            opt.zero_grad()
            model(x).pow(2).sum().backward()
            opt.step()
        return cursor

    random.seed(5)
    order = list(range(20))
    random.shuffle(order)

    model, opt, scaler = build()
    cursor = train(model, opt, order, 0, 3)
    L.save_state(tmp_path / "state_step3.pt", opt, scaler, 3, cursor, order, 0, 10)
    weights = {k: v.clone() for k, v in model.state_dict().items()}
    train(model, opt, order, cursor, 4)  # the uninterrupted continuation
    expected = {k: v.clone() for k, v in model.state_dict().items()}
    expected_next = random.random()

    model2, opt2, scaler2 = build()  # a fresh process: new optimiser, weights reloaded from the adapter file
    model2.load_state_dict(weights)
    random.seed(999)
    torch.manual_seed(999)
    step, cursor2, order2, skipped = L.load_state(tmp_path / "state_step3.pt", opt2, scaler2, 10)
    assert (step, cursor2, order2, skipped) == (3, cursor, order, 0)
    train(model2, opt2, order2, cursor2, 4)
    for key, value in expected.items():
        assert torch.equal(model2.state_dict()[key], value)
    assert opt2.state_dict()["state"][0]["step"] == opt.state_dict()["state"][0]["step"]
    assert random.random() == expected_next
    assert L.newest_state(tmp_path) == (tmp_path / "state_step3.pt", 3)


def test_resume_refuses_a_state_from_a_run_of_a_different_length(tmp_path):
    torch = pytest.importorskip("torch")
    import b5_train_lora as L

    model = torch.nn.Linear(2, 1)
    opt = torch.optim.AdamW(model.parameters())
    scaler = torch.amp.GradScaler("cuda", enabled=False)
    L.save_state(tmp_path / "state_step1.pt", opt, scaler, 1, 0, [0], 0, 300)
    with pytest.raises(SystemExit):
        L.load_state(tmp_path / "state_step1.pt", opt, scaler, 100)


# ---- model server question handling (ml/serve_vqa.py) ------------------------------------------------------

def test_server_tells_the_three_question_kinds_apart():
    assert S.question_kind("Do pastures cover at least 90% of the image?") == "binary"
    assert S.question_kind("Is there any urban fabric?") == "binary"
    assert S.question_kind("How much of the scene do arable lands cover? a) 90 to 100%, b) 30 to 60%, "
                           "c) 0 to 20%, d) 60 to 80%") == "mcq"
    assert S.question_kind("Describe the land cover in this image.") == "free"
    # an opener inside a word is not an auxiliary verb
    assert S.question_kind("Island coastlines: describe them.") == "free"


def test_server_does_not_read_requests_as_yes_no_questions():
    # found in the owner's live session: "Do ..." imperatives were answered "No, 92%"
    assert S.question_kind("Do Descriptive analysis") == "free"
    assert S.question_kind("Do change anaylisis") == "free"
    assert S.question_kind("Can you describe the image?") == "free"
    assert S.question_kind("Could you please give a summary of the scene?") == "free"
    # the trained binary forms stay binary, including "Can you detect" and "Would you classify"
    assert S.question_kind("Do broad-leaved forests take up between 0% and 20% of the image?") == "binary"
    assert S.question_kind("Can you detect any marine waters in the image?") == "binary"
    assert S.question_kind("Would you classify arable lands as covering between 10% and 60% of the image?") == "binary"
    # a question typed without "?" still counts when its opener cannot be an imperative
    assert S.question_kind("Is there a river passing through") == "binary"


def test_server_offers_only_the_options_the_question_lists():
    assert S.candidates("Is it wet?", "binary") == ["yes", "no"]
    assert S.candidates("Pick: a) x, b) y, c) z", "mcq") == ["a", "b", "c"]
    assert S.candidates("Describe it.", "free") == []


def test_server_puts_the_option_text_back_beside_its_letter():
    q = "Pick the touching pair: a) Pastures and Permanent crops, b) Arable land and Pastures, c) x, d) y"
    assert S.answer_text(q, "mcq", "b") == "b) Arable land and Pastures"
    assert S.answer_text("Is it wet?", "binary", "no") == "No"
    assert S.answer_text("Describe it.", "free", "Farmland.") == "Farmland."


# ---- b1_v3: caption targets without country, season or climate (ml/b1_v3.py) -----------------------------

CAPTION = (
    'This satellite image, captured during the fall season in Serbia, showcases a predominantly agricultural '
    'landscape within the "temperate, no dry season, hot summer" climate zone. The dominant feature is arable land '
    '(~924,000 sqm). The agricultural areas fall under the broader category of cultivated land. The mix suggests a '
    'diverse landscape, characteristic of Serbia during the fall season.'
)


def test_caption_loses_country_season_and_climate_but_keeps_land_cover():
    new, dropped = V3.rewrite_caption(CAPTION)
    assert new.startswith("This satellite image showcases a predominantly agricultural landscape.")
    assert "~924,000 sqm" in new
    # "fall" as a verb is not a season
    assert "fall under the broader category" in new
    assert dropped == ["The mix suggests a diverse landscape, characteristic of Serbia during the fall season."]
    assert not V3.FORBIDDEN.search(new)


def test_caption_first_sentence_in_the_other_order():
    new, _ = V3.rewrite_caption("This satellite image, captured in Austria during spring, showcases a diverse landscape.")
    assert new == "This satellite image showcases a diverse landscape."


def test_caption_questions_ask_only_for_land_cover():
    for old, new in V3.QUESTION_MAP.items():
        assert not V3.FORBIDDEN.search(new), new
        assert not any(w in new.lower() for w in ("region", "location", "where", "when", "time of year")), new
    with pytest.raises(SystemExit):
        V3.rewrite_question("A prompt nobody mapped.")


def test_only_caption_rows_change_and_images_point_to_the_source():
    rows = [
        {"id": 1, "type": "binary", "question": "Is it summer?", "answer": "no", "image": "images/a.png"},
        {"id": 2, "type": "captioning", "question": "Describe this image in detail.", "answer": CAPTION,
         "image": "images/b.png"},
    ]
    out, report = V3.convert(rows, "../b1_v2")
    assert out[0] == dict(rows[0], image="../b1_v2/images/a.png")  # binary untouched, even when it says "summer"
    assert out[1]["image"] == "../b1_v2/images/b.png"
    assert not V3.FORBIDDEN.search(out[1]["answer"])
    assert report == {"rows": 2, "captions": 1, "dropped_sentences": 1, "dropped_with_area": 0}

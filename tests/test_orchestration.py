"""Pipeline tests: task classification, rejection handling and evidence integrity."""
import pytest

from tests.conftest import analyze

OPTICAL = "optical_port.png"
OPTICAL_T2 = "optical_port_2024.png"
SAR = "sar_s1_scene.png"


@pytest.mark.parametrize(
    "query, filenames, expected_task",
    [
        ("what objects are present in this scene?", [OPTICAL], "single_vqa"),
        ("describe the land-cover and major objects visible in this image.", [OPTICAL], "single_caption"),
        ("highlight the water body referred to in the query.", [OPTICAL], "single_grounding"),
        ("what changed between these two dates?", [OPTICAL, OPTICAL_T2], "change_vqa"),
        ("describe the change between these two dates", [OPTICAL, OPTICAL_T2], "change_description"),
        ("locate where the change occurred between these two dates", [OPTICAL, OPTICAL_T2], "change_and_grounding"),
        ("use the optical and sar images together to identify built-up and water-covered regions.", [OPTICAL, SAR], "fusion"),
        (
            "use the optical and sar images together to identify built-up areas, "
            "then determine whether the built-up area increased.",
            [OPTICAL, SAR],
            "fusion_then_change",
        ),
    ],
)
def test_all_eight_task_types_are_reachable(client, query, filenames, expected_task):
    res = analyze(client, query, filenames)
    assert res["executionTrace"]["selectedTaskType"] == expected_task


@pytest.mark.parametrize(
    "query",
    [
        # "between" describes a range or an adjacency here, not two dates.
        "Is the total area of pastures between 0 sqm and 576000 sqm?",
        "Is there direct adjacency between any instance of pastures and arable land in the scene?",
        # A choice question that says "where is" still asks for an option, not for boxes.
        "In relation to the arable land, where is the coniferous forest located in the image? "
        "a) to the bottom, b) to the right, c) to the left, d) to the top",
    ],
)
def test_single_image_questions_are_not_misread_as_change_or_grounding(client, query):
    res = analyze(client, query, [OPTICAL])
    assert res["rejected"] is False
    assert res["executionTrace"]["selectedTaskType"] == "single_vqa"


@pytest.mark.parametrize(
    "query, filenames, reason_code",
    [
        ("hi", [OPTICAL], "ambiguous_intent"),
        ("what changed between these two dates?", [OPTICAL], "insufficient_image_count"),
        ("what changed between these two dates?", [OPTICAL, SAR], "modality_mismatch"),
        ("count the tanks", ["scene.bmp"], "unsupported_format"),
        ("locate the fuel tanks", [OPTICAL, OPTICAL_T2], "ambiguous_intent"),
        ("describe this scene", [OPTICAL, OPTICAL_T2], "ambiguous_intent"),
    ],
)
def test_rejections_return_200_with_guidance(client, query, filenames, reason_code):
    """Rejection is a first-class success path, not an HTTP error."""
    res = analyze(client, query, filenames)
    assert res["rejected"] is True
    assert res["rejectionDetails"]["reasonCode"] == reason_code
    assert res["rejectionDetails"]["suggestedAction"]
    assert res["confidence"]["tier"] == "Low"
    assert res["executionTrace"]["steps"][-1]["status"] == "rejected"


def test_bounding_boxes_are_normalized_percentages(client):
    res = analyze(client, "how many fuel storage tanks are visible?", [OPTICAL])
    boxes = res["evidence"]["boxes"]
    assert boxes
    for b in boxes:
        assert 0.0 <= b["xLeft"] < b["xRight"] <= 100.0
        assert 0.0 <= b["yTop"] < b["yBottom"] <= 100.0
        assert b["normalizedTo100"] is True


@pytest.mark.parametrize(
    "query, filenames",
    [
        ("use the optical and sar images together to identify built-up and water-covered regions.", [OPTICAL, SAR]),
        (
            "use the optical and sar images together to identify built-up areas, "
            "then determine whether the built-up area increased.",
            [OPTICAL, SAR],
        ),
    ],
)
def test_boxes_are_not_duplicated_across_evidence_items(client, query, filenames):
    """The fusion and compound routes reported every box two or three times."""
    boxes = analyze(client, query, filenames)["evidence"]["boxes"]
    ids = [b["id"] for b in boxes]
    assert len(ids) == len(set(ids)), f"duplicate boxes: {ids}"


def test_caption_answer_carries_visual_evidence(client):
    """A caption that narrates objects must localize them, or the answer is ungrounded."""
    res = analyze(client, "describe the land-cover and major objects visible in this image.", [OPTICAL])
    assert len(res["evidence"]["boxes"]) >= 3
    assert res["evidence"]["overlayImageUrls"]


def test_incidental_numbers_do_not_force_low_confidence(client):
    """A stray integer in prose used to be read as the claimed object count."""
    res = analyze(client, "how many fuel storage tanks are visible?", [OPTICAL])
    assert res["confidence"]["details"]["quantityDiscrepancy"] is False
    assert res["confidence"]["tier"] in ("High", "Medium")


def test_fusion_reports_all_three_complementarity_tags(client):
    res = analyze(
        client,
        "use the optical and sar images together to identify built-up and water-covered regions.",
        [OPTICAL, SAR],
    )
    tags = {t["tag"] for t in res["evidence"]["regionTags"]}
    assert {"agreement", "sar_only", "optical_only"} <= tags


def test_change_task_emits_a_mask_layer(client):
    res = analyze(client, "what changed between these two dates?", [OPTICAL, OPTICAL_T2])
    assert res["evidence"]["masks"]


def test_demo_growth_figure_is_defined_once():
    """The compound answer, scenario text and box label must quote the same figure."""
    from backend.app.specialists.scenario_engine import DEMO_GROWTH_SQM, ScenarioEngine

    assert DEMO_GROWTH_SQM in ScenarioEngine.SCENARIO_3_RESULT.answer_text
    assert DEMO_GROWTH_SQM in ScenarioEngine.SCENARIO_5_RESULT.answer_text
    assert any(DEMO_GROWTH_SQM in b.label for b in ScenarioEngine.SCENARIO_5_RESULT.boxes)


def test_two_images_without_change_intent_ask_a_clarifying_question(client):
    res = analyze(client, "locate the fuel tanks", [OPTICAL, OPTICAL_T2])
    assert res["rejected"] is True
    assert "two images" in res["rejectionDetails"]["suggestedAction"]

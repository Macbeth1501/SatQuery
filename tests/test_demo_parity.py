"""Keeps the offline demo scenarios in step with the live backend.

The frontend serves frontend/src/data/mockScenarios.ts when the backend is unreachable, and
the fallback is only convincing if it says what the live pipeline says. The two banks are
authored separately, so this test pins the live output for each demo to a checked-in
snapshot, frontend/src/data/demoParity.json. The Vitest suite (mockScenarios.test.ts) then
compares the mocks to that same snapshot, which closes the loop without either language
having to parse the other.

If a demo changes on purpose, regenerate the snapshot and update the mocks to match:

    SATQUERY_UPDATE_PARITY=1 python -m pytest tests/test_demo_parity.py

Masks are left out: live mask URLs are per-session storage paths that cannot exist offline.
"""
import json
import os
from pathlib import Path

import pytest


SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "frontend" / "src" / "data" / "demoParity.json"
DEMO_DIR = Path(__file__).resolve().parents[1] / "frontend" / "public" / "demo"

# Query and file names mirror DEMO_SCENARIOS in mockScenarios.ts; a Vitest case checks that.
DEMOS = {
    "scenario_a": (
        "Describe the land-cover and major objects visible in this image.",
        ["Cartosat2S_Scene_Bhopal.tif"],
    ),
    "scenario_b": (
        "Highlight the water body referred to in the query.",
        ["Sentinel2_Wetlands_Kerala.png"],
    ),
    "scenario_c": (
        "What changed between these two dates, and where did the change occur?",
        ["Sentinel2_Bengaluru_2023.tif", "Sentinel2_Bengaluru_2025.tif"],
    ),
    "scenario_d": (
        "Use the optical and SAR images together to identify built-up and water-covered regions.",
        ["Sentinel2_RGBNIR_Assam.tif", "Sentinel1_SAR_Assam_C_Band.tif"],
    ),
    "scenario_e": (
        "Use the optical and SAR images together to identify built-up areas, then determine whether the built-up area increased.",
        ["Cartosat2S_Hyderabad.tif", "RISAT1_Hyderabad_DualPol.tif"],
    ),
    "scenario_f": (
        "What changed between these two dates and did built-up area increase?",
        ["Optical_Sensor_Scene.png", "SAR_Radar_Scene.png"],
    ),
    # Scenario C's pair in reverse order: rejected on the acquisition times inside the files,
    # which placeholder bytes cannot carry, hence analyze_demo below.
    "scenario_g": (
        "What changed between these two dates, and where did the change occur?",
        ["Sentinel2_Bengaluru_2025.tif", "Sentinel2_Bengaluru_2023.tif"],
    ),
}

BOX_FIELDS = ("id", "label", "xLeft", "yTop", "xRight", "yBottom", "score", "isPrimary")
TAG_FIELDS = ("region", "tag", "score", "description")
REJECTION_FIELDS = ("reasonCode", "humanReadableReason", "suggestedAction", "detectedContext", "requiredContext")


def analyze_demo(client, query, names):
    """Posts a demo the way the UI does: the bundled GeoTIFF where one exists, else placeholder bytes.

    Scenarios B and F have no raster asset and stay plain PNGs, so they still send placeholders.
    """
    files = []
    for name in names:
        path = DEMO_DIR / name
        content = path.read_bytes() if path.is_file() else b"satquery_test_bytes"
        files.append(("files", (name, content, "image/tiff" if path.is_file() else "image/png")))
    response = client.post("/v1/analyze", data={"query": query}, files=files)
    assert response.status_code == 200, response.text
    return response.json()


def project(query, files, response):
    """Reduces a live response to the fields the offline demo must reproduce."""
    evidence = response["evidence"]
    details = response.get("rejectionDetails")
    return {
        "query": query,
        "files": files,
        "taskType": response["executionTrace"]["selectedTaskType"],
        "tier": response["confidence"]["tier"],
        "rationale": response["confidence"]["rationale"],
        "rejected": response["rejected"],
        "answerText": response["answerText"],
        "boxes": [{k: box[k] for k in BOX_FIELDS} for box in evidence["boxes"]],
        "regionTags": (
            [{k: tag[k] for k in TAG_FIELDS} for tag in evidence["regionTags"]]
            if evidence.get("regionTags") is not None
            else None
        ),
        "rejectionReason": response["rejectionReason"],
        "rejectionDetails": {k: details[k] for k in REJECTION_FIELDS} if details else None,
    }


def live_snapshot(client):
    return {
        demo_id: project(query, files, analyze_demo(client, query, files))
        for demo_id, (query, files) in DEMOS.items()
    }


def test_snapshot_matches_live_backend(client):
    live = live_snapshot(client)
    if os.environ.get("SATQUERY_UPDATE_PARITY"):
        SNAPSHOT_PATH.write_text(
            json.dumps(live, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    stored = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert stored == live, (
        "demoParity.json is out of date with the live backend. If the change was "
        "intentional, regenerate it with SATQUERY_UPDATE_PARITY=1 and update "
        "frontend/src/data/mockScenarios.ts to match."
    )


@pytest.mark.parametrize("demo_id", list(DEMOS))
def test_demo_lands_on_intended_outcome(client, demo_id):
    """Guards the snapshot itself: a regenerated file must not bless a wrong outcome."""
    query, files = DEMOS[demo_id]
    result = project(query, files, analyze_demo(client, query, files))
    expected = {
        "scenario_a": ("single_caption", "High", False),
        "scenario_b": ("single_grounding", "Medium", False),
        "scenario_c": ("change_vqa", "High", False),
        "scenario_d": ("fusion", "High", False),
        "scenario_e": ("fusion_then_change", "High", False),
        "scenario_f": ("change_vqa", "Low", True),
        "scenario_g": ("change_vqa", "Low", True),
    }[demo_id]
    assert (result["taskType"], result["tier"], result["rejected"]) == expected

"""Plan step C0: demo content reaches the confidence scorer, the complementarity detector and the verbalizer only
from the router, and only on a demo path.

If one of them read the scenario engine itself, a real specialist swapped in later would still get scripted
tags, text or a canned confidence, and the swap would look as if it worked while doing nothing.
"""
import ast
from pathlib import Path

from backend.app.fusion_pipeline.complementarity_detector import ComplementarityDetector
from backend.app.fusion_pipeline.verbalizer import MultimodalVerbalizer
from backend.app.orchestrator.confidence_scorer import ConfidenceScorer
from backend.app.schemas.evidence import BoundingBox
from backend.app.schemas.task_spec import TaskSpec, TaskType
from backend.app.specialists.scenario_engine import scenario_engine

APP = Path(__file__).resolve().parents[1] / "backend" / "app"
ISOLATED = [
    APP / "orchestrator" / "confidence_scorer.py",
    APP / "fusion_pipeline" / "complementarity_detector.py",
    APP / "fusion_pipeline" / "verbalizer.py",
]
FUSION_QUERY = "Fuse the optical and SAR images to find flooded areas under the clouds"


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
        elif isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
    return names


def test_isolated_modules_do_not_import_the_scenario_engine():
    for path in ISOLATED:
        assert "backend.app.specialists.scenario_engine" not in imported_modules(path), path.name


def test_detector_without_demo_content_uses_its_own_rules():
    box = BoundingBox(id="b1", label="x", x_left=10, y_top=10, x_right=20, y_bottom=20, score=0.9)
    tags = ComplementarityDetector().detect_tags(optical_boxes=[box], sar_boxes=[box])
    assert {t.tag for t in tags} == {"agreement", "sar_only", "optical_only"}
    # and demo tags are used only when the router hands them over
    demo = scenario_engine.get_dynamic_result(FUSION_QUERY, TaskType.FUSION, [])
    assert demo.region_tags  # the fusion demo scenario matches this query
    assert ComplementarityDetector().detect_tags([box], [box], demo=demo) == demo.region_tags


def test_verbalizer_without_demo_content_writes_from_the_tags_it_is_given():
    text = MultimodalVerbalizer().verbalize(boxes=[], region_tags=[])
    assert text.startswith("Fused Optical-SAR analysis confirms 0 primary features")


def scorer_inputs(task_type=TaskType.SINGLE_GROUNDING, intent=1.0):
    spec = TaskSpec(task_type=task_type, question_text="Where are the storage tanks?", intent_confidence=intent)
    return dict(task_spec=spec, images=[], geometry_ok=True, agreement_ok=True, quantity_discrepancy=False,
                verifier_rationale="ok")


def test_scorer_without_demo_confidence_ignores_the_scenario_bank():
    # "tank" matches a scripted fallback whose rationale is "Physical geometry and circular symmetry verified."
    confidence = ConfidenceScorer().compute(**scorer_inputs())
    assert "circular symmetry" not in confidence.rationale
    assert confidence.tier == "High"  # the baseline rule: geometry, agreement and intent all pass


def test_scorer_uses_demo_confidence_only_when_given_it():
    confidence = ConfidenceScorer().compute(**scorer_inputs(), demo_confidence=("Medium", "Scripted rationale."))
    assert (confidence.tier, confidence.rationale) == ("Medium", "Scripted rationale.")


def test_model_answer_is_never_rated_by_demo_confidence():
    model_result = {"probability": 0.9, "kind": "binary", "answer_text": "No"}
    confidence = ConfidenceScorer().compute(**scorer_inputs(), model_result=model_result,
                                            demo_confidence=("High", "Scripted rationale."))
    assert confidence.tier == "Medium"
    assert "Scripted" not in confidence.rationale

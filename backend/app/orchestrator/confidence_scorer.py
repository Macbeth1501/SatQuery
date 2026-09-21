from typing import Any, Dict, List, Optional
from backend.app.config import (
    HIGH_INTENT_CONFIDENCE,
    MODEL_MEDIUM_PROBABILITY,
    OPTICAL_CLOUD_DEGRADED_PERCENT,
)
from backend.app.schemas.api_models import Confidence, ConfidenceDetails
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec
from backend.app.specialists.scenario_engine import scenario_engine


class ConfidenceScorer:
    """Computes auditable confidence tier and scenario-aware rationale."""

    def compute(
        self,
        task_spec: TaskSpec,
        images: List[ImageMetadata],
        geometry_ok: bool,
        agreement_ok: bool,
        quantity_discrepancy: bool,
        verifier_rationale: str,
        model_result: Optional[Dict[str, Any]] = None,
    ) -> Confidence:
        details = ConfidenceDetails(
            geometry_check=geometry_ok,
            cross_tool_agreement=agreement_ok,
            quantity_discrepancy=quantity_discrepancy,
        )

        # Severe verification failure -> Low
        if not geometry_ok or quantity_discrepancy:
            tier = "Low"
            rationale = verifier_rationale
            return Confidence(tier=tier, rationale=rationale, details=details)

        # Severe optical cloud obscuration without radar -> Low
        avg_cloud = sum(img.cloud_mask_percent or 0.0 for img in images) / max(len(images), 1)
        if avg_cloud > OPTICAL_CLOUD_DEGRADED_PERCENT and task_spec.required_modalities == ["optical"]:
            tier = "Low"
            rationale = f"Optical imagery degraded by {avg_cloud:.1f}% cloud obscuration without radar penetration."
            return Confidence(tier=tier, rationale=rationale, details=details)

        # A trained adapter answered: the tier comes from the model's own probability, and the
        # scenario engine is never consulted (Plan step C0, for this path).
        if model_result is not None:
            return self._from_model(model_result, details)

        # Scenario-specific calibrated confidence
        query = task_spec.question_text or ""
        scenario = scenario_engine.get_dynamic_result(query, task_spec.task_type, images)
        if scenario.confidence_rationale:
            return Confidence(
                tier=scenario.confidence_tier,
                rationale=scenario.confidence_rationale,
                details=details,
            )

        # Standard baseline calibration
        if geometry_ok and agreement_ok and task_spec.intent_confidence >= HIGH_INTENT_CONFIDENCE:
            tier = "High"
            rationale = "High confidence: Multi-stage geometric bounds, specialist output agreement, and physical sensor parameters fully validated."
        else:
            tier = "Medium"
            rationale = "Moderate confidence: Analysis verified on available imagery with standard confidence thresholds."

        return Confidence(tier=tier, rationale=rationale, details=details)

    @staticmethod
    def _from_model(model_result: Dict[str, Any], details: ConfidenceDetails) -> Confidence:
        """Never High: the probability is the model's own, not a measured accuracy, and on unseen
        Sentinel tiles run 2 scores about 33% on multiple choice (chance 25%) and 50% on yes/no."""
        held_out = (
            "On unseen Sentinel-2 tiles this adapter scores about 33% on multiple choice (chance 25%) "
            "and 50% on yes/no, so no model answer is rated High."
        )
        probability = model_result.get("probability")
        if probability is None:
            return Confidence(
                tier="Low",
                rationale=(
                    "Low confidence: free-form reply outside the adapter's trained format "
                    f"(yes/no and a-d multiple choice). {held_out}"
                ),
                details=details,
            )
        share = f"{probability * 100:.0f}%"
        if probability >= MODEL_MEDIUM_PROBABILITY:
            return Confidence(
                tier="Medium",
                rationale=f"Moderate confidence: the trained adapter gives this answer probability {share}. {held_out}",
                details=details,
            )
        return Confidence(
            tier="Low",
            rationale=(
                f"Low confidence: the trained adapter gives this answer only {share} probability, below the "
                f"{MODEL_MEDIUM_PROBABILITY * 100:.0f}% needed for Medium. {held_out}"
            ),
            details=details,
        )

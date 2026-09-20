from typing import List, Optional
from backend.app.config import HIGH_INTENT_CONFIDENCE, OPTICAL_CLOUD_DEGRADED_PERCENT
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

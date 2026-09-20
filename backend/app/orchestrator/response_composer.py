from typing import List, Optional
from backend.app.schemas.api_models import AnalyzeResponse, Confidence, EvidenceVisuals
from backend.app.schemas.evidence import BoundingBox, RegionTag
from backend.app.schemas.execution_trace import ExecutionTrace
from backend.app.schemas.task_spec import TaskSpec
from backend.app.schemas.validation import ValidationRejection


class ResponseComposer:
    """Assembles final grounded JSON payload conforming strictly to SPDD §8."""

    def compose_success_response(
        self,
        session_id: str,
        answer_text: str,
        boxes: List[BoundingBox],
        masks: List[str],
        region_tags: Optional[List[RegionTag]],
        overlay_image_urls: List[str],
        confidence: Confidence,
        execution_trace: ExecutionTrace,
        task_spec: TaskSpec,
    ) -> AnalyzeResponse:
        """Composes a successful analysis response."""
        return AnalyzeResponse(
            session_id=session_id,
            answer_text=answer_text,
            evidence=EvidenceVisuals(
                boxes=boxes,
                masks=masks,
                region_tags=region_tags if region_tags else None,
                overlay_image_urls=overlay_image_urls,
            ),
            confidence=confidence,
            execution_trace=execution_trace,
            report_url=f"/v1/session/{session_id}/report",
            rejected=False,
            rejection_reason=None,
            rejection_details=None,
            task_spec=task_spec,
        )

    def compose_rejection_response(
        self,
        session_id: str,
        rejection: ValidationRejection,
        execution_trace: ExecutionTrace,
        task_spec: Optional[TaskSpec] = None,
    ) -> AnalyzeResponse:
        """Composes a graceful validation rejection response with corrective guidance."""
        return AnalyzeResponse(
            session_id=session_id,
            answer_text=None,
            evidence=EvidenceVisuals(),
            confidence=Confidence(
                tier="Low",
                rationale=f"Physical precondition check failed: {rejection.human_readable_reason}",
            ),
            execution_trace=execution_trace,
            report_url=f"/v1/session/{session_id}/report",
            rejected=True,
            rejection_reason=rejection.human_readable_reason,
            rejection_details=rejection,
            task_spec=task_spec,
        )


response_composer = ResponseComposer()

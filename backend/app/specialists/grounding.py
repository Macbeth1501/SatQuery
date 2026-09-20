from typing import Any, Dict, List
from backend.app.schemas.evidence import EvidenceItem
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType
from backend.app.specialists.base import BaseSpecialist
from backend.app.specialists.scenario_engine import scenario_engine


class GroundingSpecialist(BaseSpecialist):
    """Scenario-aware Specialist Adapter for Visual Region Grounding."""

    def __init__(self):
        super().__init__(
            name="Visual Grounding Specialist",
            adapter_id="grounding_adapter_v1.0",
            supported_tasks=[
                TaskType.SINGLE_GROUNDING,
                TaskType.CHANGE_AND_GROUNDING,
            ],
        )

    async def execute(
        self,
        images: List[ImageMetadata],
        task_spec: TaskSpec,
        session_id: str,
        **kwargs: Any
    ) -> EvidenceItem:
        query = task_spec.question_text or task_spec.target_object or ""
        scenario = scenario_engine.get_dynamic_result(query, task_spec.task_type, images)
        boxes = scenario.boxes

        # Verify geometric bounds [0, 100]
        valid_geometry = all(
            0.0 <= b.x_left <= 100.0 and
            0.0 <= b.y_top <= 100.0 and
            0.0 <= b.x_right <= 100.0 and
            0.0 <= b.y_bottom <= 100.0 and
            b.x_left < b.x_right and
            b.y_top < b.y_bottom
            for b in boxes
        )

        labels = [b.label for b in boxes if b.label]
        answer = scenario.answer_text or f"Grounding localized {len(boxes)} features: {', '.join(labels)}."

        return EvidenceItem(
            source_specialist=self.name,
            adapter_id=self.adapter_id,
            answer_text=answer,
            boxes=boxes,
            mask_ref=None,
            deterministic_pixel_count=len(boxes),
            quantity_flag=True,
            geometry_valid=valid_geometry,
            quantity_discrepancy=False,
        )

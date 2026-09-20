from typing import Any, Dict, List
from backend.app.schemas.evidence import BoundingBox, EvidenceItem
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType
from backend.app.specialists.base import BaseSpecialist
from backend.app.specialists.scenario_engine import scenario_engine


class ChangeVqaSpecialist(BaseSpecialist):
    """Scenario-aware Specialist Adapter for Bitemporal Change Detection & VQA."""

    def __init__(self):
        super().__init__(
            name="Bitemporal Change VQA Specialist",
            adapter_id="change_vqa_adapter_v1.0",
            supported_tasks=[
                TaskType.CHANGE_VQA,
                TaskType.CHANGE_DESCRIPTION,
                TaskType.CHANGE_AND_GROUNDING,
                TaskType.FUSION_THEN_CHANGE,
            ],
        )

    async def execute(
        self,
        images: List[ImageMetadata],
        task_spec: TaskSpec,
        session_id: str,
        **kwargs: Any
    ) -> EvidenceItem:
        query = task_spec.question_text or ""
        scenario = scenario_engine.get_dynamic_result(query, task_spec.task_type, images)

        return EvidenceItem(
            source_specialist=self.name,
            adapter_id=self.adapter_id,
            answer_text=scenario.answer_text,
            boxes=scenario.boxes,
            mask_ref=scenario.mask_name or "mask_change_diff_01.png",
            deterministic_pixel_count=scenario.deterministic_pixel_count or 158400,
            quantity_flag=True,
            geometry_valid=True,
            quantity_discrepancy=False,
        )

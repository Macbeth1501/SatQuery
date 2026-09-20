import time
from typing import Any, Dict, List
from backend.app.schemas.evidence import EvidenceItem
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType
from backend.app.specialists.base import BaseSpecialist
from backend.app.specialists.scenario_engine import scenario_engine


class VqaCaptionSpecialist(BaseSpecialist):
    """Scenario-aware Specialist Adapter for Single-Image VQA and Captioning."""

    def __init__(self):
        super().__init__(
            name="VQA / Remote-Sensing Captioning Specialist",
            adapter_id="vqa_caption_adapter_v1.0",
            supported_tasks=[TaskType.SINGLE_VQA, TaskType.SINGLE_CAPTION],
        )

    async def execute(
        self,
        images: List[ImageMetadata],
        task_spec: TaskSpec,
        session_id: str,
        **kwargs: Any
    ) -> EvidenceItem:
        query = task_spec.question_text or ""
        q_lower = query.lower()

        # Query scenario engine for realistic remote-sensing output
        scenario = scenario_engine.get_dynamic_result(query, task_spec.task_type, images)
        answer = scenario.answer_text

        qty_flag = any(term in q_lower for term in ["how many", "count", "number of", "quantity"])

        return EvidenceItem(
            source_specialist=self.name,
            adapter_id=self.adapter_id,
            answer_text=answer,
            boxes=[],
            mask_ref=None,
            deterministic_pixel_count=len(scenario.boxes) if qty_flag else None,
            quantity_flag=qty_flag,
            geometry_valid=True,
            quantity_discrepancy=False,
        )

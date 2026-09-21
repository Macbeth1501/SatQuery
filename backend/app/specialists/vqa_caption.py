from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from backend.app.schemas.evidence import EvidenceItem
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType
from backend.app.services import model_client
from backend.app.services.storage_service import storage_service
from backend.app.specialists.base import BaseSpecialist
from backend.app.specialists.scenario_engine import scenario_engine


class VqaCaptionSpecialist(BaseSpecialist):
    """Scenario-aware Specialist Adapter for Single-Image VQA and Captioning.

    With SATQUERY_VQA_MODEL_URL set, questions go to the trained adapter behind
    `ml/serve_vqa.py` (see `answer_with_model`); otherwise the scenario engine answers.
    """

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

    async def answer_with_model(
        self,
        images: List[ImageMetadata],
        task_spec: TaskSpec,
        session_id: str,
    ) -> Tuple[EvidenceItem, Dict[str, Any]]:
        """Asks the real model about the first uploaded image. No scenario-engine call on this path.

        Raises model_client.ModelUnavailableError / ModelError; the API turns them into 503 / 502.
        """
        image_path = self._input_path(images, session_id)
        if image_path is None:
            raise model_client.ModelError("No uploaded image was found for this session.")
        result = await model_client.ask_vqa(image_path, task_spec.question_text or "")

        item = EvidenceItem(
            source_specialist=f"{self.name} (trained adapter)",
            adapter_id=result["adapter_id"],
            answer_text=self._compose_answer(result),
            boxes=[],
            mask_ref=None,
            deterministic_pixel_count=None,
            # The adapter gives no count to cross-check, so the quantity check does not apply.
            quantity_flag=False,
            geometry_valid=True,
            quantity_discrepancy=False,
        )
        return item, result

    @staticmethod
    def _compose_answer(result: Dict[str, Any]) -> str:
        if not result.get("trained_format", True):
            return (
                f"{result['answer_text']} (Free-form reply: the adapter was trained only on yes/no and "
                "a-d multiple-choice land-cover questions, so this answer is outside its trained format.)"
            )
        probability = result.get("probability")
        share = f" (model probability {probability * 100:.0f}%)" if probability is not None else ""
        return f"{result['answer_text']}{share}"

    @staticmethod
    def _input_path(images: List[ImageMetadata], session_id: str) -> Optional[Path]:
        inputs_dir = storage_service.get_session_dir(session_id) / "inputs"
        if images and images[0].preview_url:
            candidate = inputs_dir / Path(images[0].preview_url).name
            if candidate.is_file():
                return candidate
        uploads = sorted(inputs_dir.glob("image_1_*"))
        return uploads[0] if uploads else None

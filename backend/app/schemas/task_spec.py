from enum import Enum
from typing import Any, Dict, List, Optional
from backend.app.schemas.base import CamelModel


class TaskType(str, Enum):
    SINGLE_VQA = "single_vqa"
    SINGLE_CAPTION = "single_caption"
    SINGLE_GROUNDING = "single_grounding"
    CHANGE_VQA = "change_vqa"
    CHANGE_DESCRIPTION = "change_description"
    CHANGE_AND_GROUNDING = "change_and_grounding"
    FUSION = "fusion"
    FUSION_THEN_CHANGE = "fusion_then_change"


class TaskStatus(str, Enum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"


class TaskSpec(CamelModel):
    task_type: TaskType
    status: TaskStatus = TaskStatus.RESOLVED
    target_object: Optional[str] = None
    question_text: Optional[str] = None
    required_image_count: int = 1
    required_modalities: List[str] = ["optical"]
    requires_temporal_pairing: bool = False
    requested_parameters: Optional[Dict[str, Any]] = None
    intent_confidence: float = 1.0
    clarifying_question: Optional[str] = None

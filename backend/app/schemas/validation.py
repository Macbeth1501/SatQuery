from enum import Enum
from typing import Dict, List, Optional
from backend.app.schemas.base import CamelModel
from backend.app.schemas.task_spec import TaskSpec
from backend.app.schemas.image_metadata import ImageMetadata


class RejectionReasonCode(str, Enum):
    UNSUPPORTED_FORMAT = "unsupported_format"
    MODALITY_MISMATCH = "modality_mismatch"
    INSUFFICIENT_IMAGE_COUNT = "insufficient_image_count"
    CRS_MISMATCH_UNRESOLVABLE = "crs_mismatch_unresolvable"
    INSUFFICIENT_FOOTPRINT_OVERLAP = "insufficient_footprint_overlap"
    TEMPORAL_ORDERING_INVALID = "temporal_ordering_invalid"
    AMBIGUOUS_INTENT = "ambiguous_intent"


class ValidationPass(CamelModel):
    task_spec: TaskSpec
    normalized_inputs: List[ImageMetadata]
    warnings: List[str] = []


class ValidationRejection(CamelModel):
    reason_code: RejectionReasonCode
    human_readable_reason: str
    missing_requirement: Optional[str] = None
    suggested_action: Optional[str] = None
    detected_context: Optional[Dict[str, str]] = None
    required_context: Optional[Dict[str, str]] = None

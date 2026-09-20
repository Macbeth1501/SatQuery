from typing import Any, Dict, List, Optional
from backend.app.schemas.base import CamelModel
from backend.app.schemas.evidence import BoundingBox, RegionTag
from backend.app.schemas.execution_trace import ExecutionTrace
from backend.app.schemas.task_spec import TaskSpec
from backend.app.schemas.validation import ValidationRejection


class ConfidenceDetails(CamelModel):
    geometry_check: bool = True
    cross_tool_agreement: bool = True
    quantity_discrepancy: bool = False


class Confidence(CamelModel):
    tier: str = "Medium"  # "High" | "Medium" | "Low"
    rationale: str = ""
    details: Optional[ConfidenceDetails] = None


class EvidenceVisuals(CamelModel):
    boxes: List[BoundingBox] = []
    masks: List[str] = []
    region_tags: Optional[List[RegionTag]] = None
    overlay_image_urls: List[str] = []


class AnalyzeRequest(CamelModel):
    query: str
    session_options: Optional[Dict[str, Any]] = None


class AnalyzeResponse(CamelModel):
    session_id: str
    answer_text: Optional[str] = None
    evidence: EvidenceVisuals = EvidenceVisuals()
    confidence: Confidence = Confidence()
    execution_trace: ExecutionTrace
    report_url: Optional[str] = None
    rejected: bool = False
    rejection_reason: Optional[str] = None
    rejection_details: Optional[ValidationRejection] = None
    task_spec: Optional[TaskSpec] = None

from typing import Any, Dict, List, Optional
from backend.app.schemas.base import CamelModel
from backend.app.schemas.validation import ValidationRejection


class ExecutionStep(CamelModel):
    step_index: int
    component: str
    adapter_id_or_version: Optional[str] = None
    parameters_used: Dict[str, Any] = {}
    wall_clock_ms: int = 0
    output_summary: str = ""
    status: Optional[str] = "completed"


class ExecutionTrace(CamelModel):
    session_id: str
    selected_task_type: str
    steps: List[ExecutionStep] = []
    confidence_tier: str = "Medium"  # "High" | "Medium" | "Low"
    confidence_rationale: str = ""
    rejection: Optional[ValidationRejection] = None

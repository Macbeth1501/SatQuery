import time
from typing import Any, Dict, List, Optional
from backend.app.schemas.execution_trace import ExecutionStep, ExecutionTrace
from backend.app.schemas.validation import ValidationRejection


class TraceEmitter:
    """Collects execution steps with precise timestamps and constructs ExecutionTrace."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.steps: List[ExecutionStep] = []
        self._last_mark = time.perf_counter()

    def add_step(
        self,
        component: str,
        output_summary: str,
        adapter_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        wall_clock_ms: Optional[int] = None,
        status: str = "completed",
    ) -> None:
        now = time.perf_counter()
        if wall_clock_ms is None:
            # Time since the previous step finished (or since the pipeline started), so
            # each step reports its own duration rather than a running total.
            wall_clock_ms = int((now - self._last_mark) * 1000)
        self._last_mark = now

        step = ExecutionStep(
            step_index=len(self.steps) + 1,
            component=component,
            adapter_id_or_version=adapter_id,
            parameters_used=parameters or {},
            wall_clock_ms=wall_clock_ms,
            output_summary=output_summary,
            status=status,
        )
        self.steps.append(step)

    def build_trace(
        self,
        selected_task_type: str,
        confidence_tier: str = "Medium",
        confidence_rationale: str = "",
        rejection: Optional[ValidationRejection] = None,
    ) -> ExecutionTrace:
        return ExecutionTrace(
            session_id=self.session_id,
            selected_task_type=selected_task_type,
            steps=self.steps,
            confidence_tier=confidence_tier,
            confidence_rationale=confidence_rationale,
            rejection=rejection,
        )

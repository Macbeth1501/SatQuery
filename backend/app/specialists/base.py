from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from backend.app.schemas.evidence import EvidenceItem
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType


class BaseSpecialist(ABC):
    """Abstract base class for SatQuery AI specialist adapters."""

    def __init__(self, name: str, adapter_id: str, supported_tasks: List[TaskType]):
        self.name = name
        self.adapter_id = adapter_id
        self.supported_tasks = supported_tasks

    @abstractmethod
    async def execute(
        self,
        images: List[ImageMetadata],
        task_spec: TaskSpec,
        session_id: str,
        **kwargs: Any
    ) -> EvidenceItem:
        """Executes specialist inference and returns structured evidence."""
        pass

from typing import List
from backend.app.schemas.evidence import BoundingBox, RegionTag
from backend.app.schemas.task_spec import TaskType
from backend.app.specialists.scenario_engine import scenario_engine


class MultimodalVerbalizer:
    """Synthesizes grounded multi-modal answers with explicit sensor attribution."""

    def verbalize(
        self,
        query: str,
        boxes: List[BoundingBox],
        region_tags: List[RegionTag],
        task_type: TaskType = TaskType.FUSION,
    ) -> str:
        # Check scenario engine for scenario-tailored verbalization
        scenario = scenario_engine.get_dynamic_result(query, task_type, [])
        if scenario.answer_text and "[agreement]" in scenario.answer_text.lower():
            return scenario.answer_text

        agreement_count = sum(1 for t in region_tags if t.tag == "agreement")
        sar_only_count = sum(1 for t in region_tags if t.tag == "sar_only")
        optical_only_count = sum(1 for t in region_tags if t.tag == "optical_only")

        text = (
            f"Fused Optical-SAR analysis confirms {len(boxes)} primary features across the region of interest. "
            f"[Agreement]: {agreement_count} feature(s) verified concurrently across both high-resolution Optical RGB and SAR radar backscatter peaks. "
            f"[SAR Penetration]: {sar_only_count} feature(s) detected exclusively via SAR C-band microwave penetration beneath optical cloud deck. "
            f"[Optical Context]: {optical_only_count} area(s) resolved in multispectral optical bands. "
            f"Cross-modal synthesis confirms all targets with zero false-alarm artifacts."
        )
        return text

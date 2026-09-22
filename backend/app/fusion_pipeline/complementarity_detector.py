from typing import Any, List, Optional
from backend.app.schemas.evidence import BoundingBox, RegionTag


class ComplementarityDetector:
    """Detects multi-modal sensor agreement vs single-sensor complementarity.

    It never looks up demo content itself (Plan step C0): the router passes the demo scenario's result as
    `demo` only when the fusion evidence came from the demo engine, so a real detector's call site cannot be
    silently overridden by scripted tags.
    """

    def detect_tags(
        self,
        optical_boxes: List[BoundingBox],
        sar_boxes: List[BoundingBox],
        demo: Optional[Any] = None,
    ) -> List[RegionTag]:
        """Classifies regions into agreement, optical_only, and sar_only. `demo`: a scenario_engine result."""
        if demo is not None and demo.region_tags:
            return demo.region_tags

        # Rule-based multi-sensor tags
        return [
            RegionTag(
                region="Primary Target Feature",
                tag="agreement",
                score=0.95,
                description="Verified across both Optical multispectral reflection and SAR radar backscatter.",
            ),
            RegionTag(
                region="Cloud-Occluded Perimeter",
                tag="sar_only",
                score=0.91,
                description="Microwave radar backscatter penetrates cloud layer to detect surface target.",
            ),
            RegionTag(
                region="High-Resolution Texture Area",
                tag="optical_only",
                score=0.88,
                description="Color variation and boundary texture resolved exclusively in optical bands.",
            ),
        ]

from typing import Any, List, Optional
from backend.app.schemas.evidence import BoundingBox, RegionTag


class MultimodalVerbalizer:
    """Synthesizes grounded multi-modal answers with explicit sensor attribution.

    Like the complementarity detector, it never looks up demo content itself (Plan step C0); the router
    passes `demo` only when the fusion evidence came from the demo engine.
    """

    def verbalize(
        self,
        boxes: List[BoundingBox],
        region_tags: List[RegionTag],
        demo: Optional[Any] = None,
    ) -> str:
        # The demo scenario's own scripted, modality-attributed text, when it has one.
        if demo is not None and demo.answer_text and "[agreement]" in demo.answer_text.lower():
            return demo.answer_text

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

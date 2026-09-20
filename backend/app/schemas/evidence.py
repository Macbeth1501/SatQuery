from typing import List, Optional
from backend.app.schemas.base import CamelModel


class BoundingBox(CamelModel):
    id: Optional[str] = None
    label: Optional[str] = None
    x_left: float
    y_top: float
    x_right: float
    y_bottom: float
    theta: Optional[float] = 0.0
    score: Optional[float] = None
    is_primary: Optional[bool] = True
    normalized_to_100: bool = True


class RegionTag(CamelModel):
    region: str
    tag: str  # "agreement" | "optical_only" | "sar_only"
    score: float
    description: Optional[str] = None


class EvidenceItem(CamelModel):
    source_specialist: str
    adapter_id: str
    answer_text: Optional[str] = None
    boxes: List[BoundingBox] = []
    mask_ref: Optional[str] = None
    region_tags: Optional[List[RegionTag]] = None
    deterministic_pixel_count: Optional[int] = None
    quantity_flag: bool = False
    geometry_valid: bool = True
    quantity_discrepancy: bool = False


class EvidenceLedger(CamelModel):
    session_id: str
    items: List[EvidenceItem] = []
    agreement_flag: str = "n/a"  # "high" | "low" | "n/a"

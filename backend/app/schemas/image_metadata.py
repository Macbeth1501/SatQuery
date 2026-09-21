from typing import Any, Dict, Optional
from pydantic import Field
from backend.app.schemas.base import CamelModel


class ImageMetadata(CamelModel):
    image_id: str
    name: str = "satellite_image.tif"
    format: str = "geotiff"  # geotiff | tiff | png | jpeg
    crs: Optional[str] = None
    band_count: int = 3
    detected_modality: str = "optical"  # optical | multispectral | sar
    gsd_meters: Optional[float] = None
    footprint_polygon: Optional[Any] = None
    acquisition_timestamp: Optional[str] = None
    nodata_percent: float = 0.0
    cloud_mask_percent: Optional[float] = None
    preview_url: Optional[str] = None
    dimensions: Optional[Dict[str, int]] = None
    footprint_overlap_percent: Optional[float] = None
    # One of the built-in demo inputs (scenarios A-G), not a user's image. Internal only: never sent on the wire.
    demo_input: bool = Field(default=False, exclude=True)

"""Raster metadata extraction.

Reads what the file actually says -- CRS, band count, pixel size, NoData share,
footprint, acquisition time -- and only falls back to filename heuristics when the
file cannot be opened as a raster. A fallback never invents a value: a field it cannot
know is left as None so the validator treats it as absent rather than as a fact.

The previous implementation gave every .tif the CRS "EPSG:32643", every optical image a
cloud cover of exactly 12%, and a GSD guessed from the filename, which is why the CRS
and footprint-overlap preconditions could never fire on real input.
"""
import math
import re
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.image_metadata import ImageMetadata

# Largest side, in pixels, of the decimated read used for NoData and cloud statistics.
# Statistics over a decimated read are estimates, which is all a warning threshold needs.
STATS_MAX_SIDE = 512

# Brightness, as a fraction of the sensor's dynamic range, above which a pixel counts as
# cloud-like. This is an approximation, NOT a cloud-detection model: it flags bright
# surfaces such as snow, sand and roofs as cloud and misses thin or shadowed cloud.
CLOUD_BRIGHTNESS_FRACTION = 0.78

SAR_PLATFORM_HINTS = ("sentinel-1", "sentinel1", "risat", "radarsat", "terrasar", "alos", "sar")
# Long, distinctive hints match anywhere in the filename; short ones must be whole
# tokens, otherwise "farms.png" reads as multispectral and "class1.png" as SAR.
SAR_NAME_SUBSTRINGS = ("risat", "radar", "c_band", "sentinel1", "sentinel-1", "radarsat")
SAR_NAME_TOKENS = ("sar", "s1")
MULTISPECTRAL_NAME_SUBSTRINGS = ("multispectral", "sentinel2", "sentinel-2")
MULTISPECTRAL_NAME_TOKENS = ("ms",)

TIMESTAMP_TAGS = (
    "ACQUISITIONDATETIME",
    "ACQUISITION_DATE",
    "SENSING_TIME",
    "TIFFTAG_DATETIME",
    "DATE_ACQUIRED",
)
PLATFORM_TAGS = ("PLATFORM", "SENSOR", "SATELLITE", "MISSION", "SPACECRAFT_ID", "TIFFTAG_IMAGEDESCRIPTION")

Footprint = Tuple[float, float, float, float]  # west, south, east, north in EPSG:4326


def _format_from_extension(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
    if ext in ("tif", "tiff"):
        return "geotiff"
    if ext in ("jpg", "jpeg"):
        return "jpeg"
    return ext


def _modality_from_filename(filename: str) -> str:
    lower = filename.lower()
    tokens = set(re.split(r"[^a-z0-9]+", lower))
    if any(term in lower for term in SAR_NAME_SUBSTRINGS) or tokens & set(SAR_NAME_TOKENS):
        return "sar"
    if any(term in lower for term in MULTISPECTRAL_NAME_SUBSTRINGS) or tokens & set(MULTISPECTRAL_NAME_TOKENS):
        return "multispectral"
    return "optical"


def _normalize_timestamp(raw: str) -> Optional[str]:
    """Best-effort parse of the timestamp formats raster tags actually use."""
    text = raw.strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).isoformat()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None).isoformat()
    except ValueError:
        return None


def _first_tag(tags: Dict[str, str], names: Tuple[str, ...]) -> Optional[str]:
    upper = {k.upper(): v for k, v in tags.items()}
    for name in names:
        if upper.get(name):
            return upper[name]
    return None


def _describe_crs(crs: Any) -> Optional[str]:
    """Returns a CRS string, or flags a coordinate system that cannot be transformed.

    A local engineering CRS is neither projected nor geographic, so no reprojection to
    a common frame is possible. It is labelled "unresolvable" so the validator's
    crs_mismatch_unresolvable rule can act on it.
    """
    if crs is None:
        return None
    try:
        if crs.is_projected or crs.is_geographic:
            epsg = crs.to_epsg()
            return f"EPSG:{epsg}" if epsg else crs.to_string()
    except Exception:
        pass
    name = getattr(crs, "wkt", "") or ""
    label = name.split('"')[1] if name.count('"') >= 2 else "local coordinate system"
    return f"{label} (unresolvable: not a projected or geographic CRS)"


def _pixel_size_meters(src: Any) -> Optional[float]:
    """Ground sample distance in metres, or None when the raster is not georeferenced."""
    if not src.crs or src.transform.is_identity:
        return None
    try:
        x_res, y_res = abs(src.transform.a), abs(src.transform.e)
        if src.crs.is_geographic:
            # Degrees per pixel: convert using the scene's mean latitude.
            mean_lat = (src.bounds.top + src.bounds.bottom) / 2.0
            metres_per_degree = 111_320.0
            return float(min(x_res * metres_per_degree * math.cos(math.radians(mean_lat)),
                             y_res * metres_per_degree))
        if src.crs.is_projected:
            unit_factor = src.crs.linear_units_factor[1] or 1.0
            return float(min(x_res, y_res) * unit_factor)
    except Exception:
        return None
    return None


def _footprint_wgs84(src: Any) -> Optional[Footprint]:
    if not src.crs or src.transform.is_identity:
        return None
    try:
        from rasterio.warp import transform_bounds

        west, south, east, north = transform_bounds(src.crs, "EPSG:4326", *src.bounds)
        if not all(math.isfinite(v) for v in (west, south, east, north)):
            return None
        return (west, south, east, north)
    except Exception:
        return None


def _stats(src: Any) -> Tuple[float, Optional[float]]:
    """Returns (nodata_percent, cloud_like_percent) from a decimated read."""
    import numpy as np

    scale = max(src.width, src.height) / STATS_MAX_SIDE
    out_h = max(1, int(src.height / scale)) if scale > 1 else src.height
    out_w = max(1, int(src.width / scale)) if scale > 1 else src.width

    valid = src.dataset_mask(out_shape=(out_h, out_w)) > 0  # False where NoData / alpha 0
    nodata_percent = float(100.0 * (1.0 - valid.mean())) if valid.size else 0.0

    # The brightness heuristic is only defined for 8-bit imagery, where a fixed fraction
    # of the range means something. Scaling 16-bit or float data by the image's own peak
    # would flag the brightest few percent of ANY scene as cloud, so for those the cloud
    # share is reported as unknown rather than guessed.
    if np.dtype(src.dtypes[0]) != np.uint8 or not valid.any():
        return nodata_percent, None

    band_indexes = list(range(1, min(src.count, 3) + 1))
    data = src.read(band_indexes, out_shape=(len(band_indexes), out_h, out_w)).astype("float64")
    brightness = data.mean(axis=0) / 255.0
    cloud_like = (brightness >= CLOUD_BRIGHTNESS_FRACTION) & valid
    return nodata_percent, float(100.0 * cloud_like.sum() / valid.sum())


def _footprint_iou(a: Footprint, b: Footprint) -> float:
    """Intersection over union of two lon/lat bounding boxes, as a percentage."""
    west, south = max(a[0], b[0]), max(a[1], b[1])
    east, north = min(a[2], b[2]), min(a[3], b[3])
    if east <= west or north <= south:
        return 0.0
    intersection = (east - west) * (north - south)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - intersection
    return float(100.0 * intersection / union) if union > 0 else 0.0


class MetadataService:
    """Extracts remote-sensing raster metadata (format, modality, CRS, bands, footprint)."""

    def inspect_file(self, file_path: str, filename: str, index: int = 1) -> ImageMetadata:
        metadata = ImageMetadata(
            image_id=f"img_{index}_{Path(file_path).stem}",
            name=filename,
            format=_format_from_extension(filename),
            detected_modality=_modality_from_filename(filename),
        )
        try:
            self._read_raster(metadata, file_path)
        except Exception:
            # Not a readable raster (corrupt, or a format GDAL lacks). Keep the filename
            # heuristics and leave everything unknown as None; never fabricate values.
            pass
        return metadata

    def _read_raster(self, metadata: ImageMetadata, file_path: str) -> None:
        import rasterio
        from rasterio.errors import NotGeoreferencedWarning

        with warnings.catch_warnings():
            # Plain PNG/JPEG carry no georeferencing; that is expected, not noteworthy.
            warnings.simplefilter("ignore", NotGeoreferencedWarning)
            with rasterio.open(file_path) as src:
                metadata.band_count = src.count
                metadata.dimensions = {"width": src.width, "height": src.height}
                metadata.crs = _describe_crs(src.crs)
                metadata.gsd_meters = _pixel_size_meters(src)

                footprint = _footprint_wgs84(src)
                if footprint:
                    metadata.footprint_polygon = {
                        "type": "Polygon",
                        "crs": "EPSG:4326",
                        "bounds": list(footprint),
                    }

                tags = src.tags()
                acquired = _first_tag(tags, TIMESTAMP_TAGS)
                if acquired:
                    metadata.acquisition_timestamp = _normalize_timestamp(acquired)

                platform = (_first_tag(tags, PLATFORM_TAGS) or "").lower()
                if platform and any(hint in platform for hint in SAR_PLATFORM_HINTS):
                    metadata.detected_modality = "sar"

                nodata, cloud = _stats(src)
                metadata.nodata_percent = round(nodata, 2)
                if metadata.detected_modality == "sar":
                    metadata.cloud_mask_percent = 0.0
                elif cloud is not None:
                    metadata.cloud_mask_percent = round(cloud, 2)

    def annotate_pair(self, images: List[ImageMetadata]) -> None:
        """Fills in the pair-level footprint overlap once both images are read.

        Overlap is the intersection-over-union of the two footprints' lon/lat bounding
        boxes. It is left as None when either image is not georeferenced, so a pair of
        plain PNGs is never rejected for an overlap nobody could measure.
        """
        if len(images) < 2:
            return
        a, b = (self._bounds(images[0]), self._bounds(images[1]))
        if a is None or b is None:
            return
        overlap = round(_footprint_iou(a, b), 2)
        for image in images[:2]:
            image.footprint_overlap_percent = overlap

    @staticmethod
    def _bounds(image: ImageMetadata) -> Optional[Footprint]:
        polygon = image.footprint_polygon
        if isinstance(polygon, dict) and polygon.get("bounds"):
            west, south, east, north = polygon["bounds"]
            return (west, south, east, north)
        return None


metadata_service = MetadataService()

"""The demo GeoTIFFs served from frontend/public/demo/, and what the backend makes of them.

Each authored raster must be readable by both rasterio (the metadata service) and Pillow (the
overlay renderer, which silently falls back to a synthetic canvas on failure), and must report the
georeferencing it was written with. tests/test_demo_parity.py sends these same files through the
pipeline and pins the outcome.
"""
import importlib.util
from pathlib import Path

import pytest
import rasterio
from PIL import Image

from backend.app.services.metadata_service import MetadataService

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "frontend" / "public" / "demo"

_spec = importlib.util.spec_from_file_location("make_demo_rasters", ROOT / "tools" / "make_demo_rasters.py")
make_demo_rasters = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(make_demo_rasters)
SPECS = {s.filename: s for s in make_demo_rasters.SPECS}

service = MetadataService()


@pytest.mark.parametrize("filename", list(SPECS))
def test_raster_is_checked_in(filename):
    assert (DEMO_DIR / filename).is_file(), f"run tools/make_demo_rasters.py: {filename} is missing"


@pytest.mark.parametrize("filename", list(SPECS))
def test_raster_opens_in_both_readers(filename):
    """Pillow must decode it, or overlay_service annotates a synthetic 640x640 canvas instead."""
    path = DEMO_DIR / filename
    with rasterio.open(path) as src:
        assert src.crs is not None and not src.transform.is_identity
    with Image.open(path) as img:
        img.load()
        assert img.size[0] > 0


@pytest.mark.parametrize("filename", list(SPECS))
def test_metadata_is_read_from_the_file(filename):
    spec = SPECS[filename]
    meta = service.inspect_file(str(DEMO_DIR / filename), filename)

    assert meta.crs == f"EPSG:{spec.epsg}"
    assert meta.gsd_meters == pytest.approx(spec.gsd)
    assert meta.footprint_polygon and meta.footprint_polygon["bounds"]
    assert meta.band_count == (1 if spec.sar else 3)
    assert meta.nodata_percent == 0.0
    modality = meta.detected_modality.value if hasattr(meta.detected_modality, "value") else meta.detected_modality
    assert (modality == "sar") == spec.sar
    if spec.acquired:
        assert meta.acquisition_timestamp == spec.acquired.rstrip("Z")
    else:
        assert meta.acquisition_timestamp is None  # unknown stays unknown, never invented


@pytest.mark.parametrize(
    "first, second",
    [
        ("Sentinel2_Bengaluru_2023.tif", "Sentinel2_Bengaluru_2025.tif"),
        ("Sentinel2_RGBNIR_Assam.tif", "Sentinel1_SAR_Assam_C_Band.tif"),
        ("Cartosat2S_Hyderabad.tif", "RISAT1_Hyderabad_DualPol.tif"),
    ],
)
def test_pair_footprints_coincide(first, second):
    """A pair shares its ground extent even when the pixel sizes differ."""
    images = [service.inspect_file(str(DEMO_DIR / n), n, i + 1) for i, n in enumerate((first, second))]
    service.annotate_pair(images)
    assert images[0].footprint_overlap_percent == pytest.approx(100.0, abs=0.5)


def test_temporal_pair_is_chronological():
    t1 = service.inspect_file(str(DEMO_DIR / "Sentinel2_Bengaluru_2023.tif"), "Sentinel2_Bengaluru_2023.tif")
    t2 = service.inspect_file(str(DEMO_DIR / "Sentinel2_Bengaluru_2025.tif"), "Sentinel2_Bengaluru_2025.tif")
    assert t1.acquisition_timestamp < t2.acquisition_timestamp

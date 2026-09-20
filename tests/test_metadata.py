"""Raster metadata extraction, and the preconditions it makes reachable.

Every fixture here is a real GeoTIFF written with rasterio. The point of the tests is
that CRS, overlap and ordering rejections fire on what is INSIDE a file; the previous
implementation read only the filename, so those rules could never trigger on real input.
"""
import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from backend.app.services.metadata_service import (
    MetadataService,
    _footprint_iou,
    _modality_from_filename,
    _normalize_timestamp,
)
from tests.conftest import analyze

service = MetadataService()

# A 2 km x 1 km scene near Bhopal in UTM zone 43N, at 10 m/pixel.
UTM43 = "EPSG:32643"
ORIGIN_X, ORIGIN_Y = 400_000.0, 2_600_000.0


def write_geotiff(
    path,
    *,
    origin=(ORIGIN_X, ORIGIN_Y),
    crs=UTM43,
    pixel=10.0,
    size=(200, 100),
    count=3,
    fill=120,
    dtype="uint8",
    nodata=None,
    tags=None,
    data=None,
):
    width, height = size
    profile = dict(
        driver="GTiff", height=height, width=width, count=count, dtype=dtype,
        crs=crs, transform=from_origin(origin[0], origin[1], pixel, pixel),
    )
    if nodata is not None:
        profile["nodata"] = nodata
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data if data is not None else np.full((count, height, width), fill, dtype=dtype))
        if tags:
            dst.update_tags(**tags)
    return str(path)


def upload(client, query, *paths):
    files = [("files", (p.rsplit("\\", 1)[-1].rsplit("/", 1)[-1], open(p, "rb").read(), "image/tiff")) for p in paths]
    response = client.post("/v1/analyze", data={"query": query}, files=files)
    assert response.status_code == 200, response.text
    return response.json()


# --- reading what the file says ---------------------------------------------------

def test_reads_crs_bands_dimensions_and_pixel_size(tmp_path):
    path = write_geotiff(tmp_path / "scene.tif", count=4)
    meta = service.inspect_file(path, "scene.tif")

    assert meta.crs == UTM43
    assert meta.band_count == 4
    assert meta.dimensions == {"width": 200, "height": 100}
    assert meta.gsd_meters == pytest.approx(10.0)
    assert meta.format == "geotiff"


def test_does_not_fabricate_a_crs_for_a_plain_png(tmp_path):
    """Every .tif used to receive 'EPSG:32643' regardless of its content."""
    from PIL import Image

    png = tmp_path / "scene.png"
    Image.new("RGB", (64, 64), (10, 20, 30)).save(png)
    meta = service.inspect_file(str(png), "scene.png")

    assert meta.crs is None
    assert meta.gsd_meters is None
    assert meta.footprint_polygon is None
    assert meta.dimensions == {"width": 64, "height": 64}


def test_an_unreadable_file_yields_unknowns_not_invented_values(tmp_path):
    bad = tmp_path / "broken.tif"
    bad.write_bytes(b"this is not a raster")
    meta = service.inspect_file(str(bad), "broken.tif")

    assert meta.format == "geotiff"
    assert meta.crs is None
    assert meta.gsd_meters is None
    assert meta.cloud_mask_percent is None, "the old code reported a made-up 12% here"


def test_footprint_is_expressed_in_wgs84(tmp_path):
    meta = service.inspect_file(write_geotiff(tmp_path / "s.tif"), "s.tif")
    west, south, east, north = meta.footprint_polygon["bounds"]

    assert meta.footprint_polygon["crs"] == "EPSG:4326"
    assert 74.0 < west < east < 74.1  # zone 43N, central meridian 75E
    assert 23.4 < south < north < 23.6


def test_acquisition_timestamp_is_parsed_from_tags(tmp_path):
    path = write_geotiff(tmp_path / "s.tif", tags={"TIFFTAG_DATETIME": "2024:03:05 10:30:00"})
    assert service.inspect_file(path, "s.tif").acquisition_timestamp == "2024-03-05T10:30:00"


def test_nodata_share_is_measured(tmp_path):
    data = np.full((1, 100, 200), 120, dtype="uint8")
    data[:, :, :100] = 0  # left half is NoData
    path = write_geotiff(tmp_path / "s.tif", count=1, data=data, nodata=0)
    assert service.inspect_file(path, "s.tif").nodata_percent == pytest.approx(50.0, abs=2.0)


# --- modality ---------------------------------------------------------------------

def test_sar_is_recognised_from_platform_metadata_not_only_the_filename(tmp_path):
    path = write_geotiff(tmp_path / "scene_0042.tif", count=2, tags={"PLATFORM": "Sentinel-1B"})
    assert service.inspect_file(path, "scene_0042.tif").detected_modality == "sar"


def test_sar_has_no_cloud_cover(tmp_path):
    path = write_geotiff(tmp_path / "s.tif", fill=250, tags={"PLATFORM": "RISAT-1"})
    assert service.inspect_file(path, "s.tif").cloud_mask_percent == 0.0


@pytest.mark.parametrize(
    "name, expected",
    [
        ("sar_s1.png", "sar"),
        ("Sentinel1_VV.tif", "sar"),
        ("RISAT1_strip.tif", "sar"),
        ("scene_ms.tif", "multispectral"),
        ("Sentinel2_Wetlands.png", "multispectral"),
        ("optical_port.png", "optical"),
        # Short hints must be whole tokens; these used to be misclassified.
        ("farms.png", "optical"),
        ("class1.png", "optical"),
    ],
)
def test_filename_fallback_matches_tokens_not_substrings(name, expected):
    assert _modality_from_filename(name) == expected


# --- cloud approximation ----------------------------------------------------------

def test_bright_optical_imagery_reads_as_cloudy(tmp_path):
    cloudy = service.inspect_file(write_geotiff(tmp_path / "c.tif", fill=250), "c.tif")
    clear = service.inspect_file(write_geotiff(tmp_path / "k.tif", fill=90), "k.tif")

    assert cloudy.cloud_mask_percent == pytest.approx(100.0)
    assert clear.cloud_mask_percent == pytest.approx(0.0)


def test_cloud_share_is_unknown_for_non_8bit_data(tmp_path):
    """A 16-bit scene has no fixed brightness scale; guessing one would flag the
    brightest few percent of ANY image as cloud."""
    path = write_geotiff(tmp_path / "s.tif", dtype="uint16", fill=3000)
    assert service.inspect_file(path, "s.tif").cloud_mask_percent is None


# --- pair overlap -----------------------------------------------------------------

def test_footprint_iou_of_identical_and_disjoint_boxes():
    box = (74.0, 23.4, 74.1, 23.5)
    assert _footprint_iou(box, box) == pytest.approx(100.0)
    assert _footprint_iou(box, (75.0, 24.0, 75.1, 24.1)) == 0.0


def test_pair_overlap_is_annotated_on_both_images(tmp_path):
    a = service.inspect_file(write_geotiff(tmp_path / "a.tif"), "a.tif", 1)
    b = service.inspect_file(write_geotiff(tmp_path / "b.tif", origin=(ORIGIN_X + 1000, ORIGIN_Y)), "b.tif", 2)
    service.annotate_pair([a, b])

    # Shifted by half a 2 km scene: intersection 1 km^2 over union 3 km^2.
    assert a.footprint_overlap_percent == pytest.approx(33.3, abs=1.0)
    assert b.footprint_overlap_percent == a.footprint_overlap_percent


def test_overlap_is_left_unknown_when_either_image_is_not_georeferenced(tmp_path):
    from PIL import Image

    png = tmp_path / "p.png"
    Image.new("RGB", (32, 32)).save(png)
    a = service.inspect_file(write_geotiff(tmp_path / "a.tif"), "a.tif", 1)
    b = service.inspect_file(str(png), "p.png", 2)
    service.annotate_pair([a, b])

    assert a.footprint_overlap_percent is None


# --- end to end: the rules that could never fire before ---------------------------

CHANGE = "what changed between these two dates?"


def test_low_footprint_overlap_is_rejected_on_real_rasters(client, tmp_path):
    far = write_geotiff(tmp_path / "far.tif", origin=(ORIGIN_X + 1800, ORIGIN_Y))
    near = write_geotiff(tmp_path / "near.tif")
    res = upload(client, CHANGE, near, far)

    assert res["rejected"] is True
    assert res["rejectionDetails"]["reasonCode"] == "insufficient_footprint_overlap"


def test_a_well_overlapping_pair_is_accepted(client, tmp_path):
    a = write_geotiff(tmp_path / "t1.tif", tags={"TIFFTAG_DATETIME": "2023:01:01 00:00:00"})
    b = write_geotiff(tmp_path / "t2.tif", tags={"TIFFTAG_DATETIME": "2024:01:01 00:00:00"})
    res = upload(client, CHANGE, a, b)

    assert res["rejected"] is False


def test_an_unresolvable_local_crs_is_rejected(client, tmp_path):
    local = CRS.from_wkt(
        'LOCAL_CS["Site grid",LOCAL_DATUM["Site datum",0],UNIT["metre",1],AXIS["X",EAST],AXIS["Y",NORTH]]'
    )
    a = write_geotiff(tmp_path / "t1.tif", crs=local)
    b = write_geotiff(tmp_path / "t2.tif")
    res = upload(client, CHANGE, a, b)

    assert res["rejected"] is True
    assert res["rejectionDetails"]["reasonCode"] == "crs_mismatch_unresolvable"


def test_reversed_acquisition_order_is_rejected(client, tmp_path):
    later = write_geotiff(tmp_path / "t1.tif", tags={"TIFFTAG_DATETIME": "2024:06:01 00:00:00"})
    earlier = write_geotiff(tmp_path / "t2.tif", tags={"TIFFTAG_DATETIME": "2023:01:01 00:00:00"})
    res = upload(client, CHANGE, later, earlier)

    assert res["rejected"] is True
    assert res["rejectionDetails"]["reasonCode"] == "temporal_ordering_invalid"


def test_optical_and_sar_are_told_apart_by_metadata_alone(client, tmp_path):
    """Neither filename hints at a sensor; only the tag does. Change detection over an
    optical/SAR pair is the system's signature rejection."""
    optical = write_geotiff(tmp_path / "scene_a.tif")
    sar = write_geotiff(tmp_path / "scene_b.tif", count=2, tags={"PLATFORM": "Sentinel-1A"})
    res = upload(client, CHANGE, optical, sar)

    assert res["rejected"] is True
    assert res["rejectionDetails"]["reasonCode"] == "modality_mismatch"


def test_nodata_warning_uses_the_configured_threshold(tmp_path):
    from backend.app.orchestrator.compatibility_validator import CompatibilityValidator
    from backend.app.schemas.task_spec import TaskSpec, TaskType

    data = np.full((1, 100, 200), 120, dtype="uint8")
    data[:, :, :150] = 0  # 75% NoData, above the 40% default
    meta = service.inspect_file(write_geotiff(tmp_path / "s.tif", count=1, data=data, nodata=0), "s.tif")

    result = CompatibilityValidator().validate(
        TaskSpec(task_type=TaskType.SINGLE_VQA, question_text="count the tanks"), [meta]
    )
    assert any("NoData" in w for w in result.warnings)


def test_timestamp_formats():
    assert _normalize_timestamp("2024:03:05 10:30:00") == "2024-03-05T10:30:00"
    assert _normalize_timestamp("2024-03-05") == "2024-03-05T00:00:00"
    assert _normalize_timestamp("20240305") == "2024-03-05T00:00:00"
    assert _normalize_timestamp("not a date") is None

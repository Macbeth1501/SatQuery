"""POST /v1/inspect: what the upload card shows comes from the file, not from a guess.

The studio used to invent metadata for every upload (EPSG:32643 and 0.65 m for any TIFF) and could
not preview a TIFF at all. It now asks this endpoint, which reuses the analysis pipeline's own
metadata reader and renders a PNG preview.
"""
import base64
import io
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "frontend" / "public" / "real" / "bigearthnet_T29UPU_55_58.tif"
DEMO_SAR = ROOT / "frontend" / "public" / "demo" / "Sentinel1_SAR_Assam_C_Band.tif"


def inspect(client, name, data):
    response = client.post("/v1/inspect", files={"file": (name, data, "application/octet-stream")})
    assert response.status_code == 200, response.text
    return response.json()


def preview_image(body):
    url = body["previewDataUrl"]
    assert url.startswith("data:image/png;base64,")
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1])))


def test_geotiff_facts_are_read_from_the_file(client):
    pytest.importorskip("rasterio")
    body = inspect(client, REAL.name, REAL.read_bytes())
    meta = body["metadata"]
    assert meta["name"] == REAL.name
    assert meta["crs"] == "EPSG:32629"
    assert meta["gsdMeters"] == 10.0
    assert meta["bandCount"] == 3
    assert meta["acquisitionTimestamp"].startswith("2017-11-12")
    assert preview_image(body).size == (120, 120)  # a TIFF the browser can now display


def test_single_band_sar_tiff_gets_a_preview_and_its_modality(client):
    pytest.importorskip("rasterio")
    body = inspect(client, DEMO_SAR.name, DEMO_SAR.read_bytes())
    assert body["metadata"]["detectedModality"] == "sar"
    assert preview_image(body).mode == "RGB"


def test_sixteen_bit_raster_is_stretched_for_display(client, tmp_path):
    rasterio = pytest.importorskip("rasterio")
    np = pytest.importorskip("numpy")
    path = tmp_path / "dn16.tif"
    data = (np.arange(64 * 64, dtype="uint16").reshape(1, 64, 64) * 3)
    with rasterio.open(path, "w", driver="GTiff", dtype="uint16", count=1, width=64, height=64) as dst:
        dst.write(data)
    body = inspect(client, "dn16.tif", path.read_bytes())
    image = preview_image(body)
    assert image.size == (64, 64)
    low, high = image.convert("L").getextrema()
    assert high - low > 200  # stretched, not a black square


def test_plain_png_reports_no_georeference_rather_than_inventing_one(client):
    buffer = io.BytesIO()
    Image.new("RGB", (32, 16), (40, 120, 60)).save(buffer, format="PNG")
    body = inspect(client, "photo.png", buffer.getvalue())
    meta = body["metadata"]
    assert meta["crs"] is None
    assert meta["gsdMeters"] is None
    assert meta["acquisitionTimestamp"] is None
    assert preview_image(body).size == (32, 16)


def test_undecodable_file_gives_unknowns_and_no_preview(client):
    body = inspect(client, "notes.txt", b"not an image")
    assert body["previewDataUrl"] is None
    assert body["metadata"]["crs"] is None


def test_client_filename_is_a_label_not_a_path(client, isolated_storage):
    body = inspect(client, "../../escape.png", b"x")
    assert body["metadata"]["name"] == "escape.png"
    assert not (isolated_storage.parent / "escape.png").exists()
    assert not list(isolated_storage.rglob("escape.png"))


def test_large_image_preview_is_capped(client):
    buffer = io.BytesIO()
    Image.new("RGB", (2000, 1000), (10, 20, 30)).save(buffer, format="PNG")
    body = inspect(client, "big.png", buffer.getvalue())
    assert max(preview_image(body).size) == 512

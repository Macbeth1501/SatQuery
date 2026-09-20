"""API contract tests: endpoints, session persistence and report export."""
import io

from PIL import Image

from tests.conftest import analyze


def test_health(client):
    body = client.get("/v1/health").json()
    assert body["status"] == "ok"
    assert body["service"]


def test_registry_lists_specialists_and_preconditions(client):
    body = client.get("/v1/registry").json()
    assert len(body["specialists"]) == 4
    codes = {p["code"] for p in body["preconditions"]}
    assert "modality_mismatch" in codes
    assert "ambiguous_intent" in codes


def test_analyze_rejects_more_than_two_images(client):
    files = [("files", (f"img{i}.png", b"x", "image/png")) for i in range(3)]
    response = client.post("/v1/analyze", data={"query": "count the tanks"}, files=files)
    assert response.status_code == 400


def test_analyze_returns_trace_and_report_url(client):
    res = analyze(client, "how many fuel storage tanks are visible?", ["optical_port.png"])
    assert res["sessionId"].startswith("sq-")
    assert res["executionTrace"]["steps"]
    assert res["reportUrl"] == f"/v1/session/{res['sessionId']}/report"


def test_session_round_trip_and_reports(client):
    res = analyze(client, "describe the land-cover and major objects visible in this image.", ["optical_port.png"])
    session_id = res["sessionId"]

    fetched = client.get(f"/v1/session/{session_id}")
    assert fetched.status_code == 200
    assert fetched.json()["sessionId"] == session_id

    as_json = client.get(f"/v1/session/{session_id}/report?format=json")
    assert as_json.status_code == 200
    assert as_json.json()["sessionId"] == session_id

    as_html = client.get(f"/v1/session/{session_id}/report?format=html")
    assert as_html.status_code == 200
    assert "SatQuery AI" in as_html.text

    as_pdf = client.get(f"/v1/session/{session_id}/report?format=pdf")
    assert as_pdf.status_code == 200
    assert as_pdf.headers["content-type"] == "application/pdf"
    assert as_pdf.content.startswith(b"%PDF-")


def test_unknown_session_is_404(client):
    assert client.get("/v1/session/sq-doesnotexist").status_code == 404


def test_report_badge_matches_confidence_tier(client):
    """The report badge was hardcoded to the green High style for every tier."""
    res = analyze(client, "highlight the water body referred to in the query.", ["optical_port.png"])
    html = client.get(f"/v1/session/{res['sessionId']}/report?format=html").text
    expected = {"High": "badge-high", "Medium": "badge-med", "Low": "badge-low"}[res["confidence"]["tier"]]
    assert f'class="badge {expected}"' in html


def test_overlay_image_is_served(client):
    res = analyze(client, "count the fuel storage tanks", ["optical_port.png"])
    session = client.get(f"/v1/session/{res['sessionId']}").json()
    overlay_url = session["evidence"]["overlayImageUrls"][0]
    assert client.get(overlay_url).status_code == 200


def test_pdf_report_is_rendered_and_cached(client, isolated_storage):
    """?format=pdf used to return printable HTML; it now returns a real PDF."""
    res = analyze(client, "how many fuel storage tanks are visible?", ["optical_port.png"])
    session_id = res["sessionId"]
    cached = isolated_storage / "sessions" / session_id / "report.pdf"
    assert not cached.exists()

    first = client.get(f"/v1/session/{session_id}/report?format=pdf")
    assert first.status_code == 200
    assert first.content.startswith(b"%PDF-")
    assert cached.is_file(), "the rendered PDF should be cached on the session"

    second = client.get(f"/v1/session/{session_id}/report?format=pdf")
    assert second.content == first.content


def test_report_carries_evidence_images_and_boxes(client):
    """Content parity: the report must show the evidence the Results page shows."""
    res = analyze(client, "how many fuel storage tanks are visible?", ["optical_port.png"])
    html = client.get(f"/v1/session/{res['sessionId']}/report?format=html").text
    for overlay_url in res["evidence"]["overlayImageUrls"]:
        assert overlay_url in html
    for box in res["evidence"]["boxes"]:
        assert box["label"] in html


def test_rejected_session_has_no_report(client):
    """A rejection produced no analysis, so there is nothing to report."""
    res = analyze(client, "what changed between these two dates?", ["optical.png", "sar_s1.png"])
    assert res["rejected"] is True
    for fmt in ("pdf", "json", "html"):
        conflict = client.get(f"/v1/session/{res['sessionId']}/report?format={fmt}")
        assert conflict.status_code == 409
        assert "rejection reason" in conflict.json()["detail"]


def _png_bytes(width: int, height: int) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (34, 74, 46)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_overlay_is_drawn_on_the_uploaded_image(client, isolated_storage):
    """A decodable upload must be annotated, not replaced by the fallback canvas.

    The frontend used to post placeholder bytes for demo scenarios, so every demo
    overlay was drawn on a synthetic 640x640 scene instead of the imagery on screen.
    """
    response = client.post(
        "/v1/analyze",
        data={"query": "how many fuel storage tanks are visible?"},
        files=[("files", ("optical_port.png", _png_bytes(600, 400), "image/png"))],
    )
    assert response.status_code == 200
    session_id = response.json()["sessionId"]

    overlay = isolated_storage / "sessions" / session_id / "evidence" / "evidence_boxes_overlay.png"
    assert overlay.is_file()
    with Image.open(overlay) as img:
        assert img.size == (600, 400), "overlay should match the uploaded raster"


def test_undecodable_upload_still_produces_an_overlay(client, isolated_storage):
    """The synthetic fallback canvas is still needed when an upload cannot be opened."""
    response = client.post(
        "/v1/analyze",
        data={"query": "how many fuel storage tanks are visible?"},
        files=[("files", ("optical_port.png", b"not-an-image", "image/png"))],
    )
    session_id = response.json()["sessionId"]

    overlay = isolated_storage / "sessions" / session_id / "evidence" / "evidence_boxes_overlay.png"
    with Image.open(overlay) as img:
        assert img.size == (640, 640)

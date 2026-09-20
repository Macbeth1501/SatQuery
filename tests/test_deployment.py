"""Deployment-readiness checks (Track D): health, startup migration, offline, concurrency.

The offline requirement (SPDD 13.5) is that a full analyze cycle needs no external network.
The backend half is enforced here by refusing every non-loopback connection while all six
demos, the session lookup and every report format run. The browser half is enforced by
scanning the frontend sources for CDN hosts (a font CDN was found and removed for this).
"""
import ipaddress
import re
import socket
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app import config
from backend.app.services import session_repository
from tests.conftest import analyze
from tests.test_demo_parity import DEMOS, project

REPO_ROOT = Path(__file__).resolve().parents[1]


# -- health and startup ------------------------------------------------------------


def test_health_reports_the_database_schema_version(client):
    body = client.get("/v1/health").json()
    assert body["status"] == "ok"
    assert body["database"]["schemaVersion"] == session_repository.SCHEMA_VERSION


def test_health_is_503_when_the_database_cannot_be_opened(client, monkeypatch):
    def broken(_self):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(session_repository.SessionRepository, "schema_version", broken)
    response = client.get("/v1/health")
    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"


def test_startup_creates_and_migrates_the_database_before_any_request(tmp_path, monkeypatch):
    db_path = tmp_path / "fresh" / "satquery.db"
    monkeypatch.setattr(config, "DATABASE_PATH", db_path)
    assert not db_path.exists()

    from backend.app.main import app

    with TestClient(app):  # entering the context runs startup, and makes no request
        assert db_path.exists()
        with sqlite3.connect(db_path) as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == session_repository.SCHEMA_VERSION


def test_startup_refuses_a_database_from_a_newer_build(tmp_path, monkeypatch):
    db_path = tmp_path / "newer.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(f"PRAGMA user_version = {session_repository.SCHEMA_VERSION + 1}")
    monkeypatch.setattr(config, "DATABASE_PATH", db_path)

    from backend.app.main import app

    with pytest.raises(session_repository.SchemaVersionError):
        with TestClient(app):
            pass


# -- offline -----------------------------------------------------------------------


def _is_loopback(address) -> bool:
    host = address[0] if isinstance(address, tuple) else address
    if isinstance(host, bytes):
        host = host.decode()
    if not isinstance(host, str):  # e.g. an AF_UNIX path
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host in ("localhost", "")


@pytest.fixture
def outbound_attempts(monkeypatch):
    """Refuses any non-loopback connection and records that it was attempted."""
    attempts = []
    real_connect = socket.socket.connect

    def guarded_connect(self, address):
        if not _is_loopback(address):
            attempts.append(address)
            raise OSError(f"outbound connection blocked by the offline test: {address}")
        return real_connect(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    return attempts


def test_the_offline_guard_actually_blocks(outbound_attempts):
    """Guards the guard: if this passes vacuously, the offline test below proves nothing."""
    with pytest.raises(OSError):
        socket.socket().connect(("203.0.113.9", 443))
    assert outbound_attempts == [("203.0.113.9", 443)]


def test_full_analyze_cycle_makes_no_outbound_connection(client, outbound_attempts):
    for query, files in DEMOS.values():
        response = analyze(client, query, files)
        if not response["rejected"]:
            session_id = response["sessionId"]
            assert client.get(f"/v1/session/{session_id}").status_code == 200
            for fmt in ("json", "html", "pdf"):
                assert client.get(f"/v1/session/{session_id}/report?format={fmt}").status_code == 200
    assert outbound_attempts == []


CDN_HOSTS = re.compile(
    r"fonts\.googleapis|fonts\.gstatic|cdnjs\.|cdn\.jsdelivr|unpkg\.com|ajax\.googleapis|"
    r"stackpath\.|bootstrapcdn|use\.fontawesome",
    re.IGNORECASE,
)


def _frontend_files():
    yield REPO_ROOT / "frontend" / "index.html"
    yield from (REPO_ROOT / "frontend" / "src").rglob("*.css")
    yield from (REPO_ROOT / "frontend" / "src").rglob("*.ts*")
    dist = REPO_ROOT / "frontend" / "dist"
    if dist.exists():  # present after a build; CI always builds before this runs
        yield from dist.rglob("*.html")
        yield from dist.rglob("*.css")
        yield from dist.rglob("*.js")


def test_frontend_loads_nothing_from_a_cdn():
    offenders = [
        str(path.relative_to(REPO_ROOT))
        for path in _frontend_files()
        if path.is_file() and CDN_HOSTS.search(path.read_text(encoding="utf-8", errors="ignore"))
    ]
    assert offenders == [], f"CDN references would break the offline requirement: {offenders}"


# -- concurrency -------------------------------------------------------------------


def test_three_concurrent_analyses_all_succeed_with_distinct_sessions(client):
    """Appendix A #23: the three-concurrent-requests target had never been exercised."""
    demo_ids = ["scenario_a", "scenario_c", "scenario_d"]

    def run(demo_id):
        query, files = DEMOS[demo_id]
        return demo_id, analyze(client, query, files)

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = dict(pool.map(run, demo_ids))

    outcomes = {demo_id: r["executionTrace"]["selectedTaskType"] for demo_id, r in results.items()}
    assert outcomes == {"scenario_a": "single_caption", "scenario_c": "change_vqa", "scenario_d": "fusion"}
    assert len({r["sessionId"] for r in results.values()}) == 3
    # each request kept its own answer; nothing bled between sessions
    assert len({r["answerText"] for r in results.values()}) == 3
    for r in results.values():
        assert client.get(f"/v1/session/{r['sessionId']}").status_code == 200

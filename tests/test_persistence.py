"""A3: sessions survive a restart and can be queried (SPDD section 10.2)."""
import json
import sqlite3

import pytest

from backend.app import config
from backend.app.services.session_repository import (
    SCHEMA_VERSION,
    SchemaVersionError,
    SessionRepository,
)
from backend.app.services.storage_service import StorageService
from tests.conftest import analyze


def test_session_survives_restart(client):
    body = analyze(client, "Describe the land cover in this image.", ["scene.png"])
    sid = body["sessionId"]

    # A fresh StorageService and repository stand in for a process restart: nothing is
    # cached in memory, so anything returned came from the database file.
    restarted = StorageService()
    reloaded = restarted.get_session_response(sid)

    assert reloaded is not None
    assert reloaded.model_dump(by_alias=True, mode="json") == client.get(f"/v1/session/{sid}").json()
    assert reloaded.answer_text == body["answerText"]


def test_session_is_read_from_the_database_not_the_json_file(client):
    sid = analyze(client, "Describe the land cover in this image.", ["scene.png"])["sessionId"]
    legacy = config.SESSIONS_DIR / sid / "response.json"
    if legacy.exists():
        legacy.unlink()
    assert client.get(f"/v1/session/{sid}").status_code == 200


def test_rejection_round_trips(client):
    body = analyze(client, "What changed between these two images?", ["optical.tif", "sar_vv.tif"])
    assert body["rejected"] is True
    reloaded = StorageService().get_session_response(body["sessionId"])
    assert reloaded.rejected is True
    assert reloaded.model_dump(by_alias=True, mode="json")["rejectionReason"] == body["rejectionReason"]


def test_unknown_session_is_none(client):
    assert StorageService().get_session_response("sq-deadbeef") is None
    assert StorageService().get_session_response("../etc") is None


def test_list_and_filter_sessions(client):
    ok = analyze(client, "Describe the land cover in this image.", ["scene.png"])["sessionId"]
    rej = analyze(client, "What changed between these two images?", ["optical.tif", "sar_vv.tif"])["sessionId"]
    repo = StorageService().repository

    rejected_ids = {s["session_id"] for s in repo.list_sessions(rejected=True)}
    accepted_ids = {s["session_id"] for s in repo.list_sessions(rejected=False)}
    assert rej in rejected_ids and rej not in accepted_ids
    assert ok in accepted_ids
    assert repo.count_sessions(rejected=True) == len(repo.list_sessions(rejected=True, limit=500))
    assert any(s["session_id"] == ok for s in repo.list_sessions(query_contains="land cover"))


def test_like_wildcards_match_literally(tmp_path, client):
    sid = analyze(client, "Describe the land cover in this image.", ["scene.png"])["sessionId"]
    repo = StorageService().repository
    assert repo.list_sessions(query_contains="%") == [] or all(
        "%" in (s["query_text"] or "") for s in repo.list_sessions(query_contains="%")
    )
    assert repo.count_sessions(query_contains="land_cover") == 0  # _ is not a wildcard


def test_save_is_idempotent_and_updates(tmp_path, client):
    sid = analyze(client, "Describe the land cover in this image.", ["scene.png"])["sessionId"]
    response = StorageService().get_session_response(sid)
    repo = SessionRepository(tmp_path / "other.db")
    repo.save_session(response)
    repo.save_session(response.model_copy(update={"answer_text": "edited"}))
    assert repo.count_sessions() == 1
    assert repo.get_session(sid).answer_text == "edited"


def test_delete_cascades(tmp_path, client):
    sid = analyze(client, "Describe the land cover in this image.", ["scene.png"])["sessionId"]
    repo = SessionRepository(tmp_path / "d.db")
    repo.save_session(StorageService().get_session_response(sid))
    assert repo.delete_session(sid) is True
    with sqlite3.connect(repo.db_path) as conn:
        for table in ("evidence_ledgers", "execution_traces"):
            assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_migration_is_idempotent_and_versioned(tmp_path):
    a = SessionRepository(tmp_path / "m.db")
    b = SessionRepository(tmp_path / "m.db")
    assert a.schema_version() == b.schema_version() == SCHEMA_VERSION


def test_newer_database_is_refused(tmp_path):
    path = tmp_path / "future.db"
    with sqlite3.connect(path) as conn:
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")
    with pytest.raises(SchemaVersionError):
        SessionRepository(path)


def test_legacy_json_session_is_imported(client):
    sid = analyze(client, "Describe the land cover in this image.", ["scene.png"])["sessionId"]
    doc = client.get(f"/v1/session/{sid}").json()
    legacy_id = "sq-legacy01"
    d = config.SESSIONS_DIR / legacy_id
    d.mkdir(parents=True, exist_ok=True)
    doc["sessionId"] = legacy_id
    (d / "response.json").write_text(json.dumps(doc), encoding="utf-8")
    assert StorageService().repository.get_session(legacy_id) is None
    assert client.get(f"/v1/session/{legacy_id}").status_code == 200
    assert StorageService().repository.get_session(legacy_id) is not None

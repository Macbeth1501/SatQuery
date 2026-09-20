"""Shared fixtures for the SatQuery AI test suite.

Every test runs in-process against a FastAPI TestClient, so no server has to be
started by hand. Session artefacts are written to a temporary storage root so a
test run never pollutes backend/storage.
"""
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def isolated_storage():
    """Redirects session storage at import time to a throwaway directory."""
    tmp_root = Path(tempfile.mkdtemp(prefix="satquery-tests-"))
    sessions = tmp_root / "sessions"
    sessions.mkdir(parents=True, exist_ok=True)

    from backend.app import config
    from backend.app.services import storage_service as storage_module

    config.STORAGE_DIR = tmp_root
    config.SESSIONS_DIR = sessions
    config.DATABASE_PATH = tmp_root / "satquery.db"
    storage_module.SESSIONS_DIR = sessions

    yield tmp_root
    shutil.rmtree(tmp_root, ignore_errors=True)


@pytest.fixture(scope="session")
def client(isolated_storage):
    from backend.app.main import app

    with TestClient(app) as test_client:
        yield test_client


def analyze(client, query, filenames=(), session_options=None):
    """Posts a multipart /v1/analyze request and returns the decoded response."""
    files = [("files", (name, b"satquery_test_bytes", "image/png")) for name in filenames]
    data = {"query": query}
    if session_options is not None:
        data["session_options"] = session_options
    response = client.post("/v1/analyze", data=data, files=files or None)
    assert response.status_code == 200, response.text
    return response.json()

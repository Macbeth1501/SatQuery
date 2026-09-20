import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
from fastapi import UploadFile
from backend.app import config
from backend.app.config import SESSIONS_DIR
from backend.app.schemas.api_models import AnalyzeResponse
from backend.app.services.session_repository import SessionRepository


class StorageService:
    """Files on disk, structured session records in SQLite.

    Uploads, overlays and rendered reports live under SESSIONS_DIR/<session_id>/. The
    session record itself (answer, evidence, confidence, trace) lives in the database,
    which is the single source of truth -- there is no separate in-memory copy to drift.
    """

    def __init__(self):
        self._repositories: Dict[str, SessionRepository] = {}

    @property
    def repository(self) -> SessionRepository:
        """The repository for the currently configured database.

        Resolved at call time, not import time, because the path comes from config and
        the test suite redirects it after this module is already imported.
        """
        key = str(config.DATABASE_PATH)
        if key not in self._repositories:
            self._repositories[key] = SessionRepository(config.DATABASE_PATH)
        return self._repositories[key]

    def get_session_dir(self, session_id: str) -> Path:
        session_dir = SESSIONS_DIR / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "inputs").mkdir(exist_ok=True)
        (session_dir / "evidence").mkdir(exist_ok=True)
        return session_dir

    async def save_uploaded_files(
        self, session_id: str, files: List[UploadFile]
    ) -> List[Dict[str, str]]:
        session_dir = self.get_session_dir(session_id)
        inputs_dir = session_dir / "inputs"
        saved_files = []

        for idx, file in enumerate(files):
            original_name = file.filename or f"image_{idx + 1}.bin"
            stored_name = f"image_{idx + 1}_{original_name}"
            file_path = inputs_dir / stored_name

            # Calculate content hash while saving
            hasher = hashlib.sha256()
            with open(file_path, "wb") as f:
                content = await file.read()
                hasher.update(content)
                f.write(content)

            saved_files.append({
                "filename": original_name,
                "stored_name": stored_name,
                "path": str(file_path),
                "content_hash": hasher.hexdigest(),
                "size_bytes": len(content),
            })

        return saved_files

    def store_session_response(
        self, session_id: str, response: AnalyzeResponse, query: Optional[str] = None
    ) -> None:
        # Make sure the session directory exists even for a rejected analysis, so a
        # later report or upload lookup never trips over a missing folder.
        self.get_session_dir(session_id)
        self.repository.save_session(response, query_text=query)

    def get_session_response(self, session_id: str) -> Optional[AnalyzeResponse]:
        found = self.repository.get_session(session_id)
        if found is not None:
            return found
        return self._import_legacy_session(session_id)

    def _import_legacy_session(self, session_id: str) -> Optional[AnalyzeResponse]:
        """Adopts a session written by the pre-database version, once, on first read.

        Earlier versions kept each session as SESSIONS_DIR/<id>/response.json. Reading
        one imports it into the database, so sessions from before the upgrade stay
        reachable without a separate migration step. The JSON file is left in place.
        """
        # Session ids come from a URL path; refuse anything that could escape SESSIONS_DIR.
        if not session_id or session_id != Path(session_id).name:
            return None
        legacy = SESSIONS_DIR / session_id / "response.json"
        if not legacy.is_file():
            return None
        try:
            response = AnalyzeResponse.model_validate(json.loads(legacy.read_text(encoding="utf-8")))
        except Exception:
            return None
        self.repository.save_session(response)
        return response


storage_service = StorageService()

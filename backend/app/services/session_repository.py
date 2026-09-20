"""SQLite persistence for analysis sessions (SPDD section 10.2).

Three tables -- `sessions`, `evidence_ledgers`, `execution_traces` -- so sessions can be
queried by task type, outcome, confidence tier or query text, and survive a restart.
Images, overlays and rendered reports stay on the filesystem; only the structured
records live here.

This uses the standard library's sqlite3 rather than SQLAlchemy and Alembic. For three
tables that would add two dependencies and a migration framework for no gain. All SQL is
confined to this module, so moving to another engine later touches one file. Schema
changes go through the MIGRATIONS list, applied in order and tracked with SQLite's
`PRAGMA user_version`, so opening an existing database is always safe and idempotent.

A connection is opened per operation. SQLite handles that cheaply, it keeps the
repository safe to call from FastAPI's worker threads, and it means no connection can be
left open across a restart.
"""
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from backend.app.schemas.api_models import AnalyzeResponse

# Each entry is one schema version. Never edit an applied migration; append a new one.
MIGRATIONS: List[str] = [
    """
    CREATE TABLE sessions (
        session_id       TEXT PRIMARY KEY,
        created_at       TEXT NOT NULL,
        query_text       TEXT,
        task_type        TEXT NOT NULL,
        rejected         INTEGER NOT NULL DEFAULT 0,
        confidence_tier  TEXT NOT NULL,
        answer_text      TEXT,
        report_url       TEXT,
        confidence_json  TEXT NOT NULL,
        rejection_json   TEXT,
        task_spec_json   TEXT
    );
    CREATE TABLE evidence_ledgers (
        session_id   TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
        ledger_json  TEXT NOT NULL
    );
    CREATE TABLE execution_traces (
        session_id  TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
        trace_json  TEXT NOT NULL
    );
    CREATE INDEX idx_sessions_created_at ON sessions(created_at);
    CREATE INDEX idx_sessions_task_type ON sessions(task_type);
    CREATE INDEX idx_sessions_outcome ON sessions(rejected, confidence_tier);
    """,
]

SCHEMA_VERSION = len(MIGRATIONS)


class SchemaVersionError(RuntimeError):
    """The database was written by a newer version of the application."""


def _dump(model: Any) -> str:
    return json.dumps(model, ensure_ascii=False, separators=(",", ":"))


class SessionRepository:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._migrate()

    # -- connection and schema ---------------------------------------------------

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            with conn:  # commits on success, rolls back on error
                yield conn
        finally:
            conn.close()

    def _migrate(self) -> None:
        with closing(sqlite3.connect(self.db_path, timeout=15)) as conn:
            # WAL lets a reader proceed while a write is in flight.
            conn.execute("PRAGMA journal_mode = WAL")
            current = conn.execute("PRAGMA user_version").fetchone()[0]
            if current > SCHEMA_VERSION:
                raise SchemaVersionError(
                    f"{self.db_path} is schema version {current}, but this application "
                    f"only understands up to version {SCHEMA_VERSION}. Upgrade the "
                    "application rather than reading a newer database with an older one."
                )
            for version in range(current, SCHEMA_VERSION):
                conn.executescript("BEGIN;\n" + MIGRATIONS[version] + f"\nPRAGMA user_version = {version + 1};\nCOMMIT;")

    def schema_version(self) -> int:
        with closing(sqlite3.connect(self.db_path)) as conn:
            return conn.execute("PRAGMA user_version").fetchone()[0]

    # -- writes ------------------------------------------------------------------

    def save_session(self, response: AnalyzeResponse, query_text: Optional[str] = None) -> None:
        """Inserts or updates a session and its ledger and trace in one transaction."""
        payload = response.model_dump(by_alias=True, mode="json")
        trace = payload["executionTrace"]
        query = query_text
        if query is None and payload.get("taskSpec"):
            query = payload["taskSpec"].get("questionText")

        rejection = None
        if payload.get("rejected"):
            rejection = _dump(
                {"reason": payload.get("rejectionReason"), "details": payload.get("rejectionDetails")}
            )

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, created_at, query_text, task_type, rejected, confidence_tier,
                    answer_text, report_url, confidence_json, rejection_json, task_spec_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    query_text = excluded.query_text,
                    task_type = excluded.task_type,
                    rejected = excluded.rejected,
                    confidence_tier = excluded.confidence_tier,
                    answer_text = excluded.answer_text,
                    report_url = excluded.report_url,
                    confidence_json = excluded.confidence_json,
                    rejection_json = excluded.rejection_json,
                    task_spec_json = excluded.task_spec_json
                """,
                (
                    payload["sessionId"],
                    datetime.now(timezone.utc).isoformat(),
                    query,
                    trace["selectedTaskType"],
                    1 if payload.get("rejected") else 0,
                    payload["confidence"]["tier"],
                    payload.get("answerText"),
                    payload.get("reportUrl"),
                    _dump(payload["confidence"]),
                    rejection,
                    _dump(payload["taskSpec"]) if payload.get("taskSpec") else None,
                ),
            )
            conn.execute(
                "INSERT INTO evidence_ledgers (session_id, ledger_json) VALUES (?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET ledger_json = excluded.ledger_json",
                (payload["sessionId"], _dump(payload["evidence"])),
            )
            conn.execute(
                "INSERT INTO execution_traces (session_id, trace_json) VALUES (?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET trace_json = excluded.trace_json",
                (payload["sessionId"], _dump(trace)),
            )

    def delete_session(self, session_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            return cursor.rowcount > 0

    # -- reads -------------------------------------------------------------------

    def session_exists(self, session_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            return row is not None

    def get_session(self, session_id: str) -> Optional[AnalyzeResponse]:
        """Rebuilds the full AnalyzeResponse by joining the three tables."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT s.*, e.ledger_json, t.trace_json
                FROM sessions s
                JOIN evidence_ledgers e ON e.session_id = s.session_id
                JOIN execution_traces t ON t.session_id = s.session_id
                WHERE s.session_id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None

        rejection = json.loads(row["rejection_json"]) if row["rejection_json"] else {}
        document = {
            "sessionId": row["session_id"],
            "answerText": row["answer_text"],
            "evidence": json.loads(row["ledger_json"]),
            "confidence": json.loads(row["confidence_json"]),
            "executionTrace": json.loads(row["trace_json"]),
            "reportUrl": row["report_url"],
            "rejected": bool(row["rejected"]),
            "rejectionReason": rejection.get("reason"),
            "rejectionDetails": rejection.get("details"),
            "taskSpec": json.loads(row["task_spec_json"]) if row["task_spec_json"] else None,
        }
        return AnalyzeResponse.model_validate(document)

    @staticmethod
    def _filters(
        task_type: Optional[str], rejected: Optional[bool], tier: Optional[str], query_contains: Optional[str]
    ) -> Tuple[str, List[Any]]:
        clauses, params = [], []
        if task_type is not None:
            clauses.append("task_type = ?")
            params.append(task_type)
        if rejected is not None:
            clauses.append("rejected = ?")
            params.append(1 if rejected else 0)
        if tier is not None:
            clauses.append("confidence_tier = ?")
            params.append(tier)
        if query_contains:
            # Escape LIKE wildcards so a query containing % or _ matches literally.
            escaped = query_contains.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append("query_text LIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return where, params

    def list_sessions(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        task_type: Optional[str] = None,
        rejected: Optional[bool] = None,
        tier: Optional[str] = None,
        query_contains: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Summaries of stored sessions, newest first. Not exposed over HTTP: the API has
        no authentication, so listing would let anyone read every user's queries."""
        where, params = self._filters(task_type, rejected, tier, query_contains)
        limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT session_id, created_at, query_text, task_type, rejected, confidence_tier
                FROM sessions {where}
                ORDER BY created_at DESC, session_id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, limit, max(0, int(offset))),
            ).fetchall()
        return [{**dict(r), "rejected": bool(r["rejected"])} for r in rows]

    def count_sessions(
        self,
        *,
        task_type: Optional[str] = None,
        rejected: Optional[bool] = None,
        tier: Optional[str] = None,
        query_contains: Optional[str] = None,
    ) -> int:
        where, params = self._filters(task_type, rejected, tier, query_contains)
        with self._connect() as conn:
            return conn.execute(f"SELECT COUNT(*) FROM sessions {where}", params).fetchone()[0]

"""Storage backend for the live board and the N = Everyone survey.

Why this exists: Streamlit Community Cloud wipes the container's local disk
whenever the app restarts, sleeps, or redeploys. The board used to keep each
session in data/<CODE>.json and the survey in data/survey_responses.db, both
on that disk — which is how SF-01's posts were lost. Everything now lives in
a hosted Postgres database when DATABASE_URL is set in Streamlit secrets
(e.g. a free Supabase project), which survives any restart.

Without DATABASE_URL the app falls back to a local SQLite file (data/app.db)
so local development still works — but that file is NOT durable on Streamlit
Cloud, and the facilitator sidebar says so in red. If DATABASE_URL is set but
unreachable, calls raise instead of silently writing somewhere else: a quiet
fallback would split one session's data across two stores.

Tables (same shape on both backends):
  board_sessions(code PK, data, updated_at)      one JSON document per session code
  board_archive(id, code, data, archived_at, reason)   snapshot taken before every reset
  survey_responses(id PK, submitted_at, time_to_complete_seconds, straightlining, answers_json)
"""
import json
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SQLITE_PATH = DATA_DIR / "app.db"
LEGACY_SURVEY_DB = DATA_DIR / "survey_responses.db"

_init_lock = threading.Lock()
_backend = None


def _database_url() -> str | None:
    try:
        import streamlit as st

        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass
    return os.environ.get("DATABASE_URL") or None


# ------------------------------------------------------------------ postgres --
class _Postgres:
    durable = True
    name = "Postgres (DATABASE_URL)"

    def __init__(self, url: str):
        from psycopg_pool import ConnectionPool

        # prepare_threshold=None: Supabase's transaction pooler (port 6543)
        # can't use server-side prepared statements.
        self.pool = ConnectionPool(
            url, min_size=1, max_size=8, kwargs={"prepare_threshold": None}, open=True, timeout=15
        )
        with self.pool.connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS board_sessions (
                    code TEXT PRIMARY KEY,
                    data JSONB NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
                )"""
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS board_archive (
                    id BIGSERIAL PRIMARY KEY,
                    code TEXT NOT NULL,
                    data JSONB NOT NULL,
                    archived_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    reason TEXT
                )"""
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS survey_responses (
                    id TEXT PRIMARY KEY,
                    submitted_at DOUBLE PRECISION NOT NULL,
                    time_to_complete_seconds DOUBLE PRECISION,
                    straightlining BOOLEAN NOT NULL DEFAULT FALSE,
                    answers_json JSONB NOT NULL
                )"""
            )

    def get_doc(self, code):
        with self.pool.connection() as conn:
            row = conn.execute("SELECT data FROM board_sessions WHERE code = %s", (code,)).fetchone()
        return row[0] if row else None

    def update_doc(self, code, default_doc, mutator):
        from psycopg.types.json import Jsonb

        with self.pool.connection() as conn:
            with conn.transaction():
                conn.execute(
                    "INSERT INTO board_sessions (code, data) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                    (code, Jsonb(default_doc)),
                )
                data = conn.execute(
                    "SELECT data FROM board_sessions WHERE code = %s FOR UPDATE", (code,)
                ).fetchone()[0]
                data = mutator(data)
                conn.execute(
                    "UPDATE board_sessions SET data = %s, updated_at = now() WHERE code = %s",
                    (Jsonb(data), code),
                )
        return data

    def archive_doc(self, code, reason):
        with self.pool.connection() as conn:
            conn.execute(
                "INSERT INTO board_archive (code, data, reason) SELECT code, data, %s FROM board_sessions WHERE code = %s",
                (reason, code),
            )

    def import_doc(self, code, doc):
        from psycopg.types.json import Jsonb

        with self.pool.connection() as conn:
            conn.execute(
                "INSERT INTO board_sessions (code, data) VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                (code, Jsonb(doc)),
            )

    def insert_survey(self, row):
        from psycopg.types.json import Jsonb

        with self.pool.connection() as conn:
            conn.execute(
                "INSERT INTO survey_responses (id, submitted_at, time_to_complete_seconds, straightlining, answers_json) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                (row["id"], row["submitted_at"], row["ttc"], bool(row["straightlining"]), Jsonb(row["answers"])),
            )

    def all_survey(self):
        with self.pool.connection() as conn:
            rows = conn.execute(
                "SELECT id, submitted_at, time_to_complete_seconds, straightlining, answers_json "
                "FROM survey_responses ORDER BY submitted_at"
            ).fetchall()
        return [(r[0], r[1], r[2], r[3], r[4]) for r in rows]


# -------------------------------------------------------------------- sqlite --
class _SQLite:
    durable = False
    name = "Local file data/app.db (NOT durable on Streamlit Cloud)"

    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        with self._conn() as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS board_sessions (code TEXT PRIMARY KEY, data TEXT NOT NULL, updated_at REAL)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS board_archive (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, "
                "data TEXT NOT NULL, archived_at REAL NOT NULL, reason TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS survey_responses (id TEXT PRIMARY KEY, submitted_at REAL NOT NULL, "
                "time_to_complete_seconds REAL, straightlining INTEGER NOT NULL DEFAULT 0, answers_json TEXT NOT NULL)"
            )

    def _conn(self):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        return _Closing(conn)

    def get_doc(self, code):
        with self._conn() as conn:
            row = conn.execute("SELECT data FROM board_sessions WHERE code = ?", (code,)).fetchone()
        return json.loads(row[0]) if row else None

    def update_doc(self, code, default_doc, mutator):
        with self.lock, self._conn() as conn:
            conn.execute("BEGIN IMMEDIATE")
            try:
                row = conn.execute("SELECT data FROM board_sessions WHERE code = ?", (code,)).fetchone()
                data = json.loads(row[0]) if row else default_doc
                data = mutator(data)
                conn.execute(
                    "INSERT INTO board_sessions (code, data, updated_at) VALUES (?, ?, ?) "
                    "ON CONFLICT(code) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                    (code, json.dumps(data), time.time()),
                )
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise
        return data

    def archive_doc(self, code, reason):
        with self.lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO board_archive (code, data, archived_at, reason) SELECT code, data, ?, ? FROM board_sessions WHERE code = ?",
                (time.time(), reason, code),
            )

    def import_doc(self, code, doc):
        with self.lock, self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO board_sessions (code, data, updated_at) VALUES (?, ?, ?)",
                (code, json.dumps(doc), time.time()),
            )

    def insert_survey(self, row):
        with self.lock, self._conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO survey_responses (id, submitted_at, time_to_complete_seconds, straightlining, answers_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (row["id"], row["submitted_at"], row["ttc"], int(bool(row["straightlining"])), json.dumps(row["answers"])),
            )

    def all_survey(self):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, submitted_at, time_to_complete_seconds, straightlining, answers_json "
                "FROM survey_responses ORDER BY submitted_at"
            ).fetchall()
        return [(r[0], r[1], r[2], bool(r[3]), json.loads(r[4])) for r in rows]


class _Closing:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        self.conn.close()


# --------------------------------------------------------------- public api --
def backend():
    """The active backend, created once per process. Also imports anything
    still sitting in the old local files (board JSON, survey SQLite) so data
    from before this change is carried over if the container still has it."""
    global _backend
    if _backend is not None:
        return _backend
    with _init_lock:
        if _backend is None:
            url = _database_url()
            b = _Postgres(url) if url else _SQLite(SQLITE_PATH)
            _import_legacy(b)
            _backend = b
    return _backend


def _import_legacy(b) -> None:
    for path in DATA_DIR.glob("*.json"):
        try:
            with open(path) as f:
                b.import_doc(path.stem, json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    if LEGACY_SURVEY_DB.exists():
        try:
            conn = sqlite3.connect(LEGACY_SURVEY_DB)
            rows = conn.execute(
                "SELECT id, submitted_at, time_to_complete_seconds, straightlining, answers_json FROM responses"
            ).fetchall()
            conn.close()
        except sqlite3.Error:
            rows = []
        for id_, ts, ttc, straight, answers in rows:
            b.insert_survey({"id": id_, "submitted_at": ts, "ttc": ttc, "straightlining": straight, "answers": json.loads(answers)})


def is_durable() -> bool:
    return backend().durable


def backend_name() -> str:
    return backend().name


def get_doc(code: str):
    return backend().get_doc(code)


def update_doc(code: str, default_doc: dict, mutator) -> dict:
    """Atomically load → mutate → save one session's document. `mutator`
    receives the current document and returns the new one."""
    return backend().update_doc(code, default_doc, mutator)


def archive_doc(code: str, reason: str) -> None:
    backend().archive_doc(code, reason)


def insert_survey(answers: dict, ttc, straightlining: bool) -> str:
    response_id = uuid.uuid4().hex
    backend().insert_survey(
        {"id": response_id, "submitted_at": time.time(), "ttc": ttc, "straightlining": straightlining, "answers": answers}
    )
    return response_id


def all_survey():
    return backend().all_survey()

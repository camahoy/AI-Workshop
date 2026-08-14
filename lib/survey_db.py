"""Persistent SQLite storage for N = Everyone survey responses.

Deliberately separate from the live board's per-session JSON files
(lib/store.py): the live board is ephemeral by design (reset between
workshop sessions, fine to lose on redeploy), but the survey is meant to
run as a standalone, company-wide field window of about two weeks, so its
responses need to survive independently of anything happening on the live
board. SQLite (WAL mode, one file under data/) is enough for that without
standing up a real hosted database.

No PII beyond what the questionnaire itself asks (service line, title,
etc.) is ever stored — no IP address, no device fingerprint, no name.
"""
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "survey_responses.db"
DB_PATH.parent.mkdir(exist_ok=True)

_lock = threading.Lock()
_initialized = False


def _connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    global _initialized
    if _initialized:
        return
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    id TEXT PRIMARY KEY,
                    submitted_at REAL NOT NULL,
                    time_to_complete_seconds REAL,
                    straightlining INTEGER NOT NULL DEFAULT 0,
                    answers_json TEXT NOT NULL
                )
                """
            )
            conn.commit()
        finally:
            conn.close()
        _initialized = True


def insert_response(answers: dict, time_to_complete_seconds: float, straightlining: bool) -> str:
    """Appends a new response row. Each submission is its own row — the
    survey has no login and no edit-in-place, matching "respond once per
    browser session is fine, don't over-engineer duplicate prevention."""
    init_db()
    response_id = uuid.uuid4().hex
    with _lock:
        conn = _connect()
        try:
            conn.execute(
                "INSERT INTO responses (id, submitted_at, time_to_complete_seconds, straightlining, answers_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (response_id, time.time(), time_to_complete_seconds, int(straightlining), json.dumps(answers)),
            )
            conn.commit()
        finally:
            conn.close()
    return response_id


def all_responses() -> list[dict]:
    """Returns every stored response as a plain dict, with `_id`,
    `_submitted_at`, `_time_to_complete_seconds`, and `_straightlining`
    metadata keys merged in alongside the questionnaire answers."""
    init_db()
    with _lock:
        conn = _connect()
        try:
            rows = conn.execute(
                "SELECT id, submitted_at, time_to_complete_seconds, straightlining, answers_json "
                "FROM responses ORDER BY submitted_at"
            ).fetchall()
        finally:
            conn.close()
    out = []
    for id_, submitted_at, ttc, straight, answers_json in rows:
        answers = json.loads(answers_json)
        answers["_id"] = id_
        answers["_submitted_at"] = submitted_at
        answers["_time_to_complete_seconds"] = ttc
        answers["_straightlining"] = bool(straight)
        out.append(answers)
    return out


def response_count() -> int:
    init_db()
    with _lock:
        conn = _connect()
        try:
            return conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
        finally:
            conn.close()

"""N = Everyone survey responses — stored through lib/db.py.

Previously a SQLite file on the app's local disk (data/survey_responses.db),
which Streamlit Community Cloud does not keep across restarts. Responses now
go to the same durable database as the live board (Postgres when
DATABASE_URL is set), in their own survey_responses table — the board's
"Reset board" never touches it. Any rows still in the old local file are
imported automatically on startup.

No PII beyond what the questionnaire itself asks (service line, title,
etc.) is ever stored — no IP address, no device fingerprint, no name.
"""
from lib import db


def init_db() -> None:
    db.backend()


def insert_response(answers: dict, time_to_complete_seconds: float, straightlining: bool) -> str:
    """Appends a new response row. Each submission is its own row — the
    survey has no login and no edit-in-place."""
    return db.insert_survey(answers, time_to_complete_seconds, straightlining)


def all_responses() -> list[dict]:
    """Returns every stored response as a plain dict, with `_id`,
    `_submitted_at`, `_time_to_complete_seconds`, and `_straightlining`
    metadata keys merged in alongside the questionnaire answers."""
    out = []
    for id_, submitted_at, ttc, straight, answers in db.all_survey():
        answers = dict(answers)
        answers["_id"] = id_
        answers["_submitted_at"] = submitted_at
        answers["_time_to_complete_seconds"] = ttc
        answers["_straightlining"] = bool(straight)
        out.append(answers)
    return out


def response_count() -> int:
    return len(db.all_survey())

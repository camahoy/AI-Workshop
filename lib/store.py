"""Shared storage for the live working-session board.

One document per session code, stored durably via lib/db.py (Postgres when
DATABASE_URL is set). Data is namespaced by session code, so sessions never
see each other's data: SF-01 and PA-01 are separate rows, and every read,
write, export, and reset takes the session code.
"""
import re
import time

from lib import db

_SAFE_CODE_RE = re.compile(r"[^A-Za-z0-9_-]")

AGREE_COLLECTIONS = ("notes", "map", "ideas", "ailog")


def normalize_code(session_code: str) -> str:
    code = _SAFE_CODE_RE.sub("", (session_code or "").strip())
    return code or "default"


def _default_data() -> dict:
    return {
        "config": None,        # per-session settings (lib/sessions.py); None = template default
        "roster": [],          # [{device_id, level, joined, (service_line, title)}]
        "notes": [],           # Good Research: [{id, text, tag?, level, created}]
        "map": [],             # Meaning & Delegation: [{id, text, x, y, tag?, level, created}]
        "ideas": [],           # Bottleneck Bank / Friction Points: [{id, text, tag?, level, created}]
        "ailog": [],           # AI in Our Work: [{id, task, tool, how, outcome, worked, didnt, barrier, barrier_other, time_impact, level, created}]
        "agree_counts": {k: {} for k in AGREE_COLLECTIONS},   # {collection: {item_id: count}}
        "my_agree": {k: {} for k in AGREE_COLLECTIONS},       # {collection: {device_id: {item_id: True}}}
        "summary": None,       # {"text": ..., "generated_at": ...}
        "last_updated": None,  # epoch seconds of most recent real activity
    }


def _fill_defaults(data: dict | None) -> dict:
    out = _default_data()
    if data:
        out.update(data)
    for k in AGREE_COLLECTIONS:
        out["agree_counts"].setdefault(k, {})
        out["my_agree"].setdefault(k, {})
    for k in ("roster", "notes", "map", "ideas", "ailog"):
        if out.get(k) is None:
            out[k] = []
    return out


def load(session_code: str) -> dict:
    return _fill_defaults(db.get_doc(normalize_code(session_code)))


def update(session_code: str, mutator) -> dict:
    """Load, mutate in place via `mutator(data)`, stamp last_updated, save,
    return the resulting data — atomically, so two people posting at once
    never overwrite each other."""

    def apply(raw):
        data = _fill_defaults(raw)
        mutator(data)
        data["last_updated"] = time.time()
        return data

    return db.update_doc(normalize_code(session_code), _default_data(), apply)


def set_config(session_code: str, config: dict) -> dict:
    """Saves settings without counting as board activity."""

    def apply(raw):
        data = _fill_defaults(raw)
        data["config"] = config
        return data

    return db.update_doc(normalize_code(session_code), _default_data(), apply)


def reset(session_code: str) -> None:
    """Clears this session's posts, agrees, roster and summary. A full copy
    is archived first (board_archive table) so a mistaken reset is
    recoverable. The session's settings are kept, so PA-01 stays PA-01."""
    code = normalize_code(session_code)
    db.archive_doc(code, "reset")

    def apply(raw):
        fresh = _default_data()
        fresh["config"] = (raw or {}).get("config")
        return fresh

    db.update_doc(code, _default_data(), apply)


def now() -> float:
    return time.time()


def toggle_agree(d: dict, collection: str, item_id: str, device_id: str) -> None:
    """Mutates `d` in place: flips whether `device_id` agrees with
    `item_id` in `collection`, and keeps the aggregate count in sync.
    Individual agree state is private (keyed by device); only the
    aggregate count is meant to be read back and displayed."""
    mine = d["my_agree"].setdefault(collection, {}).setdefault(device_id, {})
    counts = d["agree_counts"].setdefault(collection, {})
    if mine.get(item_id):
        counts[item_id] = max(0, counts.get(item_id, 1) - 1)
        del mine[item_id]
    else:
        counts[item_id] = counts.get(item_id, 0) + 1
        mine[item_id] = True

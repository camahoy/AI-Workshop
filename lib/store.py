"""Shared, file-backed storage for live workshop board data.

Streamlit Community Cloud runs one process for the whole app, so a JSON
file on local disk is effectively shared state across every connected
device. Data is namespaced by session code so multiple concurrent
workshops never see each other's data. Storage is intentionally simple
(no database) since the app is expected to sleep between sessions and
data does not need to survive a redeploy.
"""
import json
import os
import re
import threading
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

_SAFE_CODE_RE = re.compile(r"[^A-Za-z0-9_-]")


def normalize_code(session_code: str) -> str:
    code = _SAFE_CODE_RE.sub("", (session_code or "").strip())
    return code or "default"


def _lock_for(session_code: str) -> threading.Lock:
    code = normalize_code(session_code)
    with _locks_guard:
        if code not in _locks:
            _locks[code] = threading.Lock()
        return _locks[code]


def _path(session_code: str) -> Path:
    return DATA_DIR / f"{normalize_code(session_code)}.json"


def _default_data() -> dict:
    return {
        "roster": [],          # [{device_id, name, level}]
        "groups": None,        # [[person, ...], ...] or None
        "group_size": 5,
        "notes": [],           # [{text, rotation}]
        "map": {"tl": [], "tr": [], "bl": [], "br": []},
        "votes": {},           # {idea_index_str: count}
        "my_votes": {},        # {device_id: {idea_index_str: count}}
        "pulse": {"q1": {}, "q2": {}},
        "my_pulse": {},        # {device_id: {"q1": val, "q2": val}}
        "summary": None,       # {"text": ..., "generated_at": ...}
    }


def load(session_code: str) -> dict:
    path = _path(session_code)
    if not path.exists():
        return _default_data()
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_data()
    defaults = _default_data()
    defaults.update(data)
    return defaults


def save(session_code: str, data: dict) -> None:
    path = _path(session_code)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, path)


def update(session_code: str, mutator) -> dict:
    """Load, mutate in place via `mutator(data)`, save, return data."""
    lock = _lock_for(session_code)
    with lock:
        data = load(session_code)
        mutator(data)
        save(session_code, data)
        return data


def reset(session_code: str) -> None:
    lock = _lock_for(session_code)
    with lock:
        save(session_code, _default_data())

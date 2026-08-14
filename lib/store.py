"""Shared, file-backed storage for the live working-session board.

Streamlit Community Cloud runs one process for the whole app, so a JSON
file on local disk is effectively shared state across every connected
device. Data is namespaced by session code so multiple concurrent
sessions never see each other's data. Storage is intentionally simple
(no database) since the app is expected to sleep between sessions and
data does not need to survive a redeploy.
"""
import json
import os
import re
import threading
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()

_SAFE_CODE_RE = re.compile(r"[^A-Za-z0-9_-]")

AGREE_COLLECTIONS = ("notes", "map", "ideas")


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
        "roster": [],          # [{device_id, service_line, title, level}]
        "notes": [],           # Good Research: [{id, text, tag}]
        "map": [],             # Meaning & Delegation: [{id, text, x, y, tag}]
        "ideas": [],           # Bottleneck Bank: [{id, text, tag}] — starts empty, no seeding
        "agree_counts": {k: {} for k in AGREE_COLLECTIONS},   # {collection: {item_id: count}}
        "my_agree": {k: {} for k in AGREE_COLLECTIONS},       # {collection: {device_id: {item_id: True}}}
        "summary": None,       # {"text": ..., "generated_at": ...}
        "last_updated": None,  # epoch seconds of most recent real activity
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
    for k in AGREE_COLLECTIONS:
        defaults["agree_counts"].setdefault(k, {})
        defaults["my_agree"].setdefault(k, {})
    return defaults


def save(session_code: str, data: dict) -> None:
    path = _path(session_code)
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w") as f:
        json.dump(data, f)
    os.replace(tmp_path, path)


def update(session_code: str, mutator) -> dict:
    """Load, mutate in place via `mutator(data)`, stamp last_updated, save,
    return the resulting data. Every real participant action should route
    through this so the "last updated" indicator reflects genuine activity."""
    lock = _lock_for(session_code)
    with lock:
        data = load(session_code)
        mutator(data)
        data["last_updated"] = time.time()
        save(session_code, data)
        return data


def reset(session_code: str) -> None:
    lock = _lock_for(session_code)
    with lock:
        save(session_code, _default_data())


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

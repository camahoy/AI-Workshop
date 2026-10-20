"""File-backed shared state for the three live boards.

Same approach as the SF board's lib/store.py: Streamlit runs one process
for every connected browser, so one JSON file guarded by a lock is shared
state. All three boards live in one file so "Delete all data" is a single
unlink.

Only what the handoff allows is stored: post text, optional tags, optional
name, timestamps, vote/comment records and a random browser id.
"""
import json
import os
import threading
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from palib import config

DATA_DIR = Path(os.environ.get("PA_BOARDS_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DATA_FILE = DATA_DIR / "pa_boards.json"

_lock = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return prefix + uuid.uuid4().hex[:10]


def _default_board(key: str) -> dict:
    board = {"open": True, "show_qr": True, "summary": None}
    if key == "c":
        board.update({"revealed": False, "picks": {}, "others": []})
    else:
        board["posts"] = []
    return board


def _default_data() -> dict:
    data = {
        "settings": {
            "session_date": "",
            "base_url": "",
            "seed_b": True,
            "retention_days": config.DEFAULT_RETENTION_DAYS,
            "ai_summary": False,
        },
        "created_at": _now(),
        "boards": {k: _default_board(k) for k in config.BOARD_KEYS},
        "ai_themes": None,
        "last_updated": None,
    }
    apply_seeds(data)
    return data


# ----------------------------------------------------------------- seeds --
def apply_seeds(data: dict) -> None:
    """Board B seed rows exist exactly when settings.seed_b is on."""
    posts = data["boards"]["b"]["posts"]
    if not data["settings"].get("seed_b"):
        posts[:] = [p for p in posts if not p.get("seed")]
        return
    have = {p["text"] for p in posts if p.get("seed")}
    for text in config.SEEDS_B:
        if text not in have:
            posts.append(_make_post(text, browser_id=None, seed=True))


# ------------------------------------------------------------- retention --
def delete_after(data: dict) -> float:
    """Epoch seconds after which everything is deleted: retention_days
    after the session date if one is set, otherwise after creation."""
    days = data["settings"].get("retention_days") or config.DEFAULT_RETENTION_DAYS
    start = data.get("created_at") or _now()
    session_date = data["settings"].get("session_date")
    if session_date:
        try:
            start = datetime.combine(date.fromisoformat(session_date), datetime.min.time()).timestamp()
        except ValueError:
            pass
    return start + timedelta(days=float(days)).total_seconds()


# ---------------------------------------------------------------- io --
def _read() -> dict:
    if not DATA_FILE.exists():
        return _default_data()
    try:
        with open(DATA_FILE) as f:
            stored = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _default_data()
    data = _default_data()
    data["settings"].update(stored.get("settings", {}))
    for k in config.BOARD_KEYS:
        data["boards"][k].update(stored.get("boards", {}).get(k, {}))
    for k in ("created_at", "ai_themes", "last_updated"):
        if k in stored:
            data[k] = stored[k]
    return data


def _write(data: dict) -> None:
    tmp = DATA_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, DATA_FILE)


def load() -> dict:
    with _lock:
        data = _read()
        if DATA_FILE.exists() and _now() > delete_after(data):
            delete_all()
            return _read()
        return data


def update(mutator) -> dict:
    """Load, apply `mutator(data)`, stamp last_updated, save. Returns the
    saved data. If the mutator returns False nothing is written."""
    with _lock:
        data = load()
        if mutator(data) is False:
            return data
        data["last_updated"] = _now()
        _write(data)
        return data


def delete_all() -> None:
    with _lock:
        for path in (DATA_FILE, DATA_FILE.with_suffix(".tmp")):
            try:
                path.unlink()
            except FileNotFoundError:
                pass


def reset_board(key: str) -> dict:
    def mutate(d):
        d["boards"][key] = _default_board(key)
        if key == "b":
            apply_seeds(d)
        if key in ("a", "b"):
            d["ai_themes"] = None
    return update(mutate)


# ------------------------------------------------------------- mutations --
def _clean(text, limit):
    return (text or "").strip()[:limit]


def _make_post(text, browser_id, seed=False, **fields) -> dict:
    post = {
        "id": _new_id("p"),
        "text": text,
        "name": "",
        "created_at": _now(),
        "browser_id": browser_id,
        "hidden": False,
        "seed": seed,
        "votes": [],
        "comments": [],
    }
    post.update(fields)
    return post


def find_post(data, key, post_id):
    return next((p for p in data["boards"][key]["posts"] if p["id"] == post_id), None)


def add_post(key: str, browser_id: str, text: str, name: str = "", **fields) -> dict | None:
    """Fields: Board A takes tool/task, Board B takes freq/minutes.
    Returns the new post, or None if rejected (empty, or posting closed)."""
    text = _clean(text, config.MAX_POST_CHARS)
    if not text:
        return None
    if key == "a":
        extra = {
            "tool": fields.get("tool") if fields.get("tool") in config.TOOLS else "",
            "task": fields.get("task") if fields.get("task") in config.TASK_TYPES else "",
        }
    else:
        minutes = fields.get("minutes")
        try:
            minutes = int(minutes) if minutes not in (None, "") else None
        except (TypeError, ValueError):
            minutes = None
        if minutes is not None and not 0 < minutes <= 24 * 60:
            minutes = None
        extra = {
            "freq": fields.get("freq") if fields.get("freq") in config.FREQUENCIES else "",
            "minutes": minutes,
        }
    post = _make_post(text, browser_id, name=_clean(name, config.MAX_NAME_CHARS), **extra)
    created = []

    def mutate(d):
        if not d["boards"][key]["open"]:
            return False
        d["boards"][key]["posts"].append(post)
        created.append(post)
    update(mutate)
    return created[0] if created else None


def toggle_vote(key: str, post_id: str, browser_id: str) -> bool | None:
    """Flips this browser's vote. Returns True if now voted, False if
    undone, None if nothing happened (closed, hidden, unknown post)."""
    result = []

    def mutate(d):
        if not d["boards"][key]["open"]:
            return False
        post = find_post(d, key, post_id)
        if not post or post["hidden"]:
            return False
        if browser_id in post["votes"]:
            post["votes"].remove(browser_id)
            result.append(False)
        else:
            post["votes"].append(browser_id)
            result.append(True)
    update(mutate)
    return result[0] if result else None


def add_comment(key: str, post_id: str, browser_id: str, text: str, name: str = "") -> bool:
    text = _clean(text, config.MAX_COMMENT_CHARS)
    if not text:
        return False
    done = []

    def mutate(d):
        if not d["boards"][key]["open"]:
            return False
        post = find_post(d, key, post_id)
        if not post or post["hidden"]:
            return False
        post["comments"].append({
            "id": _new_id("c"),
            "text": text,
            "name": _clean(name, config.MAX_NAME_CHARS),
            "created_at": _now(),
            "browser_id": browser_id,
        })
        done.append(True)
    update(mutate)
    return bool(done)


def set_hidden(key: str, item_id: str, hidden: bool) -> None:
    def mutate(d):
        board = d["boards"][key]
        items = board["others"] if key == "c" else board["posts"]
        for item in items:
            if item["id"] == item_id:
                item["hidden"] = hidden
    update(mutate)


def toggle_pick(browser_id: str, option_index: int) -> None:
    def mutate(d):
        board = d["boards"]["c"]
        if not board["open"] or not 0 <= option_index < len(config.NEXT_OPTIONS):
            return False
        mine = board["picks"].setdefault(browser_id, [])
        if option_index in mine:
            mine.remove(option_index)
        else:
            mine.append(option_index)
    update(mutate)


def add_other(browser_id: str, text: str) -> bool:
    text = _clean(text, config.MAX_POST_CHARS)
    if not text:
        return False
    done = []

    def mutate(d):
        board = d["boards"]["c"]
        if not board["open"]:
            return False
        board["others"].append({
            "id": _new_id("o"), "text": text, "created_at": _now(),
            "browser_id": browser_id, "hidden": False,
        })
        done.append(True)
    update(mutate)
    return bool(done)


def set_board_flag(key: str, flag: str, value) -> dict:
    def mutate(d):
        d["boards"][key][flag] = value
    return update(mutate)


def set_setting(name: str, value) -> dict:
    def mutate(d):
        d["settings"][name] = value
        if name == "seed_b":
            apply_seeds(d)
    return update(mutate)


def save_summary(key: str, summary: dict) -> None:
    def mutate(d):
        d["boards"][key]["summary"] = summary
    update(mutate)


def save_ai_themes(themes: dict) -> None:
    def mutate(d):
        d["ai_themes"] = themes
    update(mutate)


# --------------------------------------------------------------- reading --
def visible_posts(data: dict, key: str) -> list[dict]:
    """Non-hidden posts, most votes first, ties newest first."""
    posts = [p for p in data["boards"][key]["posts"] if not p["hidden"]]
    return sorted(posts, key=lambda p: (-len(p["votes"]), -p["created_at"]))


def participants(data: dict, key: str) -> set[str]:
    board = data["boards"][key]
    ids = set()
    if key == "c":
        ids.update(b for b, picks in board["picks"].items() if picks)
        ids.update(o["browser_id"] for o in board["others"])
    else:
        for p in board["posts"]:
            ids.add(p["browser_id"])
            ids.update(p["votes"])
            ids.update(c["browser_id"] for c in p["comments"])
    ids.discard(None)
    return ids

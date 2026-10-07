"""CSV export of every board in one session.

Column names are plain, with no spaces, so the files import cleanly into a
SharePoint List. Level appears here and nowhere on screen in anonymous
sessions. Files are UTF-8 with a byte-order mark so Excel opens accents and
curly quotes correctly.
"""
import csv
import io
import time
import zipfile
from datetime import datetime, timezone

from lib.board_map import QUAD_LABELS, quad_of


def _iso(ts) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _csv(columns: list[str], rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({c: ("" if r.get(c) is None else r.get(c)) for c in columns})
    return ("﻿" + buf.getvalue()).encode("utf-8")


def board_files(code: str, data: dict, cfg: dict) -> dict[str, bytes]:
    """{filename: csv bytes} for each board in the session: every tab that's
    switched on, plus any board that holds data even if its tab is hidden,
    so nothing collected is ever left out of an export."""
    anonymous = cfg["anonymous"]
    agree = data.get("agree_counts", {})
    files: dict[str, bytes] = {}

    def wanted(key):
        return key in cfg["tabs"] or bool(data.get(key))

    def post_rows(key):
        counts = agree.get(key, {})
        return [
            {
                "Post": p.get("text", ""),
                "Tag": p.get("tag", ""),
                "AgreeCount": counts.get(p["id"], 0),
                "Level": p.get("level", ""),
                "Created": _iso(p.get("created")),
            }
            for p in data.get(key, [])
        ]

    post_cols = ["Post", "AgreeCount", "Level", "Created"] if anonymous else ["Post", "Tag", "AgreeCount", "Level", "Created"]

    if wanted("notes"):
        files[f"{code}_GoodResearch.csv"] = _csv(post_cols, post_rows("notes"))

    if wanted("map"):
        counts = agree.get("map", {})
        rows = [
            {
                "Task": p.get("text", ""),
                "X": round(p.get("x", 0), 3),
                "Y": round(p.get("y", 0), 3),
                "Quadrant": QUAD_LABELS[quad_of(p["x"], p["y"])],
                "Tag": p.get("tag", ""),
                "AgreeCount": counts.get(p["id"], 0),
                "Level": p.get("level", ""),
                "Created": _iso(p.get("created")),
            }
            for p in data.get("map", [])
        ]
        cols = ["Task", "X", "Y", "Quadrant", "AgreeCount", "Level", "Created"]
        if not anonymous:
            cols.insert(4, "Tag")
        files[f"{code}_MeaningDelegation.csv"] = _csv(cols, rows)

    if wanted("ideas"):
        name = "FrictionPoints" if cfg["ideas_style"] == "friction" else "BottleneckBank"
        files[f"{code}_{name}.csv"] = _csv(post_cols, post_rows("ideas"))

    if wanted("ailog"):
        counts = agree.get("ailog", {})
        rows = [
            {
                "Task": e.get("task", ""),
                "Tool": e.get("tool", ""),
                "HowUsed": e.get("how", ""),
                "Outcome": e.get("outcome", ""),
                "WhatWorked": e.get("worked", ""),
                "WhatDidnt": e.get("didnt", ""),
                "Barrier": e.get("barrier", ""),
                "BarrierOther": e.get("barrier_other", ""),
                "TimeImpact": e.get("time_impact", ""),
                "SameForMeCount": counts.get(e["id"], 0),
                "Level": e.get("level", ""),
                "Created": _iso(e.get("created")),
            }
            for e in data.get("ailog", [])
        ]
        cols = ["Task", "Tool", "HowUsed", "Outcome", "WhatWorked", "WhatDidnt", "Barrier", "BarrierOther",
                "TimeImpact", "SameForMeCount", "Level", "Created"]
        files[f"{code}_AILog.csv"] = _csv(cols, rows)

    roster = data.get("roster", [])
    if anonymous:
        rows = [{"Level": p.get("level", ""), "Joined": _iso(p.get("joined"))} for p in roster]
        files[f"{code}_Participants.csv"] = _csv(["Level", "Joined"], rows)
    else:
        rows = [
            {"ServiceLine": p.get("service_line", ""), "Title": p.get("title", ""), "Level": p.get("level", ""),
             "Joined": _iso(p.get("joined"))}
            for p in roster
        ]
        files[f"{code}_Participants.csv"] = _csv(["ServiceLine", "Title", "Level", "Joined"], rows)

    return files


def zip_files(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    # Fixed entry timestamps: identical data gives identical bytes, so the
    # download link stays the same across the board's 4-second refreshes.
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in files.items():
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, content)
    return buf.getvalue()


def stamp() -> str:
    return time.strftime("%Y%m%d-%H%M", time.gmtime())

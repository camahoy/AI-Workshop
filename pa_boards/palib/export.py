"""CSV exports. Board B's columns match the Wishlist tab of
04_Wishlist-and-Questions.xlsx so rows paste straight in.

Files are UTF-8 with a BOM so Excel opens accents and curly quotes
correctly, and any cell starting with = + - @ is prefixed with an
apostrophe so Excel never runs it as a formula.
"""
import csv
import io
import zipfile

from palib import config, store, summary

A_COLUMNS = ["Use", "Tool", "Task type", "Votes", "Comments", "Name"]
B_COLUMNS = ["Time drain", "How often", "Minutes each time", "Votes", "Comments", "Source"]
C_COLUMNS = ["Option", "Votes", "Percent of participants"]


def _safe(value):
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _comments(post) -> str:
    return " | ".join(
        f"{c['text']} ({c['name']})" if c.get("name") else c["text"] for c in post["comments"]
    )


def _csv(columns, rows) -> bytes:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(columns)
    for row in rows:
        writer.writerow([_safe(v) for v in row])
    return buf.getvalue().encode("utf-8-sig")


def source_label(data) -> str:
    when = data["settings"].get("session_date") or "date not set"
    return f"Live board, {when}"


def board_csv(data: dict, key: str) -> bytes:
    if key == "c":
        s = summary.summarize_next(data)
        rows = [[o["label"], o["votes"], f"{o['pct']:.0f}%"] for o in s["options"]]
        rows += [[f"Other: {text}", "", ""] for text in s["others"]]
        return _csv(C_COLUMNS, rows)

    posts = store.visible_posts(data, key)
    if key == "a":
        rows = [
            [p["text"], p.get("tool", ""), p.get("task", ""), len(p["votes"]), _comments(p), p.get("name", "")]
            for p in posts
        ]
        return _csv(A_COLUMNS, rows)

    live = source_label(data)
    rows = [
        [
            p["text"],
            p.get("freq", ""),
            p.get("minutes") if p.get("minutes") is not None else "",
            len(p["votes"]),
            _comments(p),
            f"{live} (seed: {config.SEED_LABEL})" if p.get("seed") else live,
        ]
        for p in posts
    ]
    return _csv(B_COLUMNS, rows)


def filename(data, key) -> str:
    when = data["settings"].get("session_date") or "undated"
    slug = config.BOARDS[key]["name"].lower().replace("'", "").replace(" ", "-")
    return f"board-{key}-{slug}-{when}.csv"


def all_zip(data: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        texts = []
        for key in config.BOARD_KEYS:
            z.writestr(filename(data, key), board_csv(data, key))
            texts.append(summary.to_text(summary.summarize(data, key)))
        themes = data.get("ai_themes")
        if themes:
            from palib import ai_summary
            texts.append(ai_summary.to_text(themes))
        z.writestr("summary.txt", ("\n\n" + "=" * 60 + "\n\n").join(texts).encode("utf-8-sig"))
    return buf.getvalue()

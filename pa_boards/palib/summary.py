"""Rule-based board summaries. Always available, no AI involved.

Each builder returns a plain dict so the same result can be rendered on
the projector, written into the export, and stored with the board.
"""
import time
from collections import Counter

from palib import config, store

NOT_GIVEN = "Not given"


def hours_per_month(post: dict) -> float | None:
    """Board B estimate: occurrences/month x minutes / 60 x (upvoters +
    the poster). None unless both frequency and minutes were given."""
    occ = config.FREQUENCIES.get(post.get("freq") or "")
    minutes = post.get("minutes")
    if occ is None or not minutes:
        return None
    people = len(post["votes"]) + (0 if post.get("seed") else 1)
    return occ * minutes / 60 * people


def _totals(data, key, posts):
    comments = [c for p in posts for c in store.visible_comments(p)]
    return {
        "posts": sum(1 for p in posts if not p.get("seed")),
        "seed_posts": sum(1 for p in posts if p.get("seed")),
        "votes": sum(len(p["votes"]) for p in posts),
        "comments": len(comments),
        "participants": len(store.participants(data, key)),
    }


def _row(post):
    return {
        "text": post["text"],
        "votes": len(post["votes"]),
        "comments": len(store.visible_comments(post)),
        "seed": bool(post.get("seed")),
    }


def summarize_posts(data: dict, key: str) -> dict:
    posts = store.visible_posts(data, key)
    result = {
        "board": key,
        "kind": "rule-based",
        "generated_at": time.time(),
        "totals": _totals(data, key, posts),
        "top": [_row(p) for p in posts[:5]],
    }
    real = [p for p in posts if not p.get("seed")]
    if key == "a":
        result["by_tool"] = Counter(p.get("tool") or NOT_GIVEN for p in real).most_common()
        result["by_task"] = Counter(p.get("task") or NOT_GIVEN for p in real).most_common()
    else:
        for row, post in zip(result["top"], posts[:5]):
            row["hours"] = hours_per_month(post)
        estimated = [(hours_per_month(p), p) for p in posts]
        estimated = sorted((e for e in estimated if e[0] is not None), key=lambda e: -e[0])
        result["by_hours"] = [dict(_row(p), hours=h) for h, p in estimated[:5]]
        result["estimated_total_hours"] = sum(h for h, _ in estimated)
    return result


def _comment_row(c):
    return {"text": c["text"], "votes": len(c.get("votes", []))}


def summarize_next(data: dict) -> dict:
    """Board C: votes per option (with % of participants), each option's
    comments, and every Other entry with its upvotes and comments."""
    board = data["boards"]["c"]
    counts = Counter()
    for picks in board["picks"].values():
        counts.update(picks)
    respondents = len(store.participants(data, "c"))
    options = []
    for i, label in enumerate(config.NEXT_OPTIONS):
        comments = store.ranked(store.option_comments(data, i))
        options.append({
            "label": label,
            "votes": counts.get(i, 0),
            "pct": (100 * counts.get(i, 0) / respondents) if respondents else 0.0,
            "comments": [_comment_row(c) for c in comments],
        })
    options.sort(key=lambda o: -o["votes"])
    others = [
        {"text": o["text"], "votes": len(o["votes"]),
         "comments": [_comment_row(c) for c in store.visible_comments(o)]}
        for o in store.visible_others(data)
    ]
    n_comments = sum(len(o["comments"]) for o in options) + sum(len(o["comments"]) for o in others)
    return {
        "board": "c",
        "kind": "rule-based",
        "generated_at": time.time(),
        "totals": {
            "participants": respondents,
            "votes": sum(counts.values()),
            "others": len(others),
            "comments": n_comments,
        },
        "options": options,
        "others": others,
    }


def summarize(data: dict, key: str) -> dict:
    return summarize_next(data) if key == "c" else summarize_posts(data, key)


def plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def fmt_hours(h: float | None) -> str:
    return "–" if h is None else f"{h:.1f} h/month (estimate)"


def to_text(summary: dict) -> str:
    """Plain-text version for the export."""
    key = summary["board"]
    b = config.BOARDS[key]
    t = summary["totals"]
    when = time.strftime("%Y-%m-%d %H:%M", time.localtime(summary["generated_at"]))
    lines = [f"Board {b['letter']}: {b['name']}", f"Question: {b['question']}", f"Generated {when} ({summary['kind']})", ""]
    if key == "c":
        lines.append(f"Participants: {t['participants']}  ·  Option votes: {t['votes']}  ·  "
                     f"Other entries: {t['others']}  ·  Comments: {t['comments']}")
        lines.append("")
        for o in summary["options"]:
            lines.append(f"{o['votes']:>4}  ({o['pct']:.0f}%)  {o['label']}")
            lines += [f"        - {c['text']}  ({plural(c['votes'], 'upvote')})" for c in o["comments"]]
        lines += ["", "Other entries (by upvotes):"]
        if summary["others"]:
            for o in summary["others"]:
                lines.append(f"- {o['text']}  ({plural(o['votes'], 'upvote')})")
                lines += [f"    - {c['text']}" for c in o["comments"]]
        else:
            lines.append("- None")
        return "\n".join(lines)

    seed_note = f" (+{t['seed_posts']} seed rows)" if t.get("seed_posts") else ""
    lines.append(
        f"Posts: {t['posts']}{seed_note}  ·  Votes: {t['votes']}  ·  "
        f"Comments: {t['comments']}  ·  Participants: {t['participants']}"
    )
    lines += ["", "Top 5 by votes:"]
    for i, row in enumerate(summary["top"], 1):
        extra = f"  ·  {fmt_hours(row['hours'])}" if key == "b" else ""
        seed = "  [seed]" if row["seed"] else ""
        lines.append(f"{i}. {row['text']}  ({plural(row['votes'], 'vote')}, {plural(row['comments'], 'comment')}{extra}){seed}")
    if key == "a":
        lines += ["", "By tool:"] + [f"- {name}: {n}" for name, n in summary["by_tool"]]
        lines += ["", "By task type:"] + [f"- {name}: {n}" for name, n in summary["by_task"]]
    else:
        lines += ["", "Biggest estimated drains (hours per month, estimate):"]
        if summary["by_hours"]:
            lines += [f"- {fmt_hours(r['hours'])}: {r['text']}" for r in summary["by_hours"]]
            lines.append(f"Total across all estimated items: {summary['estimated_total_hours']:.1f} h/month (estimate)")
        else:
            lines.append("- None yet (needs both 'How often' and 'Minutes each time')")
        lines += [
            "",
            "Estimate = occurrences per month (Daily 21, Weekly 4.3, Monthly 1, Quarterly 1/3) "
            "x minutes / 60 x (upvoters + poster).",
        ]
    return "\n".join(lines)

"""Builds the closing-moment synthesis by sending the live board to Claude
and streaming the response back for a typewriter-style projection."""
import streamlit as st
from anthropic import Anthropic

from lib.board_map import QUAD_LABELS, quad_of

SYSTEM_PROMPT = """You are synthesizing the output of a live, cross-level, cross-division working session at a market research company about AI adoption. This session exists to prime the case for a formal AI strategy initiative, gathering real evidence of what people actually need before any roadmap is proposed to the CEO. The company wants AI to create real operating efficiency and, downstream, better conditions for revenue, without relying on headcount reduction, and wants adoption to be mindful and sustainable rather than rushed.

Write a tight, decision-useful summary for a CEO audience, using plain language, grounded ONLY in the data given (do not invent specifics not implied by the input). Note that "agree" counts show how widely shared a sentiment is, not a ranking of importance, different service lines may have entirely different, equally valid bottlenecks.

Sections:
1. What "good research" actually means to this room, synthesized from the specific moments people described, not a generic definition
2. The meaning/delegation map: what's in the "protect this" quadrant, what's in the tension zone (meaningful but delegable, worth a real conversation about whether and how to automate), and what's the clearest automation opportunity (not a source of meaning and delegable), note any service-line patterns
3. The most widely-shared bottlenecks, noting which service lines raised them and which agreed, and whether bottlenecks differ meaningfully by service line (this matters, a single company-wide tool may not fit everyone)
4. A short "case for an AI strategy initiative" paragraph: based only on what this room said, is there real evidence a coordinated initiative is worth proposing, and what's the first concrete step

Keep it under 500 words. No markdown headers with #, short bolded-style labels using plain text. Be direct, avoid corporate filler, and do not force a false consensus if the data shows real disagreement or divergence by service line, name that divergence explicitly instead."""

PULSE_SYSTEM_PROMPT = """You are summarizing a team pulse for the Public Affairs team. Part 1, friction points: group the posts into themes. For each theme give the number of posts and total agrees, with representative posts quoted or closely paraphrased. Part 2, AI in our work: give counts by outcome, the barriers ranked with counts, and what worked and what didn't grouped by task type. Do not recommend solutions or tools. Do not invent anything not in the data. Under 350 words."""

DEFAULT_MODEL = "claude-sonnet-5"


def build_board_data(data: dict) -> str:
    roster = data.get("roster", [])
    notes = data.get("notes", [])
    map_notes = data.get("map", [])
    ideas = data.get("ideas") or []
    agree = data.get("agree_counts", {})
    notes_agree = agree.get("notes", {})
    map_agree = agree.get("map", {})
    ideas_agree = agree.get("ideas", {})

    service_lines = sorted({p["service_line"] for p in roster if p.get("service_line")})
    levels = sorted({p["level"] for p in roster})

    notes_text = "\n".join(
        f"- [{n.get('tag', 'Unspecified')}, {notes_agree.get(n['id'], 0)} agree] {n['text']}" for n in notes
    ) or "(none posted)"

    map_groups = {"tl": [], "tr": [], "bl": [], "br": []}
    for n in map_notes:
        q = quad_of(n["x"], n["y"])
        map_groups[q].append(f"{n['text']} [{n.get('tag', 'Unspecified')}, {map_agree.get(n['id'], 0)} agree]")

    ideas_ranked = sorted(
        (
            {"text": i["text"], "tag": i.get("tag") or "Starter bottleneck", "count": ideas_agree.get(i["id"], 0)}
            for i in ideas
        ),
        key=lambda v: v["count"],
        reverse=True,
    )
    ideas_text = "\n".join(f"- {v['count']} agree [raised by {v['tag']}]: {v['text']}" for v in ideas_ranked)

    return f"""
ROOM: {len(roster)} participants. Service lines represented: {', '.join(service_lines) or 'none recorded'}. Levels: {', '.join(levels)}

WHAT "GOOD RESEARCH" LOOKS LIKE (specific moments described by the room, tagged by service line, with agree counts):
{notes_text}

MEANING & DELEGATION MAP (tasks placed by the room; tl = meaningful+non-delegable "{QUAD_LABELS['tl']}"; tr = meaningful+delegable "{QUAD_LABELS['tr']}" [the most interesting tension zone]; bl = meaningless+non-delegable "{QUAD_LABELS['bl']}"; br = meaningless+delegable "{QUAD_LABELS['br']}" [the obvious automation wins]):
Meaningful, non-delegable (protect this): {' | '.join(map_groups['tl']) or '(none)'}
Meaningful, delegable (the tension zone, worth discussing): {' | '.join(map_groups['tr']) or '(none)'}
Meaningless, non-delegable (stuck doing tedious work AI can't take yet): {' | '.join(map_groups['bl']) or '(none)'}
Meaningless, delegable (automate these first): {' | '.join(map_groups['br']) or '(none)'}

BOTTLENECK BANK (ranked by how many people agreed it's a real bottleneck, tagged by who raised it, this is a shared-pain signal not a priority ranking):
{ideas_text}
""".strip()


def build_pulse_data(data: dict) -> str:
    """Team-pulse sessions: friction points + AI log. Never includes Level
    or any identity — the summary is shown on screen."""
    agree = data.get("agree_counts", {})
    ideas_agree = agree.get("ideas", {})
    ai_same = agree.get("ailog", {})
    posts = data.get("ideas") or []
    entries = data.get("ailog") or []

    posts_text = "\n".join(f"- [{ideas_agree.get(p['id'], 0)} agree] {p['text']}" for p in posts) or "(none posted)"

    outcome_counts: dict[str, int] = {}
    barrier_counts: dict[str, int] = {}
    for e in entries:
        outcome_counts[e.get("outcome", "")] = outcome_counts.get(e.get("outcome", ""), 0) + 1
        barrier_counts[e.get("barrier", "")] = barrier_counts.get(e.get("barrier", ""), 0) + 1
    outcomes_text = ", ".join(f"{k}: {v}" for k, v in outcome_counts.items()) or "(none)"
    barriers_text = "\n".join(
        f"- {k}: {v}" for k, v in sorted(barrier_counts.items(), key=lambda kv: kv[1], reverse=True)
    ) or "(none)"

    def fmt(e):
        parts = [f"Task: {e.get('task', '')}"]
        for label, key in (("Tool", "tool"), ("How used", "how"), ("Outcome", "outcome"), ("What worked", "worked"),
                           ("What didn't", "didnt"), ("Barrier", "barrier"), ("Barrier (other)", "barrier_other"),
                           ("Time", "time_impact")):
            if e.get(key):
                parts.append(f"{label}: {e[key]}")
        parts.append(f"Same for me: {ai_same.get(e['id'], 0)}")
        return "- " + " | ".join(parts)

    entries_text = "\n".join(fmt(e) for e in entries) or "(none)"

    return f"""
PART 1, FRICTION POINTS ({len(posts)} posts, with agree counts — agrees show a friction point is shared, not a ranking):
{posts_text}

PART 2, AI IN OUR WORK ({len(entries)} entries):
Outcome counts: {outcomes_text}
Barrier counts:
{barriers_text}
Entries:
{entries_text}
""".strip()


def stream_summary(board_data: str, system_prompt: str = SYSTEM_PROMPT, max_tokens: int = 1200):
    """Yields text chunks as they arrive from the Claude API."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not configured in Streamlit secrets."
        )
    model = st.secrets.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": board_data}],
    ) as stream:
        for text in stream.text_stream:
            yield text

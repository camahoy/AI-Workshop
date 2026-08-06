"""Builds the closing-moment synthesis by sending the live board to Claude
and streaming the response back for a typewriter-style projection."""
import streamlit as st
from anthropic import Anthropic

SEED_VOTE_IDEAS = [
    "A shared system so AM doesn't have to manually chase DP/Stats for status updates",
    "AI that drafts the first pass of a discussion guide, which a researcher then edits",
    "AI moderation running multiple qualitative conversations in parallel",
    "Faster panel selection with clear quality flags, not just speed",
    "Templates/automation for repetitive client reporting formats",
    "A clear, sellable rule for when synthetic panels are appropriate vs. human data",
    "Pricing/packaging for AI-enabled speed as a new revenue line, not just a cost saving",
    "Faster turnaround aimed at mid-market/SMB clients we currently can't afford to serve",
]

SYSTEM_PROMPT = """You are synthesizing the output of a live, cross-level workshop \
(Analyst through SVP/CEO) at a market research company about AI adoption. The \
company faces flat-to-declining organic revenue and is investing in AI \
transformation, but wants to grow revenue WITHOUT reducing headcount, and wants \
AI adoption to be mindful and sustainable rather than rushed.

Write a tight, decision-useful summary with these sections, using plain language, \
grounded ONLY in the data given (do not invent specifics not implied by the input):
1. What the room agrees "good research" actually requires (2-3 sentences, \
synthesized from the notes)
2. Where the room is aligned vs. split on where AI should touch the work (from \
the agency map)
3. Top 3 priorities by vote, and why they matter commercially
4. The pulse gap (between AI being applied well vs. people having a say) and what \
it implies
5. Three concrete next steps that would grow revenue and keep AI adoption \
mindful/sustainable, explicitly without relying on headcount reduction

Keep it under 400 words. No markdown headers with #, just short bolded-style \
labels using plain text. Be direct and avoid corporate filler."""

DEFAULT_MODEL = "claude-sonnet-5"


def build_board_data(roster, notes, map_data, votes, pulse) -> str:
    levels = sorted({p["level"] for p in roster})
    votes_ranked = sorted(
        (
            {"idea": idea, "count": votes.get(str(i), 0)}
            for i, idea in enumerate(SEED_VOTE_IDEAS)
        ),
        key=lambda v: v["count"],
        reverse=True,
    )
    notes_text = "\n".join(f"- {n['text']}" for n in notes) or "(none posted)"
    votes_text = "\n".join(
        f"- {v['count']} votes: {v['idea']}" for v in votes_ranked
    )

    return f"""
ROOM: {len(roster)} participants across levels: {', '.join(levels)}

WHAT "GOOD RESEARCH" MEANS TO THE ROOM (raw sticky notes):
{notes_text}

AGENCY MAP — where AI removes drudgery vs. removes judgment:
Low AI / Removes Drudgery: {' | '.join(map_data.get('tl', [])) or '(none)'}
High AI / Removes Drudgery: {' | '.join(map_data.get('tr', [])) or '(none)'}
Low AI / Removes Judgment: {' | '.join(map_data.get('bl', [])) or '(none)'}
High AI / Removes Judgment: {' | '.join(map_data.get('br', [])) or '(none)'}

DOT VOTE RESULTS (ranked, out of {len(roster) * 3} possible votes):
{votes_text}

CLOSING PULSE:
Q1 "AI applied to the right parts of my work" - {pulse.get('q1', {})}
Q2 "I have a say in how AI gets applied" - {pulse.get('q2', {})}
""".strip()


def stream_summary(board_data: str):
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
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": board_data}],
    ) as stream:
        for text in stream.text_stream:
            yield text

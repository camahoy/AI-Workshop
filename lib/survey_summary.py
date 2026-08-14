"""Builds the AI-generated synthesis for the N = Everyone results page.
Separate from lib/claude_summary.py (the live board's closing synthesis) —
different audience, different data shape, different system prompt."""
import streamlit as st
from anthropic import Anthropic

SYSTEM_PROMPT = """You are synthesizing results from "N = Everyone," an anonymous, company-wide survey about current AI usage, tool effectiveness, and where people want AI to show up (or not) in their work. This is a standalone follow-up to a live cross-division workshop, feeding the same case for a formal AI strategy initiative with a broader, asynchronous sample.

Write a tight, decision-useful summary for a CEO/leadership audience, using plain language, grounded ONLY in the data given (do not invent specifics not implied by the input). State the sample size explicitly, and if any service line has too few responses to report separately, say so rather than presenting the results as more representative than they are.

Sections:
1. Current AI usage and tool effectiveness patterns: what people actually use, how often, and how effective they say it is
2. Where people want AI most vs. least: drawing on which tasks AI could realistically take on (the task-level data) and the "magic wand" open responses, contrasted with where people explicitly do not want AI involved
3. Trust and readiness signals: confidence in AI output, trust vs. human-led work, and how easy or hard it currently is to integrate AI day to day
4. The investment-priority results (approximate MaxDiff best-minus-worst scores) and what they mean for where to invest first — note this is a lightweight approximation, not full MaxDiff rigor
5. A synthesis of the open-ended themes, especially what people said leadership should fund and anything else they flagged as important

Keep it under 600 words. No markdown headers with #, short bolded-style labels using plain text. Be direct, avoid corporate filler, and do not force a false consensus if the data shows real disagreement, name that divergence explicitly instead."""

DEFAULT_MODEL = "claude-sonnet-5"


def stream_summary(results_text: str):
    """Yields text chunks as they arrive from the Claude API."""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not configured in Streamlit secrets.")
    model = st.secrets.get("ANTHROPIC_MODEL", DEFAULT_MODEL)
    client = Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model,
        max_tokens=1400,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": results_text}],
    ) as stream:
        for text in stream.text_stream:
            yield text

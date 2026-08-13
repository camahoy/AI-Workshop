"""Interactive "N = Everyone" questionnaire: a live, in-app, simplified
version of questionnaire/AI-Perceptions-Questionnaire-Draft.docx.

Simplified deliberately, since a few things in the draft only make sense
on a real survey platform, not a live workshop board:
  - True piped grids (B2/C1) become one combined frequency+effectiveness
    block per tool the respondent actually selected at B1.
  - D1a's per-task AI-capability/meaningfulness grid is dropped — that
    exact question (is this task meaningful, could AI take it) is already
    covered, more richly, by the Meaning & Delegation Map tab. D1 itself
    (which tasks you spend time on) is kept as a behavioral signal.
  - F4's balanced-incomplete-block MaxDiff design becomes a single
    top-choice / lowest-choice pick — same "force a real trade-off"
    spirit, without needing a real MaxDiff module.
  - B3b/B3c (detail on a self-built tool) are dropped; B3/B3a are kept.

Responses are stored per device_id (never a name), and only ever surfaced
as aggregates — no individual open-ended answer is displayed anywhere in
the UI, matching the questionnaire's own "reported in aggregate, not by
name" privacy model.
"""

TASK_BANK = [
    "Research data pre-processing", "Research execution", "Design / concept work", "Writing",
    "Emailing", "Deliverable creation", "Translating language", "AI moderation",
    "Research support", "Thinking support (second set of eyes)", "Knowledge summarization",
    "Design generation", "Image generation", "Document creation", "Knowledge interaction",
    "Information retrieval", "Administrative execution",
]

TOOL_OPTIONS = [
    "Company-provided Copilot",
    "A personal ChatGPT, Claude, Gemini, or similar account, used for work tasks",
    "An internal tool or agent built by my division or team",
    "A third-party research platform with AI features",
    "Something else",
    "None of the above",
]
# The tools specific enough to ask a per-tool frequency/effectiveness follow-up about.
DETAILED_TOOLS = TOOL_OPTIONS[:4]

FREQ_OPTIONS = ["Daily", "A few times a week", "A few times a month", "Rarely"]
TENURE_OPTIONS = ["Less than 1 year", "1 to 3 years", "4 to 7 years", "8+ years"]
AWARE_OPTIONS = ["Yes", "No", "Not sure"]
E4_OPTIONS = [
    "I want to use it more than I currently can",
    "I'm using it about the right amount",
    "I'm being asked or expected to use it more than I'm comfortable with",
    "I don't think it belongs in my role",
    "Not sure",
]
PRIORITY_OPTIONS = [
    "Tools that make existing work faster / more efficient",
    "Tools that improve quality or accuracy of output",
    "Client-facing AI capabilities",
    "Training and skill-building so people can use AI well",
    "Governance, data security, and clear rules for appropriate use",
]

# (field, label) for the six 1-5 attitude scales, reused by both the live
# results panel and the Claude prompt builder.
SCALE_QUESTIONS = [
    ("c3_rating", "Current AI tools fit the work you do"),
    ("e1", "Confident AI output is accurate enough with light review"),
    ("e2", "Trust AI-assisted research vs. fully human-led"),
    ("e3", "Easy to integrate AI into day-to-day work"),
    ("f1", "Have a say in how AI tools are selected"),
    ("f2", "Tools are actually built for how your division works"),
]

OPEN_TEXT_FIELDS = ("c2_limitation", "d2_wand", "d3_not_want", "e5_trust", "f3_fund", "g1_other")

STEPS = ["ab", "cd", "ef", "g"]


def aggregate(responses: dict) -> dict:
    """Computes aggregate-only stats from {device_id: response_dict}. No
    individual response is ever exposed by this function's return value
    beyond raw open-text excerpts, which come back unattributed."""
    n = len(responses)
    result = {"n": n}
    if n == 0:
        return result

    tool_counts = {t: 0 for t in TOOL_OPTIONS}
    tool_detail = {t: {"freq_counts": {f: 0 for f in FREQ_OPTIONS}, "eff_sum": 0, "eff_n": 0} for t in DETAILED_TOOLS}
    task_counts = {t: 0 for t in TASK_BANK}
    scale_sums = {k: 0 for k, _ in SCALE_QUESTIONS}
    scale_ns = {k: 0 for k, _ in SCALE_QUESTIONS}
    e4_counts = {o: 0 for o in E4_OPTIONS}
    tenure_counts = {o: 0 for o in TENURE_OPTIONS}
    aware_counts = {o: 0 for o in AWARE_OPTIONS}
    built_counts = {"Yes": 0, "No": 0}
    priority_top = {o: 0 for o in PRIORITY_OPTIONS}
    priority_low = {o: 0 for o in PRIORITY_OPTIONS}
    open_text_counts = {k: 0 for k in OPEN_TEXT_FIELDS}

    for r in responses.values():
        for t in r.get("b1_tools", []):
            if t in tool_counts:
                tool_counts[t] += 1
        for t, det in (r.get("b1_detail") or {}).items():
            if t not in tool_detail:
                continue
            f = det.get("freq")
            if f in tool_detail[t]["freq_counts"]:
                tool_detail[t]["freq_counts"][f] += 1
            e = det.get("effectiveness")
            if isinstance(e, (int, float)):
                tool_detail[t]["eff_sum"] += e
                tool_detail[t]["eff_n"] += 1
        for t in r.get("d1_tasks", []):
            if t in task_counts:
                task_counts[t] += 1
        for key, _ in SCALE_QUESTIONS:
            v = r.get(key)
            if isinstance(v, (int, float)):
                scale_sums[key] += v
                scale_ns[key] += 1
        if r.get("e4") in e4_counts:
            e4_counts[r["e4"]] += 1
        if r.get("a3_tenure") in tenure_counts:
            tenure_counts[r["a3_tenure"]] += 1
        if r.get("b4_aware") in aware_counts:
            aware_counts[r["b4_aware"]] += 1
        if r.get("b3_built") in built_counts:
            built_counts[r["b3_built"]] += 1
        if r.get("f4_top") in priority_top:
            priority_top[r["f4_top"]] += 1
        if r.get("f4_low") in priority_low:
            priority_low[r["f4_low"]] += 1
        for key in OPEN_TEXT_FIELDS:
            if (r.get(key) or "").strip():
                open_text_counts[key] += 1

    scale_avgs = {k: (scale_sums[k] / scale_ns[k] if scale_ns[k] else None) for k, _ in SCALE_QUESTIONS}
    tool_avg_eff = {t: (d["eff_sum"] / d["eff_n"] if d["eff_n"] else None) for t, d in tool_detail.items()}

    result.update(
        tool_counts=tool_counts,
        tool_detail=tool_detail,
        tool_avg_eff=tool_avg_eff,
        task_counts=task_counts,
        scale_avgs=scale_avgs,
        e4_counts=e4_counts,
        tenure_counts=tenure_counts,
        aware_counts=aware_counts,
        built_counts=built_counts,
        priority_top=priority_top,
        priority_low=priority_low,
        open_text_counts=open_text_counts,
    )
    return result


def to_prompt_text(responses: dict, excerpt_limit: int = 40) -> str:
    """Renders the aggregate as compact text for the Claude summary prompt.
    Open-ended excerpts are included unattributed (no service line/title),
    since this survey's own privacy model is stricter than the rest of the
    board's tagged posts."""
    agg = aggregate(responses)
    n = agg["n"]
    if n == 0:
        return "(no survey responses yet)"

    lines = [f"{n} response{'s' if n != 1 else ''}."]
    scale_bits = [
        f"{label} = {agg['scale_avgs'][key]:.1f}/5"
        for key, label in SCALE_QUESTIONS
        if agg["scale_avgs"].get(key) is not None
    ]
    lines.append("Attitude averages: " + (", ".join(scale_bits) or "(none yet)"))

    tool_bits = [f"{t} {agg['tool_counts'].get(t, 0)}/{n}" for t in TOOL_OPTIONS if t != "None of the above"]
    lines.append("Tool usage: " + ", ".join(tool_bits))

    top_bits = [f"{o} ({agg['priority_top'].get(o, 0)})" for o in PRIORITY_OPTIONS]
    low_bits = [f"{o} ({agg['priority_low'].get(o, 0)})" for o in PRIORITY_OPTIONS]
    lines.append("Investment priority, top picks: " + ", ".join(top_bits))
    lines.append("Investment priority, lowest picks: " + ", ".join(low_bits))

    excerpts = []
    for r in responses.values():
        for key in OPEN_TEXT_FIELDS:
            v = (r.get(key) or "").strip()
            if v:
                excerpts.append(v)
    if excerpts:
        lines.append("Open-ended excerpts (unattributed): " + " | ".join(excerpts[:excerpt_limit]))

    return "\n".join(lines)

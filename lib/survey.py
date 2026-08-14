"""Data model, question metadata, and aggregation logic for the "N =
Everyone" survey app (pages/1_N_Everyone_Survey.py) and its gated results
page (pages/2_Survey_Results.py). Sourced from
questionnaire/AI-Perceptions-Questionnaire-Draft.docx.

Two things are deliberately simplified relative to running this on a real
survey platform (Qualtrics/Sawtooth), both flagged in-app to whoever reads
the results, not silently:

  - F4 (investment priority) is NOT a true balanced-incomplete-block
    MaxDiff design. With only 5 priority items, though, there are exactly
    5 unique 4-item subsets (each leaving one item out) — so
    `generate_maxdiff_sets()` just shows all 5 leave-one-out subsets,
    shuffled, which gives every item balanced exposure (4 of 5 sets) for
    free. Scoring is the standard lightweight MaxDiff approximation:
    (times chosen best − times chosen worst) / times shown, per item.
    This is a reasonable trade-off approximation, not full MaxDiff rigor
    (no hierarchical Bayes, no individual-level utilities) — good enough
    to rank priorities, not to defend a precise utility score.
  - Grid questions (B2, C1, D1a) are real per-row matrix questions, but
    D1a is capped at 8 rows (randomly sampled from the respondent's D1
    selections if they picked more), to keep a self-administered mobile
    form from running too long.
"""
import random
import time

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
# The tools specific enough to ask per-tool B2/C1 follow-ups about.
DETAILED_TOOLS = TOOL_OPTIONS[:4]

FREQ_OPTIONS = ["Daily", "A few times a week", "A few times a month", "Rarely"]
TENURE_OPTIONS = ["Less than 1 year", "1 to 3 years", "4 to 7 years", "8+ years"]
AWARE_OPTIONS = ["Yes", "No", "Not sure"]
SHARED_OPTIONS = ["Yes, just me so far", "Yes, a few people", "Yes, most of the team", "Not yet, but I plan to share it"]
E4_OPTIONS = [
    "I want to use it more than I currently can",
    "I'm using it about the right amount",
    "I'm being asked or expected to use it more than I'm comfortable with",
    "I don't think it belongs in my role",
    "Not sure",
]
COULD_AI_OPTIONS = ["Fully", "AI drafts, I finish", "Not really"]
PRIORITY_OPTIONS = [
    "Tools that make existing work faster / more efficient",
    "Tools that improve quality or accuracy of output",
    "Client-facing AI capabilities",
    "Training and skill-building so people can use AI well",
    "Governance, data security, and clear rules for appropriate use",
]
D1A_CAP = 8
MAXDIFF_SET_SIZE = 4

# (field, label) for the six 1-5 attitude scales.
SCALE_QUESTIONS = [
    ("c3_rating", "Current AI tools fit the work you do"),
    ("e1", "Confident AI output is accurate enough with light review"),
    ("e2", "Trust AI-assisted research vs. fully human-led"),
    ("e3", "Easy to integrate AI into day-to-day work"),
    ("f1", "Have a say in how AI tools are selected"),
    ("f2", "Tools are actually built for how your division works"),
]

OPEN_TEXT_FIELDS = ("b1_other_desc", "c2_limitation", "d2_wand", "d3_not_want", "e5_trust", "f3_fund", "g1_other")
OPEN_TEXT_LABELS = {
    "b1_other_desc": "B1 — the other AI tool named",
    "c2_limitation": "C2 — biggest limitation of current AI tools",
    "d2_wand": "D2 — magic wand: what would you hand off to AI",
    "d3_not_want": "D3 — where you would NOT want AI involved",
    "e5_trust": "E5 — what would need to be true to trust AI more",
    "f3_fund": "F3 — one thing leadership could fund or build",
    "g1_other": "G1 — anything else leadership should know",
}

STEPS = ["ab", "cd1", "d1a", "e", "f", "g"]

MIN_OPEN_TEXT_CHARS = 15


def under_min_length(text: str, min_chars: int = MIN_OPEN_TEXT_CHARS) -> bool:
    t = (text or "").strip()
    return bool(t) and len(t) < min_chars


def sample_d1a_tasks(selected: list[str], cap: int = D1A_CAP) -> list[str]:
    if len(selected) <= cap:
        return list(selected)
    return random.sample(selected, cap)


def is_straightlining(d1a: dict) -> bool:
    """True if the respondent gave the identical "could AI take this on"
    answer for every row of D1a (and there were at least 3 rows to judge
    that from)."""
    vals = [v.get("could_ai") for v in (d1a or {}).values() if v.get("could_ai")]
    return len(vals) >= 3 and len(set(vals)) == 1


def generate_maxdiff_sets() -> list[list[str]]:
    """5 sets, each the 4 priority items left after excluding exactly one
    — the only 5 unique 4-item subsets of a 5-item list. Gives every item
    balanced exposure (shown in 4 of 5 sets) without a real MaxDiff
    generator. Order of items within each set, and order of the sets
    themselves, are shuffled per respondent."""
    sets = []
    for leave_out in PRIORITY_OPTIONS:
        subset = [i for i in PRIORITY_OPTIONS if i != leave_out]
        random.shuffle(subset)
        sets.append(subset)
    random.shuffle(sets)
    return sets


def aggregate(responses: list[dict]) -> dict:
    """Computes aggregate-only stats from a list of response dicts (as
    returned by survey_db.all_responses()). No individual response is
    exposed beyond raw open-text excerpts, which come back unattributed
    unless include_tags=True is handled by the caller."""
    n = len(responses)
    result = {"n": n}
    if n == 0:
        return result

    tool_counts = {t: 0 for t in TOOL_OPTIONS}
    b2_freq = {t: {f: 0 for f in FREQ_OPTIONS} for t in DETAILED_TOOLS}
    c1_eff_sum = {t: 0 for t in DETAILED_TOOLS}
    c1_eff_n = {t: 0 for t in DETAILED_TOOLS}
    task_counts = {t: 0 for t in TASK_BANK}
    scale_sums = {k: 0 for k, _ in SCALE_QUESTIONS}
    scale_ns = {k: 0 for k, _ in SCALE_QUESTIONS}
    e4_counts = {o: 0 for o in E4_OPTIONS}
    tenure_counts = {o: 0 for o in TENURE_OPTIONS}
    aware_counts = {o: 0 for o in AWARE_OPTIONS}
    built_counts = {"Yes": 0, "No": 0}
    shared_counts = {o: 0 for o in SHARED_OPTIONS}
    open_text_counts = {k: 0 for k in OPEN_TEXT_FIELDS}

    d1a_asked = {t: 0 for t in TASK_BANK}
    d1a_could = {t: {o: 0 for o in COULD_AI_OPTIONS} for t in TASK_BANK}
    d1a_meaningful_sum = {t: 0 for t in TASK_BANK}
    d1a_meaningful_n = {t: 0 for t in TASK_BANK}

    maxdiff_shown = {o: 0 for o in PRIORITY_OPTIONS}
    maxdiff_best = {o: 0 for o in PRIORITY_OPTIONS}
    maxdiff_worst = {o: 0 for o in PRIORITY_OPTIONS}

    straightlining_n = 0
    ttc_sum = 0.0
    ttc_n = 0

    for r in responses:
        for t in r.get("b1_tools", []):
            if t in tool_counts:
                tool_counts[t] += 1
        for t, f in (r.get("b2_freq") or {}).items():
            if t in b2_freq and f in b2_freq[t]:
                b2_freq[t][f] += 1
        for t, e in (r.get("c1_eff") or {}).items():
            if t in c1_eff_sum and isinstance(e, (int, float)):
                c1_eff_sum[t] += e
                c1_eff_n[t] += 1
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
        if r.get("b3c_shared") in shared_counts:
            shared_counts[r["b3c_shared"]] += 1
        for key in OPEN_TEXT_FIELDS:
            if (r.get(key) or "").strip():
                open_text_counts[key] += 1

        for t, det in (r.get("d1a") or {}).items():
            if t not in d1a_asked:
                continue
            d1a_asked[t] += 1
            ca = det.get("could_ai")
            if ca in d1a_could[t]:
                d1a_could[t][ca] += 1
            m = det.get("meaningful")
            if isinstance(m, (int, float)):
                d1a_meaningful_sum[t] += m
                d1a_meaningful_n[t] += 1

        for s in r.get("f4_sets", []):
            items = s.get("items", [])
            for it in items:
                if it in maxdiff_shown:
                    maxdiff_shown[it] += 1
            best = s.get("best")
            worst = s.get("worst")
            if best in maxdiff_best:
                maxdiff_best[best] += 1
            if worst in maxdiff_worst:
                maxdiff_worst[worst] += 1

        if r.get("_straightlining"):
            straightlining_n += 1
        ttc = r.get("_time_to_complete_seconds")
        if isinstance(ttc, (int, float)) and ttc > 0:
            ttc_sum += ttc
            ttc_n += 1

    scale_avgs = {k: (scale_sums[k] / scale_ns[k] if scale_ns[k] else None) for k, _ in SCALE_QUESTIONS}
    c1_avg_eff = {t: (c1_eff_sum[t] / c1_eff_n[t] if c1_eff_n[t] else None) for t in DETAILED_TOOLS}
    d1a_meaningful_avg = {t: (d1a_meaningful_sum[t] / d1a_meaningful_n[t] if d1a_meaningful_n[t] else None) for t in TASK_BANK}
    maxdiff_score = {
        o: ((maxdiff_best[o] - maxdiff_worst[o]) / maxdiff_shown[o] if maxdiff_shown[o] else None)
        for o in PRIORITY_OPTIONS
    }

    result.update(
        tool_counts=tool_counts,
        b2_freq=b2_freq,
        c1_avg_eff=c1_avg_eff,
        task_counts=task_counts,
        scale_avgs=scale_avgs,
        e4_counts=e4_counts,
        tenure_counts=tenure_counts,
        aware_counts=aware_counts,
        built_counts=built_counts,
        shared_counts=shared_counts,
        open_text_counts=open_text_counts,
        d1a_asked=d1a_asked,
        d1a_could=d1a_could,
        d1a_meaningful_avg=d1a_meaningful_avg,
        maxdiff_shown=maxdiff_shown,
        maxdiff_best=maxdiff_best,
        maxdiff_worst=maxdiff_worst,
        maxdiff_score=maxdiff_score,
        straightlining_n=straightlining_n,
        avg_time_to_complete_seconds=(ttc_sum / ttc_n if ttc_n else None),
    )
    return result


def service_line_buckets(responses: list[dict], min_n: int = 5) -> dict[str, list[dict]]:
    """Groups responses by service line, rolling any service line below
    min_n responses into a combined "Other" bucket rather than showing an
    unreliable small-sample breakout."""
    buckets: dict[str, list[dict]] = {}
    for r in responses:
        sl = (r.get("service_line") or "Unspecified").strip() or "Unspecified"
        buckets.setdefault(sl, []).append(r)
    real = {sl: rs for sl, rs in buckets.items() if len(rs) >= min_n}
    other = [r for sl, rs in buckets.items() if len(rs) < min_n for r in rs]
    if other:
        real["Other (service lines below reporting threshold)"] = other
    return real


def to_results_prompt_text(responses: list[dict], excerpt_limit: int = 60) -> str:
    """Renders tabulated results + open-text excerpts as text for the
    results page's Claude synthesis. Excerpts are unattributed (service
    line/title not attached to the excerpt itself)."""
    agg = aggregate(responses)
    n = agg["n"]
    if n == 0:
        return "(no survey responses yet)"

    lines = [f"{n} response{'s' if n != 1 else ''}."]

    tool_bits = [f"{t}: {agg['tool_counts'].get(t, 0)}/{n}" for t in TOOL_OPTIONS if t != "None of the above"]
    lines.append("TOOL USAGE (B1): " + ", ".join(tool_bits))

    for t in DETAILED_TOOLS:
        freq = agg["b2_freq"].get(t, {})
        freq_bits = ", ".join(f"{f}={c}" for f, c in freq.items() if c)
        eff = agg["c1_avg_eff"].get(t)
        eff_bit = f"{eff:.1f}/5 avg effectiveness" if eff is not None else "no effectiveness data"
        if freq_bits or eff is not None:
            lines.append(f"  {t} — frequency: {freq_bits or '(none)'}; {eff_bit}")

    lines.append(f"Built own tool (B3): Yes {agg['built_counts'].get('Yes', 0)}/{n}, No {agg['built_counts'].get('No', 0)}/{n}")
    lines.append("Aware of other divisions' tools (B4): " + ", ".join(f"{o}={agg['aware_counts'].get(o, 0)}" for o in AWARE_OPTIONS))

    scale_bits = [f"{label} = {agg['scale_avgs'][key]:.1f}/5" for key, label in SCALE_QUESTIONS if agg["scale_avgs"].get(key) is not None]
    lines.append("ATTITUDE AVERAGES (C3, E1-E3, F1-F2, 1-5 scale): " + (", ".join(scale_bits) or "(none yet)"))

    lines.append("HOW AI SHOWS UP GOING FORWARD (E4): " + ", ".join(f"{o}={agg['e4_counts'].get(o, 0)}" for o in E4_OPTIONS))

    task_bits = [f"{t}: {agg['task_counts'].get(t, 0)}/{n}" for t in TASK_BANK if agg["task_counts"].get(t, 0)]
    lines.append("TIME SPENT BY TASK (D1, behavioral): " + (", ".join(task_bits) or "(none)"))

    d1a_bits = []
    for t in TASK_BANK:
        asked = agg["d1a_asked"].get(t, 0)
        if not asked:
            continue
        could = agg["d1a_could"].get(t, {})
        m = agg["d1a_meaningful_avg"].get(t)
        m_bit = f"{m:.1f}/5 meaningful" if m is not None else ""
        could_bit = ", ".join(f"{k}={v}" for k, v in could.items() if v)
        d1a_bits.append(f"{t} (asked of {asked}): {could_bit}; {m_bit}")
    lines.append("COULD AI TAKE THIS ON, PER TASK (D1a, only asked of respondents who selected that task at D1): " + (" | ".join(d1a_bits) or "(none)"))

    maxdiff_bits = sorted(
        (f"{o} = {agg['maxdiff_score'][o]:.2f} (shown {agg['maxdiff_shown'][o]}, best {agg['maxdiff_best'][o]}, worst {agg['maxdiff_worst'][o]})" for o in PRIORITY_OPTIONS if agg["maxdiff_score"].get(o) is not None),
        reverse=True,
    )
    lines.append(
        "INVESTMENT PRIORITY (F4, approximate MaxDiff — best-minus-worst share per item, range -1 to 1, higher = higher priority): "
        + (", ".join(maxdiff_bits) or "(none)")
    )

    lines.append(
        f"DATA QUALITY: {agg['straightlining_n']}/{n} flagged for straightlining on D1a (same answer every row); "
        + (f"average completion time {agg['avg_time_to_complete_seconds'] / 60:.1f} minutes" if agg["avg_time_to_complete_seconds"] else "no timing data")
    )

    for key in OPEN_TEXT_FIELDS:
        excerpts = [(r.get(key) or "").strip() for r in responses if (r.get(key) or "").strip()]
        if excerpts:
            lines.append(f"{OPEN_TEXT_LABELS[key]} ({len(excerpts)} responses, sample): " + " | ".join(excerpts[:excerpt_limit]))

    return "\n".join(lines)

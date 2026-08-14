"""N = Everyone — Results: tabulated survey results, full open-end
responses, and an AI-generated synthesis. Gated by a shared passphrase
(not real authentication — this just keeps it off the same link
respondents use to take the survey)."""
import streamlit as st

from lib import survey, survey_db, survey_summary, theme

st.set_page_config(page_title="N = Everyone — Results", page_icon="📊", layout="centered")
theme.inject()


def render_gate():
    theme.header("N = Everyone", "Results (facilitator only)")
    configured = st.secrets.get("SURVEY_RESULTS_PASSWORD")
    if not configured:
        st.caption("No SURVEY_RESULTS_PASSWORD is set in secrets — anyone with this page's URL can view results. Set one in Streamlit secrets to require it.")
        st.session_state["results_authed"] = True
        return
    st.markdown(
        '<div class="prompt-box"><div class="label">Passphrase required</div>'
        "<p>This page is not the survey link — it's for whoever's running this initiative to review results.</p></div>",
        unsafe_allow_html=True,
    )
    pw = st.text_input("Passphrase", type="password", key="results_pw")
    if st.button("View results", type="primary"):
        if pw == configured:
            st.session_state["results_authed"] = True
            st.rerun()
        else:
            st.error("Incorrect passphrase.")


def pct(n, d):
    return f"{n} ({n / d:.0%})" if d else f"{n} (0%)"


def render_scale_block(agg, n):
    st.markdown("#### Attitude averages (1–5 scale)")
    for key, label in survey.SCALE_QUESTIONS:
        avg = agg["scale_avgs"].get(key)
        if avg is None:
            st.caption(f"{label} — no data")
            continue
        st.caption(f"{label} — {avg:.1f}/5")
        st.progress(avg / 5)


def render_tool_block(agg, n):
    st.markdown("#### Tool usage (B1) and per-tool detail (B2/C1)")
    for t in survey.TOOL_OPTIONS:
        if t == "None of the above":
            continue
        c = agg["tool_counts"].get(t, 0)
        st.markdown(f"**{t}** — {pct(c, n)}")
        if t in survey.DETAILED_TOOLS and c:
            freq = agg["b2_freq"].get(t, {})
            freq_bits = ", ".join(f"{f}: {v}" for f, v in freq.items() if v)
            eff = agg["c1_avg_eff"].get(t)
            eff_bit = f"{eff:.1f}/5 avg effectiveness" if eff is not None else "no effectiveness data"
            st.caption(f"Frequency — {freq_bits or '(none recorded)'}. Effectiveness — {eff_bit}.")

    st.markdown("#### Custom tools and cross-division awareness (B3/B4)")
    st.caption(f"Built or requested a custom tool (B3): Yes {pct(agg['built_counts'].get('Yes', 0), n)}, No {pct(agg['built_counts'].get('No', 0), n)}")
    aware_bits = ", ".join(f"{o}: {pct(agg['aware_counts'].get(o, 0), n)}" for o in survey.AWARE_OPTIONS)
    st.caption(f"Aware of other divisions' tools (B4): {aware_bits}")


def render_task_block(agg, n):
    st.markdown("#### Time spent by task (D1, behavioral)")
    ranked = sorted(survey.TASK_BANK, key=lambda t: agg["task_counts"].get(t, 0), reverse=True)
    for t in ranked:
        c = agg["task_counts"].get(t, 0)
        if c:
            st.caption(f"{t} — {pct(c, n)}")

    st.markdown("#### Could AI take this on? Per task (D1a — only asked of respondents who selected that task at D1)")
    asked_tasks = [t for t in survey.TASK_BANK if agg["d1a_asked"].get(t, 0)]
    if not asked_tasks:
        st.markdown('<div class="empty-note">No D1a data yet.</div>', unsafe_allow_html=True)
    for t in asked_tasks:
        asked = agg["d1a_asked"][t]
        could = agg["d1a_could"].get(t, {})
        m = agg["d1a_meaningful_avg"].get(t)
        could_bits = ", ".join(f"{k}: {v}" for k, v in could.items() if v)
        m_bit = f"{m:.1f}/5 meaningful" if m is not None else "no data"
        st.caption(f"**{t}** (asked of {asked}) — {could_bits}; {m_bit}")


def render_maxdiff_block(agg):
    st.markdown("#### Investment priority (F4, approximate MaxDiff)")
    st.caption("Best-minus-worst share per item, range -1 to 1, higher = higher priority. See the note at the bottom of this page for what \"approximate\" means here.")
    ranked = sorted(
        (o for o in survey.PRIORITY_OPTIONS if agg["maxdiff_score"].get(o) is not None),
        key=lambda o: agg["maxdiff_score"][o],
        reverse=True,
    )
    if not ranked:
        st.markdown('<div class="empty-note">No F4 data yet.</div>', unsafe_allow_html=True)
    for o in ranked:
        score = agg["maxdiff_score"][o]
        st.caption(f"{o} — score {score:+.2f} (shown {agg['maxdiff_shown'][o]}, best {agg['maxdiff_best'][o]}, worst {agg['maxdiff_worst'][o]})")
        st.progress((score + 1) / 2)


def render_open_text_block(responses):
    st.markdown("#### Open-ended responses, in full")
    st.caption("Grouped by question, unattributed (no service line or title attached) — this is the questionnaire's own stricter anonymity standard for open text.")
    for key in survey.OPEN_TEXT_FIELDS:
        excerpts = [(r.get(key) or "").strip() for r in responses if (r.get(key) or "").strip()]
        with st.expander(f"{survey.OPEN_TEXT_LABELS[key]} ({len(excerpts)})"):
            if not excerpts:
                st.caption("No responses yet.")
            for e in excerpts:
                st.markdown(f'<div class="note">{theme.esc(e)}</div>', unsafe_allow_html=True)


def render_service_line_block(responses):
    st.markdown("#### By service line")
    min_n = st.number_input("Minimum N to report a service line separately", min_value=1, max_value=20, value=5, key="min_n_input")
    buckets = survey.service_line_buckets(responses, min_n=int(min_n))
    st.caption("Service lines below the threshold are rolled into \"Other\" rather than shown as an unreliable small-sample number.")
    for sl, rs in sorted(buckets.items(), key=lambda kv: len(kv[1]), reverse=True):
        agg = survey.aggregate(rs)
        avgs = [f"{label} {agg['scale_avgs'][k]:.1f}" for k, label in survey.SCALE_QUESTIONS if agg["scale_avgs"].get(k) is not None]
        st.caption(f"**{sl}** — n={len(rs)}. " + (", ".join(avgs) if avgs else "no scale data"))


def render_results():
    responses = survey_db.all_responses()
    n = len(responses)
    agg = survey.aggregate(responses)

    theme.header("N = Everyone", "Results")
    st.markdown(f'<div class="board-status">{n} response{"s" if n != 1 else ""} recorded</div>', unsafe_allow_html=True)

    if n == 0:
        st.markdown('<div class="empty-note">No survey responses yet.</div>', unsafe_allow_html=True)
        return

    flagged = agg["straightlining_n"]
    avg_ttc = agg["avg_time_to_complete_seconds"]
    ttc_bit = f"{avg_ttc / 60:.1f} min average completion time" if avg_ttc else "no timing data"
    st.caption(f"Data quality: {flagged}/{n} flagged for straightlining on D1a (same answer every row, not auto-excluded, for manual review) · {ttc_bit}")

    render_scale_block(agg, n)
    st.divider()
    render_tool_block(agg, n)
    st.divider()
    render_task_block(agg, n)
    st.divider()
    render_maxdiff_block(agg)
    st.divider()
    render_service_line_block(responses)
    st.divider()
    render_open_text_block(responses)
    st.divider()

    st.markdown("#### AI-generated synthesis")
    if st.session_state.get("results_summary_error"):
        st.error(st.session_state["results_summary_error"])
    if st.button("Generate synthesis from survey results", type="primary"):
        st.session_state.pop("results_summary_error", None)
        results_text = survey.to_results_prompt_text(responses)
        placeholder = st.empty()
        accumulated = ""
        try:
            for chunk in survey_summary.stream_summary(results_text):
                accumulated += chunk
                placeholder.markdown(f'<div class="summary-output">{theme.esc(accumulated)}▌</div>', unsafe_allow_html=True)
            placeholder.markdown(f'<div class="summary-output">{theme.esc(accumulated)}</div>', unsafe_allow_html=True)
        except Exception as e:
            st.session_state["results_summary_error"] = f"Could not generate synthesis: {e}"
            st.rerun()

    st.divider()
    st.caption(
        "Simplification note: F4 uses 5 leave-one-out sets (the only 5 unique 4-item subsets of a 5-item list) "
        "rather than a real balanced-incomplete-block MaxDiff design, and scores are a simple best-minus-worst "
        "share, not hierarchical-Bayes individual utilities. Good enough to rank priorities, not to defend a "
        "precise statistical score. D1a is capped at 8 rows per respondent (randomly sampled if more were "
        "selected at D1) to keep the form from running long."
    )


def main():
    if not st.session_state.get("results_authed"):
        render_gate()
    else:
        render_results()


main()

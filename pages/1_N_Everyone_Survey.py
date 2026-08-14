"""N = Everyone: the real, standalone AI Perceptions & Workflow Assessment
survey. Open to the whole company via a shared link, no login required.
Answers persist to a SQLite file (lib/survey_db.py) independent of the
live board's ephemeral per-session state, since this is meant to field
for about two weeks rather than reset with a workshop.

See lib/survey.py's module docstring for what was simplified relative to
a real survey platform (MaxDiff via leave-one-out sets, D1a capped at 8
rows) and why.
"""
import time

import streamlit as st

from lib import survey, survey_db, theme

st.set_page_config(page_title="N = Everyone — Survey", page_icon="📝", layout="centered")
theme.inject()


# Streamlit drops a widget's session_state entry once that widget stops
# being drawn on a rerun, so per-step answers can't just live in the
# widget keys — each step's values are copied into a plain, non-widget
# "survey_draft" dict in session_state before the step changes, and
# widgets read their defaults from that draft. (Confirmed the hard way
# building the live board's earlier in-app wizard — Back/Next silently
# dropped every prior step's answers without this.)
def sync_step_ab(draft):
    ss = st.session_state
    tools = ss.get("sv_b1_tools", [])
    b2_freq = {}
    for t in tools:
        if t in survey.DETAILED_TOOLS:
            b2_freq[t] = ss.get(f"sv_b2_freq_{t}", survey.FREQ_OPTIONS[0])
    draft.update(
        service_line=(ss.get("sv_a1_service_line") or "").strip(),
        title=(ss.get("sv_a2_title") or "").strip(),
        a3_tenure=ss.get("sv_a3_tenure"),
        a4_region=(ss.get("sv_a4_region") or "").strip(),
        b1_tools=tools,
        b2_freq=b2_freq,
        b3_built=ss.get("sv_b3_built"),
        b3a_desc=(ss.get("sv_b3a_desc") or "").strip(),
        b3b_tasks=ss.get("sv_b3b_tasks", []),
        b3c_shared=ss.get("sv_b3c_shared"),
        b4_aware=ss.get("sv_b4_aware"),
    )


def sync_step_cd1(draft):
    ss = st.session_state
    tools = draft.get("b1_tools", [])
    c1_eff = {}
    for t in tools:
        if t in survey.DETAILED_TOOLS:
            c1_eff[t] = ss.get(f"sv_c1_eff_{t}", 3)
    new_d1 = ss.get("sv_d1_tasks", [])
    if new_d1 != draft.get("d1_tasks"):
        draft["d1a_sample"] = survey.sample_d1a_tasks(new_d1)
    draft.update(
        c1_eff=c1_eff,
        c2_limitation=(ss.get("sv_c2_limitation") or "").strip(),
        c3_rating=ss.get("sv_c3_rating"),
        d1_tasks=new_d1,
    )


def sync_step_d1a(draft):
    ss = st.session_state
    d1a = {}
    for t in draft.get("d1a_sample", []):
        d1a[t] = {
            "could_ai": ss.get(f"sv_d1a_could_{t}", survey.COULD_AI_OPTIONS[0]),
            "meaningful": ss.get(f"sv_d1a_meaningful_{t}", 3),
        }
    draft.update(
        d1a=d1a,
        d2_wand=(ss.get("sv_d2_wand") or "").strip(),
        d3_not_want=(ss.get("sv_d3_not_want") or "").strip(),
    )


def sync_step_e(draft):
    ss = st.session_state
    draft.update(
        e1=ss.get("sv_e1"), e2=ss.get("sv_e2"), e3=ss.get("sv_e3"),
        e4=ss.get("sv_e4"),
        e5_trust=(ss.get("sv_e5_trust") or "").strip(),
    )


def validate_step_f(draft):
    ss = st.session_state
    sets = draft.get("f4_item_sets", [])
    for i in range(len(sets)):
        best = ss.get(f"sv_f4_best_{i}")
        worst = ss.get(f"sv_f4_worst_{i}")
        if best is not None and worst is not None and best == worst:
            return f"In priority set {i + 1}, most important and least important can't be the same item."
    return None


def sync_step_f(draft):
    ss = st.session_state
    sets = draft.get("f4_item_sets", [])
    f4_sets = []
    for i, items in enumerate(sets):
        f4_sets.append({
            "items": items,
            "best": ss.get(f"sv_f4_best_{i}"),
            "worst": ss.get(f"sv_f4_worst_{i}"),
        })
    draft.update(
        f1=ss.get("sv_f1"), f2=ss.get("sv_f2"),
        f3_fund=(ss.get("sv_f3_fund") or "").strip(),
        f4_sets=f4_sets,
    )


def sync_step_g(draft):
    ss = st.session_state
    draft.update(g1_other=(ss.get("sv_g1_other") or "").strip())


SYNC_FOR_STEP = {"ab": sync_step_ab, "cd1": sync_step_cd1, "d1a": sync_step_d1a, "e": sync_step_e, "f": sync_step_f, "g": sync_step_g}
VALIDATE_FOR_STEP = {"f": validate_step_f}


def open_text_hint(text: str):
    if survey.under_min_length(text):
        st.caption("Could you add a bit more detail? (not required)")


def render_step_ab(draft):
    st.markdown("#### Section A · Classification")
    st.caption("Used for segmentation only, not to identify individual respondents in reporting.")
    st.text_input("Which service line or division do you primarily work in?", value=draft.get("service_line", ""), key="sv_a1_service_line")
    st.text_input("What is your title?", value=draft.get("title", ""), key="sv_a2_title")
    tenure_default = draft.get("a3_tenure")
    st.selectbox(
        "How long have you worked at the company?", survey.TENURE_OPTIONS,
        index=survey.TENURE_OPTIONS.index(tenure_default) if tenure_default in survey.TENURE_OPTIONS else 0,
        key="sv_a3_tenure",
    )
    st.text_input("Which region or market do you primarily support?", value=draft.get("a4_region", ""), key="sv_a4_region")

    st.markdown("#### Section B · Current AI usage (behavioral)")
    st.caption("Behavioral first — what you actually use, not what you think you should say.")
    tools = st.multiselect(
        "B1. Which of the following AI tools do you currently use for work, even occasionally? Select all that apply.",
        survey.TOOL_OPTIONS, default=draft.get("b1_tools", []), key="sv_b1_tools",
    )
    detailed = [t for t in tools if t in survey.DETAILED_TOOLS]
    if detailed:
        st.caption("B2. For each tool selected above, how often do you use it?")
        b2 = draft.get("b2_freq") or {}
        for t in detailed:
            st.markdown(f"**{t}**")
            st.radio("Frequency", survey.FREQ_OPTIONS, index=survey.FREQ_OPTIONS.index(b2.get(t)) if b2.get(t) in survey.FREQ_OPTIONS else 0, key=f"sv_b2_freq_{t}", horizontal=True, label_visibility="collapsed")

    built_default = draft.get("b3_built", "No")
    st.radio(
        "B3. Have you personally built, configured, or requested a custom AI tool for your own or your team's use, beyond an off-the-shelf tool as provided?",
        ["Yes", "No"], index=["Yes", "No"].index(built_default) if built_default in ("Yes", "No") else 1,
        key="sv_b3_built", horizontal=True,
    )
    if st.session_state.get("sv_b3_built") == "Yes":
        st.text_area("B3a. Briefly describe what you built or requested.", value=draft.get("b3a_desc", ""), key="sv_b3a_desc", height=70)
        open_text_hint(st.session_state.get("sv_b3a_desc", ""))
        st.multiselect("B3b. What does it do? Select all that apply.", survey.TASK_BANK, default=draft.get("b3b_tasks", []), key="sv_b3b_tasks")
        shared_default = draft.get("b3c_shared")
        st.radio(
            "B3c. Does anyone else on your team currently use what you built?", survey.SHARED_OPTIONS,
            index=survey.SHARED_OPTIONS.index(shared_default) if shared_default in survey.SHARED_OPTIONS else 0,
            key="sv_b3c_shared",
        )
    aware_default = draft.get("b4_aware")
    st.radio(
        "B4. Are you aware of any AI tools/agents built by OTHER divisions that you don't have access to but think could be useful?",
        survey.AWARE_OPTIONS, index=survey.AWARE_OPTIONS.index(aware_default) if aware_default in survey.AWARE_OPTIONS else 0,
        key="sv_b4_aware", horizontal=True,
    )


def render_step_cd1(draft):
    tools = draft.get("b1_tools", [])
    detailed = [t for t in tools if t in survey.DETAILED_TOOLS]
    st.markdown("#### Section C · Effectiveness of current tools")
    if detailed:
        st.caption("C1. For each tool you currently use, how effective is it for your work?")
        c1 = draft.get("c1_eff") or {}
        for t in detailed:
            st.markdown(f"**{t}**")
            st.select_slider("Effectiveness (1 = not at all, 5 = extremely)", [1, 2, 3, 4, 5], value=c1.get(t, 3), key=f"sv_c1_eff_{t}", label_visibility="collapsed")
    else:
        st.caption("(No tools selected in Section B, so there's nothing to rate here.)")
    st.text_area("C2. What's the single biggest limitation of the AI tool(s) you currently use?", value=draft.get("c2_limitation", ""), key="sv_c2_limitation", height=70)
    open_text_hint(draft.get("c2_limitation", ""))
    st.select_slider(
        "C3. Overall, how would you rate the AI tools currently available to you for the kind of work you do? (1 = poor fit, 5 = excellent fit)",
        options=[1, 2, 3, 4, 5], value=draft.get("c3_rating", 3), key="sv_c3_rating",
    )

    st.markdown("#### Section D · Workflow and task-level assessment")
    st.multiselect(
        "D1. Which of these do you spend meaningful time on in a typical week? Select all that apply.",
        survey.TASK_BANK, default=draft.get("d1_tasks", []), key="sv_d1_tasks",
    )
    st.caption(f"The next screen asks a couple of quick questions about the tasks you pick here (capped at {survey.D1A_CAP} — if you pick more, we'll randomly sample {survey.D1A_CAP} of them to keep this from running long).")


def render_step_d1a(draft):
    sample = draft.get("d1a_sample", [])
    st.markdown("#### Section D, continued · Your selected tasks")
    if not sample:
        st.caption("You didn't select any tasks at D1, so there's nothing to rate here.")
    else:
        st.caption("D1a. For each task you selected, could AI take it on, and how meaningful is it to you personally?")
        d1a = draft.get("d1a") or {}
        for t in sample:
            st.markdown(f"**{t}**")
            d = d1a.get(t, {})
            st.radio("Could AI take this on?", survey.COULD_AI_OPTIONS, index=survey.COULD_AI_OPTIONS.index(d.get("could_ai")) if d.get("could_ai") in survey.COULD_AI_OPTIONS else 0, key=f"sv_d1a_could_{t}", horizontal=True)
            st.select_slider("How meaningful is this task to you personally? (1 not at all, 5 very)", [1, 2, 3, 4, 5], value=d.get("meaningful", 3), key=f"sv_d1a_meaningful_{t}")

    st.text_area(
        "D2. If you had a magic wand and could hand off any part of your workflow to AI tomorrow, no limitations, what would it be, and why that specifically?",
        value=draft.get("d2_wand", ""), key="sv_d2_wand", height=80,
    )
    open_text_hint(draft.get("d2_wand", ""))
    st.text_area(
        "D3. Is there a part of your workflow where you would NOT want AI involved, even if it were technically capable? What is it, and why?",
        value=draft.get("d3_not_want", ""), key="sv_d3_not_want", height=80,
    )
    open_text_hint(draft.get("d3_not_want", ""))


def render_step_e(draft):
    st.markdown("#### Section E · Trust and readiness")
    st.select_slider("E1. How confident are you that AI-assisted output is accurate enough to use with only light review? (1 = not at all, 5 = extremely)", options=[1, 2, 3, 4, 5], value=draft.get("e1", 3), key="sv_e1")
    st.select_slider("E2. How much do you trust AI-assisted research findings compared to fully human-led research? (1 = not nearly as much, 5 = just as much)", options=[1, 2, 3, 4, 5], value=draft.get("e2", 3), key="sv_e2")
    st.select_slider("E3. How easy or hard is it currently to integrate AI into your day-to-day workflow? (1 = very hard, 5 = very easy)", options=[1, 2, 3, 4, 5], value=draft.get("e3", 3), key="sv_e3")
    e4_default = draft.get("e4")
    st.radio("E4. Which best describes how you'd like AI to show up in your role going forward?", survey.E4_OPTIONS, index=survey.E4_OPTIONS.index(e4_default) if e4_default in survey.E4_OPTIONS else 1, key="sv_e4")
    st.text_area("E5. What would need to be true for you to trust AI more in your work?", value=draft.get("e5_trust", ""), key="sv_e5_trust", height=70)
    open_text_hint(draft.get("e5_trust", ""))


def render_step_f(draft):
    st.markdown("#### Section F · Organizational voice and priorities")
    st.select_slider("F1. Do you feel you have a say in how AI tools are selected and rolled out for your team? (1 = no say, 5 = full say)", options=[1, 2, 3, 4, 5], value=draft.get("f1", 3), key="sv_f1")
    st.select_slider("F2. Do you feel the AI tools currently provided are actually built for how your division works day to day? (1 = not at all, 5 = completely)", options=[1, 2, 3, 4, 5], value=draft.get("f2", 3), key="sv_f2")
    st.text_area("F3. What's one thing leadership could fund or build that would make the biggest difference to your day-to-day work?", value=draft.get("f3_fund", ""), key="sv_f3_fund", height=70)
    open_text_hint(draft.get("f3_fund", ""))

    if "f4_item_sets" not in draft:
        draft["f4_item_sets"] = survey.generate_maxdiff_sets()
    st.markdown("**F4. Investment priority**")
    st.caption(
        "If the company could only prioritize ONE of these for AI investment next year, which should it be? "
        "Shown as a short series of small sets — pick the most and least important in each, that forces a real "
        "trade-off instead of rating everything highly. (Simplified from true MaxDiff — see the note at the "
        "bottom of the results page for what that means.)"
    )
    prior_by_index = draft.get("f4_sets", [])
    for i, items in enumerate(draft["f4_item_sets"]):
        st.markdown(f"*Set {i + 1} of {len(draft['f4_item_sets'])}*")
        prior = prior_by_index[i] if i < len(prior_by_index) else {}
        best_default = prior.get("best")
        st.radio("Most important", items, index=items.index(best_default) if best_default in items else None, key=f"sv_f4_best_{i}")
        worst_pool = items + ["None of these"]
        worst_default = prior.get("worst")
        st.radio("Least important", worst_pool, index=worst_pool.index(worst_default) if worst_default in worst_pool else None, key=f"sv_f4_worst_{i}")
        st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)


def render_step_g(draft):
    st.markdown("#### Section G · Closing")
    st.text_area(
        "G1. Is there anything else about AI in your work that this survey didn't ask about, but you think leadership should know?",
        value=draft.get("g1_other", ""), key="sv_g1_other", height=90,
    )
    open_text_hint(draft.get("g1_other", ""))
    st.caption("Thank you for your time. Results will be shared in aggregate, and specific themes from open-ended responses will directly inform the AI strategy roadmap.")


RENDER_FOR_STEP = {"ab": render_step_ab, "cd1": render_step_cd1, "d1a": render_step_d1a, "e": render_step_e, "f": render_step_f, "g": render_step_g}
STEP_TITLES = {"ab": "About you & current usage", "cd1": "Effectiveness & workflow", "d1a": "Your selected tasks", "e": "Trust & readiness", "f": "Priorities", "g": "Closing"}


def main():
    theme.header("N = Everyone", "AI Perceptions & Workflow Assessment")

    if st.session_state.get("survey_app_submitted"):
        st.markdown(
            '<div class="prompt-box"><div class="label">Thank you</div>'
            "<p>Your response has been recorded. Results are reported in aggregate only, by service line and "
            "title, never by name.</p></div>",
            unsafe_allow_html=True,
        )
        st.caption("You can close this tab. Reload the page if you need to submit a separate response.")
        return

    st.markdown(
        '<div class="prompt-box"><div class="label">AI Perceptions & Workflow Assessment — Draft v0.1</div>'
        "<p>This asks about how you currently use AI tools in your work, what's working and what isn't, and "
        "where you'd want AI to show up differently. Results are reported by service line and title, not by "
        "name, and individual answers are never shown, only aggregates.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="prompt-sub">About 12 to 15 minutes, anonymous, no login required.</div>', unsafe_allow_html=True)

    step = st.session_state.get("survey_step")
    if step is None:
        if st.button("Start the survey", type="primary", key="sv_start_btn"):
            st.session_state["survey_draft"] = {"_start_ts": time.time()}
            st.session_state["survey_step"] = 0
            st.rerun()
        return

    draft = st.session_state.setdefault("survey_draft", {"_start_ts": time.time()})
    steps = survey.STEPS
    total = len(steps)
    current = steps[step]
    st.progress((step + 1) / total)
    st.caption(f"Step {step + 1} of {total} — {STEP_TITLES[current]}")

    RENDER_FOR_STEP[current](draft)

    if st.session_state.get("sv_step_error"):
        st.error(st.session_state["sv_step_error"])

    c1, c2 = st.columns(2)
    if step > 0:
        if c1.button("Back", key="sv_back_btn"):
            SYNC_FOR_STEP[current](draft)
            st.session_state.pop("sv_step_error", None)
            st.session_state["survey_step"] -= 1
            st.rerun()
    if step < total - 1:
        if c2.button("Next", key="sv_next_btn", type="primary"):
            validator = VALIDATE_FOR_STEP.get(current)
            error = validator(draft) if validator else None
            if error:
                st.session_state["sv_step_error"] = error
                st.rerun()
            else:
                SYNC_FOR_STEP[current](draft)
                st.session_state.pop("sv_step_error", None)
                st.session_state["survey_step"] += 1
                st.rerun()
    else:
        if c2.button("Submit", key="sv_submit_btn", type="primary"):
            validator = VALIDATE_FOR_STEP.get(current)
            error = validator(draft) if validator else None
            if error:
                st.session_state["sv_step_error"] = error
                st.rerun()
            else:
                SYNC_FOR_STEP[current](draft)
                start_ts = draft.pop("_start_ts", None)
                draft.pop("d1a_sample", None)
                draft.pop("f4_item_sets", None)
                straightlining = survey.is_straightlining(draft.get("d1a"))
                ttc = (time.time() - start_ts) if start_ts else None
                survey_db.insert_response(draft, ttc, straightlining)
                st.session_state.pop("survey_step", None)
                st.session_state.pop("survey_draft", None)
                st.session_state["survey_app_submitted"] = True
                st.rerun()


main()

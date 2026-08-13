"""Field Notes: AI Working Session — live, cross-level, cross-division board.

Session code is passed via ?session=CODE in the URL (baked into the QR
join link by the facilitator) and namespaces all stored data. Facilitator
mode is unlocked by a password (st.secrets["FACILITATOR_PASSWORD"]) and
persisted as a browser cookie — not a URL flag.

Identity model: no names are ever collected. Joining asks for Service
Line, Title, and Level; every post anywhere in the app is tagged
"{Service Line} · {Title}", never a name or device id. Level is used
only for segmentation/reporting, not for breakout groups — there are none.
"""
import html
import time
import uuid

import qrcode
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_cookies_controller import CookieController
from io import BytesIO

from lib import questionnaire, store, survey
from lib.board_map import QUAD_LABELS, build_map_figure, quad_of
from lib.claude_summary import build_board_data, stream_summary
from lib.survey import TASK_BANK

LEVELS = ["Analyst", "Manager", "Director", "Client Officer", "VP", "SVP", "President", "CEO"]

RESET_CONFIRM_WINDOW = 5  # seconds to confirm a reset before it auto-disarms

TAB_KEYS = ["join", "notes", "map", "ideas", "everyone", "closing"]
TAB_LABELS = {
    "join": "Join",
    "notes": "Good Research",
    "map": "Meaning & Delegation",
    "ideas": "Bottleneck Bank",
    "everyone": "N = Everyone",
    "closing": "Closing",
}

st.set_page_config(
    page_title="Field Notes: AI Working Session",
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed",
)

CSS = """
<style>
:root {
  --ink: #1c2b2d; --paper: #f6f2e9; --card: #fffdf7; --line: #d8cfb8;
  --mustard: #c98a2c; --moss: #4f6d5a; --rust: #a8532f; --pencil: #6b7270;
}
.stApp { background: var(--paper); }
html, body, [class*="css"] { font-family: 'Courier New', ui-monospace, monospace; }
.board-eyebrow { font-size: 11px; letter-spacing: .14em; text-transform: uppercase; color: var(--rust); font-weight: 700; }
.board-title { font-family: Georgia, serif; font-size: 24px; font-weight: 700; margin: 2px 0 6px; color: var(--ink); }
.board-status { font-size: 11px; color: var(--pencil); margin-bottom: 12px; }
.prompt-box { border: 2px solid var(--ink); background: var(--card); padding: 14px 16px; margin-bottom: 8px; border-radius: 6px; }
.prompt-box .label { font-size: 11px; text-transform: uppercase; letter-spacing: .1em; color: var(--moss); font-weight: 700; margin-bottom: 4px; }
.prompt-box p { margin: 0; font-family: Georgia, serif; font-size: 15px; line-height: 1.5; color: var(--ink); }
.prompt-sub { font-size: 12px; line-height: 1.5; color: var(--pencil); margin: 0 0 16px; }
.note { background: var(--card); border: 1.5px solid var(--ink); border-radius: 3px; padding: 12px; font-size: 13px; line-height: 1.4; color: var(--ink); box-shadow: 2px 2px 0 var(--line); margin-bottom: 2px; }
.note .tag { display: block; margin-top: 8px; font-size: 9.5px; text-transform: uppercase; letter-spacing: .04em; color: var(--rust); font-weight: 700; }
.note.q-tl { border-left: 4px solid #4f6d5a; }
.note.q-tr { border-left: 4px solid #c98a2c; }
.note.q-bl { border-left: 4px solid #6b7270; }
.note.q-br { border-left: 4px solid #a8532f; }
.roster-chip { display: inline-block; background: var(--card); border: 1px solid var(--ink); border-radius: 12px; padding: 4px 11px; font-size: 11px; margin: 2px 4px 2px 0; color: var(--ink); }
.roster-chip .lvl { color: var(--rust); font-weight: 700; }
.empty-note { color: var(--pencil); font-style: italic; font-size: 13px; }
.summary-output { border: 2px solid var(--ink); background: var(--card); border-radius: 6px; padding: 18px; font-family: Georgia, serif; font-size: 14.5px; line-height: 1.65; color: var(--ink); white-space: pre-wrap; }
div[data-testid="stButton"] button[kind="primary"] { background-color: var(--mustard); border-color: var(--ink); color: var(--ink); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(s: str) -> str:
    return html.escape(s or "")


def my_roster_entry(data, device_id):
    return next((p for p in data["roster"] if p["device_id"] == device_id), None)


def tag_for(entry) -> str:
    if not entry:
        return "Unspecified"
    parts = [entry.get("service_line") or "Unspecified"]
    if entry.get("title"):
        parts.append(entry["title"])
    return " · ".join(parts)


# ---------------------------------------------------------------- landing --
def render_facilitator_setup(cookies):
    st.markdown('<div class="board-eyebrow">Live Session Board</div>', unsafe_allow_html=True)
    st.markdown('<div class="board-title">Field Notes: AI Working Session</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="prompt-box"><div class="label">Facilitator setup</div>'
        "<p>This link has no active session. Start one below, then share the "
        "QR code or join link with the room — no one needs to see the code itself.</p></div>",
        unsafe_allow_html=True,
    )
    default_code = "SF-01"
    code_input = st.text_input("Session code", value=default_code, help="e.g. SF-01, NYC-02 — short and unique per session")

    configured_password = st.secrets.get("FACILITATOR_PASSWORD")
    pw_input = None
    if configured_password:
        pw_input = st.text_input("Facilitator password", type="password")
    else:
        st.caption("No FACILITATOR_PASSWORD is set in secrets — anyone with this screen can start a session. Set one in Streamlit secrets to require it.")

    if st.button("Start session", type="primary"):
        if configured_password and pw_input != configured_password:
            st.error("Incorrect facilitator password.")
        else:
            code = store.normalize_code(code_input)
            cookies.set("workshop_facilitator", "1", max_age=60 * 60 * 24)
            st.query_params["session"] = code
            st.rerun()
    st.caption("Already have a join link or QR code as a participant? Ask your facilitator — this screen is for starting a new session.")


# ------------------------------------------------------------- sidebar ui --
def render_facilitator_sidebar(session_code, data, cookies):
    st.sidebar.markdown("### 🎛️ Facilitator Controls")
    st.sidebar.caption(f"Session code: **{session_code}**")

    base_url = st.sidebar.text_input(
        "Deployed app URL",
        value=st.secrets.get("APP_BASE_URL", ""),
        placeholder="https://your-app-name.streamlit.app",
        help="Used only to build the join link/QR below — paste your app's live URL once it's deployed.",
    )
    join_link = f"{base_url.rstrip('/')}/?session={session_code}" if base_url else None
    if join_link:
        st.sidebar.text_input("Join link", value=join_link, disabled=True)
        qr_img = qrcode.make(join_link)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        st.sidebar.image(buf.getvalue(), caption="Scan to join", width=180)
    else:
        st.sidebar.info("Paste your deployed app URL above to generate the QR code and join link.")

    st.sidebar.divider()
    if st.sidebar.button("End session / start a new one"):
        st.query_params.clear()
        st.rerun()

    if st.sidebar.button("Log out of facilitator mode"):
        cookies.remove("workshop_facilitator")
        st.rerun()


def render_facilitator_login(cookies):
    with st.sidebar.expander("🔒 Facilitator login"):
        configured_password = st.secrets.get("FACILITATOR_PASSWORD")
        if configured_password:
            pw = st.text_input("Password", type="password", key="facilitator_login_pw")
            if st.button("Log in", key="facilitator_login_btn"):
                if pw == configured_password:
                    cookies.set("workshop_facilitator", "1", max_age=60 * 60 * 24)
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        else:
            st.caption("No FACILITATOR_PASSWORD is set in secrets — set one to require a password here.")
            if st.button("Enable facilitator controls on this device", key="facilitator_login_nopw"):
                cookies.set("workshop_facilitator", "1", max_age=60 * 60 * 24)
                st.rerun()


# --------------------------------------------------------- agree wall item --
def render_agree_item(session_code, device_id, data, collection, item, tag_label=None, quad=None):
    item_id = item["id"]
    label = tag_label if tag_label is not None else esc(item.get("tag") or "Unspecified")
    quad_class = f" q-{quad}" if quad else ""
    st.markdown(
        f'<div class="note{quad_class}">{esc(item["text"])}<span class="tag">{label}</span></div>',
        unsafe_allow_html=True,
    )
    counts = data["agree_counts"].get(collection, {})
    mine = data["my_agree"].get(collection, {}).get(device_id, {})
    agreed = item_id in mine
    count = counts.get(item_id, 0)
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("✓ Agreed" if agreed else "Agree", key=f"agree_{collection}_{item_id}"):
            def mutate(d, collection=collection, item_id=item_id, device_id=device_id):
                store.toggle_agree(d, collection, item_id, device_id)
            store.update(session_code, mutate)
            st.rerun()
    with c2:
        st.markdown(f'<div style="padding-top:8px; font-size:11px; color:var(--pencil);">{count} agree</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ join --
def render_join(session_code, device_id, data, is_facilitator):
    st.markdown(
        '<div class="prompt-box"><div class="label">Step 1</div>'
        "<p>No name is collected. Everything you post is shown under your service line and title, not your name.</p></div>",
        unsafe_allow_html=True,
    )

    my_entry = my_roster_entry(data, device_id)

    with st.form("join_form", clear_on_submit=True):
        service_line = st.text_input("Service Line / Division", value="", placeholder="e.g. Data Processing, AM, Stats, Client Service")
        title = st.text_input("Title", value="", placeholder="e.g. Senior Research Analyst")
        level = st.selectbox("Level (used only for segmentation/reporting)", LEVELS, index=0)
        submitted = st.form_submit_button("Join the room", type="primary")

    if submitted and service_line.strip():
        entry = {
            "device_id": device_id,
            "service_line": service_line.strip(),
            "title": title.strip(),
            "level": level,
        }

        def mutate(d):
            roster = d["roster"]
            idx = next((i for i, p in enumerate(roster) if p["device_id"] == device_id), None)
            if idx is not None:
                roster[idx] = entry
            else:
                roster.append(entry)

        data = store.update(session_code, mutate)
        my_entry = entry
        # auto-advance straight to the next screen — no separate continue step
        st.session_state.active_screen = "notes"
        st.rerun()

    if my_entry:
        st.success(f"You're in as {my_entry['service_line']} · {my_entry['title'] or 'no title'} · {my_entry['level']}.")

    st.markdown(
        '<div class="prompt-box" style="margin-top:20px;"><div class="label">Who\'s here</div>'
        "<p style=\"font-size:13px;\">Everyone who's joined so far, shown by service line, title, and level.</p></div>",
        unsafe_allow_html=True,
    )
    roster = data["roster"]
    if roster:
        chips = "".join(
            f'<span class="roster-chip">{esc(p["service_line"])} <span class="lvl">· {esc(p["title"] or "no title")} · {esc(p["level"])}</span></span>'
            for p in roster
        )
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-note">No one has joined yet.</div>', unsafe_allow_html=True)

    if is_facilitator:
        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        st.divider()
        st.markdown('<div class="board-eyebrow">Facilitator only</div>', unsafe_allow_html=True)
        now = time.time()
        armed_at = st.session_state.get("reset_armed_at")
        armed = armed_at is not None and (now - armed_at) < RESET_CONFIRM_WINDOW
        if armed:
            remaining = max(0, RESET_CONFIRM_WINDOW - (now - armed_at))
            if st.button(f"⚠️ Click again to confirm reset ({remaining:.0f}s)", key="reset_confirm_btn", type="primary"):
                store.reset(session_code)
                st.session_state.pop("reset_armed_at", None)
                st.rerun()
            st.caption("This clears all posts, agree counts, and the roster for this session only. Other sessions are untouched.")
        else:
            if armed_at is not None:
                st.session_state.pop("reset_armed_at", None)
            if st.button("Reset board", key="reset_arm_btn"):
                st.session_state["reset_armed_at"] = now
                st.rerun()


# ----------------------------------------------------------------- notes --
def render_notes(session_code, device_id, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Prompt</div>'
        "<p>Think of one specific project, not research in general. What did you personally catch, decide, "
        "or push back on, something the client never saw, that would have gone wrong without you? "
        "Describe that one moment.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="prompt-sub">Be specific: what almost happened, and what did you do instead? '
        'Avoid general statements like "attention to detail matters."</div>',
        unsafe_allow_html=True,
    )
    with st.form("note_form", clear_on_submit=True):
        text = st.text_area("Your note", label_visibility="collapsed", placeholder="Describe the specific moment…", height=90)
        submitted = st.form_submit_button("Post", type="primary")
    if submitted and text.strip():
        entry = my_roster_entry(data, device_id)

        def mutate(d, t=text.strip(), tag=tag_for(entry)):
            d["notes"].append({"id": "n" + uuid.uuid4().hex[:8], "text": t, "tag": tag})
        data = store.update(session_code, mutate)

    notes = data["notes"]
    if notes:
        for n in reversed(notes):
            render_agree_item(session_code, device_id, data, "notes", n)
    else:
        st.markdown('<div class="empty-note">No notes yet, be the first to post.</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------- map --
def render_map(session_code, device_id, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Prompt</div>'
        "<p>Pick a task from your work. Is it meaningful to you, does it give you accomplishment, satisfaction, "
        "or a sense of connection to your work? Separately: could you delegate it entirely, if you stopped doing "
        "it yourself, would anything important change? Place it where both are true.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="prompt-sub"><strong>Meaningful</strong> = gives you a sense of accomplishment, satisfaction, '
        "or connection to your motivation for the work. <strong>Delegable</strong> = if you stopped doing this "
        "yourself, nothing important would change, it doesn't require your specific judgment or autonomy.</div>",
        unsafe_allow_html=True,
    )

    # The naming field below is keyed with a generation counter that bumps
    # on every event that should force its displayed value (a task-bank
    # click, or a fresh grid click). A stable key relying on session_state
    # to pre-seed an *existing* widget races Streamlit's plotly on_select
    # rerun — the widget can end up created before its seeded value has
    # been round-tripped, silently reverting to empty. A brand-new key has
    # no prior frontend state to race against, so its `value=` always wins.
    if "map_field_gen" not in st.session_state:
        st.session_state["map_field_gen"] = 0
    if "map_selected_task" not in st.session_state:
        st.session_state["map_selected_task"] = ""

    st.caption("Task bank — tap one to prefill the note field, or free-type your own after clicking the grid.")
    cols = st.columns(3)
    for i, task in enumerate(TASK_BANK):
        with cols[i % 3]:
            if st.button(task, key=f"taskbank_{i}", use_container_width=True):
                st.session_state["map_selected_task"] = task
                st.session_state["map_field_gen"] += 1
                st.rerun()

    notes = data.get("map", [])
    if not notes:
        st.caption("Click anywhere on the grid to place the first task.")

    seq = st.session_state.get("map_chart_seq", 0)
    fig = build_map_figure(notes)
    event = st.plotly_chart(fig, on_select="rerun", key=f"map_chart_{seq}", use_container_width=True)

    points = event.selection.points if event else []
    if points and points[0].get("curve_number") == 0:
        st.session_state["pending_map_xy"] = (points[0]["x"], points[0]["y"])
        st.session_state["map_chart_seq"] = seq + 1
        st.session_state["map_field_gen"] += 1

    pending = st.session_state.get("pending_map_xy")
    if pending:
        x, y = pending
        q = quad_of(x, y)
        st.caption(f"Naming the task at this spot — {QUAD_LABELS[q]}")
        gen = st.session_state["map_field_gen"]
        text = st.text_input(
            "Task", key=f"map_task_text_{gen}", value=st.session_state.get("map_selected_task", ""),
            label_visibility="collapsed",
            placeholder="e.g. Spotting a contradiction between two data sources",
        )
        c1, c2 = st.columns(2)
        save = c1.button("Add note", key="map_add_btn", type="primary")
        cancel = c2.button("Cancel", key="map_cancel_btn")
        if save and text.strip():
            entry = my_roster_entry(data, device_id)

            def mutate(d, x=x, y=y, t=text.strip(), tag=tag_for(entry)):
                d["map"].append({"id": "m" + uuid.uuid4().hex[:8], "text": t, "x": x, "y": y, "tag": tag})
            store.update(session_code, mutate)
            st.session_state.pop("pending_map_xy", None)
            st.session_state["map_selected_task"] = ""
            st.rerun()
        elif cancel:
            st.session_state.pop("pending_map_xy", None)
            st.rerun()

    if notes:
        st.markdown("#### Placed so far")
        for n in reversed(notes):
            render_agree_item(session_code, device_id, data, "map", n, quad=quad_of(n["x"], n["y"]))


# ----------------------------------------------------------------- ideas --
def render_ideas(session_code, device_id, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Prompt</div>'
        "<p>What's a bottleneck in your own role, something that slows you down or gets in your way, that AI "
        "could realistically help with? Describe the bottleneck itself, not a solution. Add as many as apply "
        "to your role.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="prompt-sub">Agreeing with someone else\'s bottleneck shows it\'s shared, it\'s not a ranking '
        "of what matters most. Different service lines have different bottlenecks, that's expected.</div>",
        unsafe_allow_html=True,
    )

    with st.form("idea_form", clear_on_submit=True):
        idea_text = st.text_area("Add a bottleneck", label_visibility="collapsed", placeholder="What slows you down that AI could realistically help with?", height=80)
        add_idea = st.form_submit_button("Add bottleneck", type="primary")
    if add_idea and idea_text.strip():
        entry = my_roster_entry(data, device_id)

        def mutate(d, t=idea_text.strip(), tag=tag_for(entry)):
            d.setdefault("ideas", [])
            d["ideas"].append({"id": "u" + uuid.uuid4().hex[:8], "text": t, "tag": tag})
        data = store.update(session_code, mutate)

    ideas = data.get("ideas") or []
    if ideas:
        for idea in reversed(ideas):
            label = f"Shared by {esc(idea['tag'])}" if idea.get("tag") else "Unspecified"
            render_agree_item(session_code, device_id, data, "ideas", idea, tag_label=label)
    else:
        st.markdown('<div class="empty-note">No bottlenecks posted yet, be the first.</div>', unsafe_allow_html=True)


# --------------------------------------------------------------- closing --
def render_closing(session_code, device_id, data, is_facilitator):
    st.markdown(
        '<div class="prompt-box"><div class="label">Closing</div>'
        "<p>This pulls everything the room posted into one synthesis for leadership, grounded in what was "
        "actually said. Best run live, projected on a shared screen, as the closing moment of the session.</p></div>",
        unsafe_allow_html=True,
    )

    st.markdown("#### N = Everyone snapshot")
    render_survey_results(data.get("survey_responses", {}))
    st.divider()

    existing = data.get("summary")

    if is_facilitator:
        if st.session_state.get("summary_error"):
            st.error(st.session_state["summary_error"])

        if st.button("Generate summary from live board", type="primary"):
            st.session_state.pop("summary_error", None)
            board_data = build_board_data(data)
            placeholder = st.empty()
            accumulated = ""
            try:
                for chunk in stream_summary(board_data):
                    accumulated += chunk
                    placeholder.markdown(f'<div class="summary-output">{esc(accumulated)}▌</div>', unsafe_allow_html=True)
                placeholder.markdown(f'<div class="summary-output">{esc(accumulated)}</div>', unsafe_allow_html=True)

                def mutate(d):
                    d["summary"] = {"text": accumulated, "generated_at": time.time()}

                store.update(session_code, mutate)
            except Exception as e:
                st.session_state["summary_error"] = f"Could not generate summary: {e}"
                st.rerun()
            return

    if existing and existing.get("text"):
        st.markdown(f'<div class="summary-output">{esc(existing["text"])}</div>', unsafe_allow_html=True)
    elif not is_facilitator:
        st.markdown('<div class="empty-note">Waiting for your facilitator to generate the closing summary.</div>', unsafe_allow_html=True)


# -------------------------------------------------------------- everyone --
# Streamlit drops a widget's session_state entry once that widget stops
# being drawn on a rerun (e.g. moving from wizard step "ab" to "cd" un-
# instantiates step "ab"'s widgets). So per-step answers can't just live
# in the widget keys — each step's values must be copied into a plain,
# non-widget "survey_draft" dict in session_state *before* the step
# changes, and widgets must read their defaults from that draft (not from
# whatever was last stored), or Back/Next would silently drop answers.
def sync_step_ab(draft):
    ss = st.session_state
    tools = ss.get("sv_b1_tools", [])
    detail = {}
    for t in tools:
        if t in survey.DETAILED_TOOLS:
            detail[t] = {
                "freq": ss.get(f"sv_b1_freq_{t}", survey.FREQ_OPTIONS[0]),
                "effectiveness": ss.get(f"sv_b1_eff_{t}", 3),
            }
    draft.update(
        a3_tenure=ss.get("sv_a3_tenure"),
        a4_region=(ss.get("sv_a4_region") or "").strip(),
        b1_tools=tools,
        b1_detail=detail,
        b3_built=ss.get("sv_b3_built"),
        b3a_desc=(ss.get("sv_b3a_desc") or "").strip(),
        b4_aware=ss.get("sv_b4_aware"),
    )


def sync_step_cd(draft):
    ss = st.session_state
    draft.update(
        c2_limitation=(ss.get("sv_c2_limitation") or "").strip(),
        c3_rating=ss.get("sv_c3_rating"),
        d1_tasks=ss.get("sv_d1_tasks", []),
        d2_wand=(ss.get("sv_d2_wand") or "").strip(),
        d3_not_want=(ss.get("sv_d3_not_want") or "").strip(),
    )


def sync_step_ef(draft):
    ss = st.session_state
    draft.update(
        e1=ss.get("sv_e1"), e2=ss.get("sv_e2"), e3=ss.get("sv_e3"),
        e4=ss.get("sv_e4"),
        e5_trust=(ss.get("sv_e5_trust") or "").strip(),
        f1=ss.get("sv_f1"), f2=ss.get("sv_f2"),
        f3_fund=(ss.get("sv_f3_fund") or "").strip(),
        f4_top=ss.get("sv_f4_top"), f4_low=ss.get("sv_f4_low"),
    )


def sync_step_g(draft):
    ss = st.session_state
    draft.update(g1_other=(ss.get("sv_g1_other") or "").strip())


SYNC_FOR_STEP = {"ab": sync_step_ab, "cd": sync_step_cd, "ef": sync_step_ef, "g": sync_step_g}


def render_step_ab(draft):
    st.markdown("#### Section A · About you")
    entry = draft.get("_entry")
    if entry:
        st.caption(f"From Join: {entry['service_line']} · {entry['title'] or 'no title'} · {entry['level']}")
    else:
        st.caption("Join the room first (Join tab) so your service line and title can be attached to this response.")
    tenure_default = draft.get("a3_tenure")
    st.selectbox(
        "How long have you worked at the company?", survey.TENURE_OPTIONS,
        index=survey.TENURE_OPTIONS.index(tenure_default) if tenure_default in survey.TENURE_OPTIONS else 0,
        key="sv_a3_tenure",
    )
    st.text_input("Which region or market do you primarily support?", value=draft.get("a4_region", ""), key="sv_a4_region")

    st.markdown("#### Section B · Current AI usage")
    st.caption("Behavioral first — what you actually use, not what you think you should say.")
    tools = st.multiselect(
        "Which of these do you currently use for work, even occasionally?", survey.TOOL_OPTIONS,
        default=draft.get("b1_tools", []), key="sv_b1_tools",
    )
    detailed = [t for t in tools if t in survey.DETAILED_TOOLS]
    if detailed:
        st.caption("For each, roughly how often, and how effective is it for your work?")
        existing_detail = draft.get("b1_detail") or {}
        for t in detailed:
            st.markdown(f"**{t}**")
            c1, c2 = st.columns(2)
            d = existing_detail.get(t, {})
            with c1:
                st.select_slider("Frequency", survey.FREQ_OPTIONS, value=d.get("freq", survey.FREQ_OPTIONS[0]), key=f"sv_b1_freq_{t}")
            with c2:
                st.select_slider("Effectiveness (1–5)", [1, 2, 3, 4, 5], value=d.get("effectiveness", 3), key=f"sv_b1_eff_{t}")

    built_default = draft.get("b3_built", "No")
    st.radio(
        "Have you personally built, configured, or requested a custom AI tool for your own or your team's use?",
        ["Yes", "No"], index=["Yes", "No"].index(built_default) if built_default in ("Yes", "No") else 1,
        key="sv_b3_built", horizontal=True,
    )
    if st.session_state.get("sv_b3_built") == "Yes":
        st.text_area("Briefly describe what you built or requested.", value=draft.get("b3a_desc", ""), key="sv_b3a_desc", height=70)
    aware_default = draft.get("b4_aware")
    st.radio(
        "Are you aware of AI tools/agents built by OTHER divisions that you don't have access to but think could be useful?",
        survey.AWARE_OPTIONS, index=survey.AWARE_OPTIONS.index(aware_default) if aware_default in survey.AWARE_OPTIONS else 0,
        key="sv_b4_aware", horizontal=True,
    )


def render_step_cd(draft):
    st.markdown("#### Section C · Effectiveness of current tools")
    st.text_area("What's the single biggest limitation of the AI tool(s) you currently use?", value=draft.get("c2_limitation", ""), key="sv_c2_limitation", height=70)
    st.select_slider(
        "Overall, how well do current AI tools fit the kind of work you do? (1 = poor fit, 5 = excellent fit)",
        options=[1, 2, 3, 4, 5], value=draft.get("c3_rating", 3), key="sv_c3_rating",
    )

    st.markdown("#### Section D · Workflow")
    st.caption("Task-level meaning and delegability is covered by the Meaning & Delegation Map tab — this is just where your time actually goes.")
    st.multiselect(
        "Which of these do you spend meaningful time on in a typical week?", TASK_BANK,
        default=draft.get("d1_tasks", []), key="sv_d1_tasks",
    )
    st.text_area(
        "If you had a magic wand and could hand off any part of your workflow to AI tomorrow, no limitations, what would it be and why?",
        value=draft.get("d2_wand", ""), key="sv_d2_wand", height=70,
    )
    st.text_area(
        "Is there a part of your workflow where you would NOT want AI involved, even if it were capable? What, and why?",
        value=draft.get("d3_not_want", ""), key="sv_d3_not_want", height=70,
    )


def render_step_ef(draft):
    st.markdown("#### Section E · Trust and readiness")
    st.select_slider(
        "How confident are you that AI-assisted output is accurate enough to use with only light review? (1 = not at all, 5 = extremely)",
        options=[1, 2, 3, 4, 5], value=draft.get("e1", 3), key="sv_e1",
    )
    st.select_slider(
        "How much do you trust AI-assisted research findings compared to fully human-led research? (1 = not nearly as much, 5 = just as much)",
        options=[1, 2, 3, 4, 5], value=draft.get("e2", 3), key="sv_e2",
    )
    st.select_slider(
        "How easy or hard is it currently to integrate AI into your day-to-day workflow? (1 = very hard, 5 = very easy)",
        options=[1, 2, 3, 4, 5], value=draft.get("e3", 3), key="sv_e3",
    )
    e4_default = draft.get("e4")
    st.radio(
        "Which best describes how you'd like AI to show up in your role going forward?", survey.E4_OPTIONS,
        index=survey.E4_OPTIONS.index(e4_default) if e4_default in survey.E4_OPTIONS else 1, key="sv_e4",
    )
    st.text_area("What would need to be true for you to trust AI more in your work?", value=draft.get("e5_trust", ""), key="sv_e5_trust", height=70)

    st.markdown("#### Section F · Organizational voice and priorities")
    st.select_slider(
        "Do you feel you have a say in how AI tools are selected and rolled out for your team? (1 = no say, 5 = full say)",
        options=[1, 2, 3, 4, 5], value=draft.get("f1", 3), key="sv_f1",
    )
    st.select_slider(
        "Do you feel the AI tools currently provided are actually built for how your division works day to day? (1 = not at all, 5 = completely)",
        options=[1, 2, 3, 4, 5], value=draft.get("f2", 3), key="sv_f2",
    )
    st.text_area(
        "What's one thing leadership could fund or build that would make the biggest difference to your day-to-day work?",
        value=draft.get("f3_fund", ""), key="sv_f3_fund", height=70,
    )
    st.caption("If the company could only prioritize ONE of these for AI investment next year — pick your top choice, and your lowest. (Simplified from a true MaxDiff exercise for live use.)")
    top_default = draft.get("f4_top")
    st.radio("Top priority", survey.PRIORITY_OPTIONS, index=survey.PRIORITY_OPTIONS.index(top_default) if top_default in survey.PRIORITY_OPTIONS else 0, key="sv_f4_top")
    low_default = draft.get("f4_low")
    st.radio("Lowest priority", survey.PRIORITY_OPTIONS, index=survey.PRIORITY_OPTIONS.index(low_default) if low_default in survey.PRIORITY_OPTIONS else 0, key="sv_f4_low")


def render_step_g(draft):
    st.markdown("#### Section G · Closing")
    st.text_area(
        "Is there anything else about AI in your work that this survey didn't ask about, but you think leadership should know?",
        value=draft.get("g1_other", ""), key="sv_g1_other", height=90,
    )
    st.caption(questionnaire.CLOSING_NOTE)


def render_survey_results(responses):
    agg = survey.aggregate(responses)
    n = agg["n"]
    st.markdown(f"#### Live results — {n} response{'s' if n != 1 else ''}")
    if n == 0:
        st.markdown('<div class="empty-note">No survey responses yet.</div>', unsafe_allow_html=True)
        return

    st.markdown("**Attitudes (1–5 average)**")
    for key, label in survey.SCALE_QUESTIONS:
        avg = agg["scale_avgs"].get(key)
        if avg is None:
            continue
        st.caption(f"{label} — {avg:.1f}/5")
        st.progress(avg / 5)

    st.markdown("**Tool usage**")
    for t in survey.TOOL_OPTIONS:
        if t == "None of the above":
            continue
        c = agg["tool_counts"].get(t, 0)
        pct = c / n
        st.caption(f"{t} — {c} ({pct:.0%})")
        st.progress(pct)

    st.markdown("**Investment priority — top vs. lowest picks**")
    for opt in survey.PRIORITY_OPTIONS:
        top_c = agg["priority_top"].get(opt, 0)
        low_c = agg["priority_low"].get(opt, 0)
        st.caption(f"{opt} — top: {top_c}, lowest: {low_c}")


def render_everyone(session_code, device_id, data):
    entry = my_roster_entry(data, device_id)
    existing = data.get("survey_responses", {}).get(device_id) or {}
    step = st.session_state.get("survey_step")

    st.markdown(
        f'<div class="prompt-box"><div class="label">{questionnaire.SUBTITLE}</div>'
        f"<p>{questionnaire.RESPONDENT_INTRO}</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="prompt-sub">{questionnaire.META} Individual answers are never shown, only aggregates.</div>', unsafe_allow_html=True)

    if step is None:
        if existing:
            st.success("You've already submitted a response for this session.")
            if st.button("Edit my response", key="sv_edit_btn"):
                st.session_state["survey_draft"] = dict(existing)
                st.session_state["survey_step"] = 0
                st.rerun()
        else:
            if st.button("Start the survey", type="primary", key="sv_start_btn"):
                st.session_state["survey_draft"] = {}
                st.session_state["survey_step"] = 0
                st.rerun()
    else:
        draft = st.session_state.setdefault("survey_draft", dict(existing))
        draft["_entry"] = entry

        steps = survey.STEPS
        total = len(steps)
        st.progress(step / total)
        st.caption(f"Step {step + 1} of {total}")
        current = steps[step]
        if current == "ab":
            render_step_ab(draft)
        elif current == "cd":
            render_step_cd(draft)
        elif current == "ef":
            render_step_ef(draft)
        elif current == "g":
            render_step_g(draft)

        c1, c2 = st.columns(2)
        if step > 0:
            if c1.button("Back", key="sv_back_btn"):
                SYNC_FOR_STEP[current](draft)
                st.session_state["survey_step"] -= 1
                st.rerun()
        if step < total - 1:
            if c2.button("Next", key="sv_next_btn", type="primary"):
                SYNC_FOR_STEP[current](draft)
                st.session_state["survey_step"] += 1
                st.rerun()
        else:
            if c2.button("Submit", key="sv_submit_btn", type="primary"):
                SYNC_FOR_STEP[current](draft)
                draft.pop("_entry", None)
                response = dict(draft)
                response.update(
                    service_line=entry.get("service_line") if entry else None,
                    title=entry.get("title") if entry else None,
                    level=entry.get("level") if entry else None,
                    submitted_at=time.time(),
                )

                def mutate(d, device_id=device_id, response=response):
                    d.setdefault("survey_responses", {})[device_id] = response

                data = store.update(session_code, mutate)
                st.session_state.pop("survey_step", None)
                st.session_state.pop("survey_draft", None)
                st.rerun()

    st.divider()
    render_survey_results(data.get("survey_responses", {}))


# ------------------------------------------------------------------- nav --
def render_nav():
    if "active_screen" not in st.session_state:
        st.session_state.active_screen = "join"

    row1 = st.columns(3)
    row2 = st.columns(3)
    for col, key in zip(row1 + row2, TAB_KEYS):
        active = st.session_state.active_screen == key
        if col.button(TAB_LABELS[key], key=f"nav_{key}", type="primary" if active else "secondary", use_container_width=True):
            st.session_state.active_screen = key
            st.rerun()


# ------------------------------------------------------------------ main --
def main():
    # The cookie component's first read on a fresh browser session is
    # asynchronous: on the very first script run it can't yet know whether
    # a cookie exists (the browser round-trip hasn't landed). If we treated
    # that "not yet known" state as "no cookie" and wrote a fresh value
    # right away, a real reload would race its own restore and stomp the
    # value it was trying to recover. So: only ever persist a *new* value
    # once we've confirmed, on a later rerun, that the round-trip already
    # completed and there's still genuinely nothing there. Must be checked
    # before constructing CookieController() this run.
    had_prior_cookie_sync = "cookies" in st.session_state
    cookies = CookieController()

    qp = st.query_params
    session_param = qp.get("session", "")

    if not session_param:
        render_facilitator_setup(cookies)
        return

    session_code = store.normalize_code(session_param)

    # Device identity lives in a browser cookie, not the URL — a cookie
    # persists across refreshes but is scoped to that one browser, so it
    # can never ride along when a join link gets copied or forwarded
    # after someone has already joined.
    cookie_device_id = cookies.get("workshop_device_id")
    if cookie_device_id:
        device_id = cookie_device_id
        st.session_state.device_id = cookie_device_id
    else:
        if "device_id" not in st.session_state:
            st.session_state.device_id = uuid.uuid4().hex[:9]
        device_id = st.session_state.device_id
        if had_prior_cookie_sync:
            cookies.set("workshop_device_id", device_id, max_age=60 * 60 * 24 * 30)

    # Facilitator status is also a cookie (set via password login), never
    # a URL flag.
    is_facilitator = cookies.get("workshop_facilitator") == "1"

    st_autorefresh(interval=4000, key="board_autorefresh")

    st.markdown('<div class="board-eyebrow">Live Session Board</div>', unsafe_allow_html=True)
    st.markdown('<div class="board-title">Field Notes: AI Working Session</div>', unsafe_allow_html=True)

    data = store.load(session_code)

    last_updated = data.get("last_updated")
    if last_updated:
        secs = max(0, int(time.time() - last_updated))
        status = "updated just now" if secs < 5 else f"updated {secs}s ago"
    else:
        status = "no activity yet"
    st.markdown(f'<div class="board-status">{status} · syncs every few seconds</div>', unsafe_allow_html=True)

    if is_facilitator:
        render_facilitator_sidebar(session_code, data, cookies)
        data = store.load(session_code)
    else:
        render_facilitator_login(cookies)

    render_nav()
    screen = st.session_state.active_screen

    if screen == "join":
        render_join(session_code, device_id, data, is_facilitator)
    elif screen == "notes":
        render_notes(session_code, device_id, data)
    elif screen == "map":
        render_map(session_code, device_id, data)
    elif screen == "ideas":
        render_ideas(session_code, device_id, data)
    elif screen == "everyone":
        render_everyone(session_code, device_id, data)
    elif screen == "closing":
        render_closing(session_code, device_id, data, is_facilitator)


if __name__ == "__main__":
    main()

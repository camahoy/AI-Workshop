"""Field Notes: AI Working Session — live, cross-level, cross-division board.

Session code is passed via ?session=CODE in the URL (baked into the QR
join link by the facilitator) and namespaces all stored data. Each session
carries its own settings (lib/sessions.py): which tabs show, what Join
asks, whether posts carry an identity tag, and whether the summary is on.
SF-01 uses the original workshop setup; PA-01 uses the team-pulse setup.

Facilitator controls (Export, Reset board, Summary, session settings)
appear only after the passphrase in st.secrets["FACILITATOR_PASSWORD"] is
entered on the setup screen (the app's base URL, no ?session=). Participant
links never show any facilitator login or control.

Data is stored durably via lib/db.py (Postgres when DATABASE_URL is set).
"""
import time
import uuid
from io import BytesIO

import qrcode
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_cookies_controller import CookieController

from lib import auth, db, export, sessions, store, theme
from lib.board_map import QUAD_LABELS, build_map_figure, quad_of
from lib.claude_summary import PULSE_SYSTEM_PROMPT, build_board_data, build_pulse_data, stream_summary
from lib.sessions import AI_BARRIERS, AI_OUTCOMES, AI_TIME_IMPACT, AI_TOOLS
from lib.survey import TASK_BANK

LEVELS = ["Analyst", "Manager", "Director", "Client Officer", "VP", "SVP", "President", "CEO"]

RESET_CONFIRM_WINDOW = 5  # seconds to confirm a reset before it auto-disarms
APP_TITLE = "Field Notes: AI Working Session"


def safe_cookie_get(cookies, key):
    """streamlit_cookies_controller's .get() can raise
    `TypeError: argument of type 'NoneType' is not a container or iterable`
    when the underlying cookie dict hasn't round-tripped from the browser
    yet (seen intermittently in production logs) — treat that the same as
    "not available on this rerun" rather than crashing the whole page."""
    try:
        return cookies.get(key)
    except TypeError:
        return None


st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📝",
    layout="centered",
    initial_sidebar_state="collapsed",
)

theme.inject()
esc = theme.esc


def my_roster_entry(data, device_id):
    return next((p for p in data["roster"] if p["device_id"] == device_id), None)


def tag_for(entry) -> str:
    if not entry:
        return "Unspecified"
    parts = [entry.get("service_line") or "Unspecified"]
    if entry.get("title"):
        parts.append(entry["title"])
    return " · ".join(parts)


def new_post(data, device_id, cfg, text: str, prefix: str) -> dict:
    """A post with its private Level and timestamp (export only). Identity
    tag only in non-anonymous sessions."""
    entry = my_roster_entry(data, device_id)
    post = {
        "id": prefix + uuid.uuid4().hex[:8],
        "text": text,
        "level": (entry or {}).get("level", ""),
        "created": time.time(),
    }
    if not cfg["anonymous"]:
        post["tag"] = tag_for(entry)
    return post


def next_tab(cfg, after: str) -> str:
    tabs = cfg["tabs"]
    i = tabs.index(after) if after in tabs else -1
    return tabs[i + 1] if i + 1 < len(tabs) else tabs[0]


# ---------------------------------------------------------------- landing --
def render_facilitator_setup(cookies, is_facilitator):
    st.markdown('<div class="board-eyebrow">Live Session Board</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="board-title">{esc(APP_TITLE)}</div>', unsafe_allow_html=True)

    if not auth.passphrase():
        st.markdown(
            '<div class="prompt-box"><div class="label">Facilitator access is off</div>'
            "<p>Set FACILITATOR_PASSWORD in Streamlit secrets to start or manage sessions. "
            "Until then, no one can open facilitator controls.</p></div>",
            unsafe_allow_html=True,
        )
        return

    st.markdown(
        '<div class="prompt-box"><div class="label">Facilitator setup</div>'
        "<p>Start a new session or reopen an existing one, then share the QR code or join link with the "
        "room — no one needs to see the code itself.</p></div>",
        unsafe_allow_html=True,
    )
    code = store.normalize_code(
        st.text_input("Session code", value="SF-01", help="e.g. SF-01, PA-01 — short and unique per session")
    )

    stored = db.get_doc(code)
    stored_cfg = (stored or {}).get("config")
    chosen = None
    if stored_cfg:
        label = sessions.TEMPLATES[stored_cfg.get("template", "workshop")]["label"]
        st.caption(f"{code} already exists ({label}). It reopens with its own settings and data.")
    elif code in sessions.PRESETS:
        label = sessions.TEMPLATES[sessions.PRESETS[code]]["label"]
        st.caption(f"{code} always uses: {label}.")
    else:
        chosen = st.selectbox(
            "Session type",
            list(sessions.TEMPLATES),
            format_func=lambda k: sessions.TEMPLATES[k]["label"],
            help="Sets the tabs, Join form, and anonymity for this session. You can change tabs later.",
        )

    pw_input = None
    if not is_facilitator:
        pw_input = st.text_input("Facilitator passphrase", type="password")

    if st.button("Start or reopen session", type="primary"):
        if not is_facilitator and not auth.check(pw_input or ""):
            st.error("Incorrect facilitator passphrase.")
            return
        if not is_facilitator:
            auth.login(cookies)
        if not stored_cfg:
            store.set_config(code, sessions.config_from_template(sessions.template_for_code(code, chosen)))
        st.query_params["session"] = code
        st.rerun()
    st.caption("Joining as a participant? Use the QR code or join link from your facilitator.")


# ------------------------------------------------------------- sidebar ui --
def render_facilitator_sidebar(session_code, data, cfg, cookies):
    sb = st.sidebar
    sb.markdown("### 🎛️ Facilitator Controls")
    sb.caption(f"Session code: **{session_code}** · {sessions.TEMPLATES[cfg['template']]['label']}")

    if db.is_durable():
        sb.caption("✓ Saved to the durable database.")
    else:
        sb.error(
            "Storage is NOT durable: posts are on this server's local disk and will be lost when the app "
            "restarts. Set DATABASE_URL in Streamlit secrets (see README) and export often."
        )

    # Export — every board in this session, any time.
    files = export.board_files(session_code, data, cfg)
    sb.download_button(
        "⬇️ Export all boards (CSV)",
        data=export.zip_files(files),
        file_name=f"{session_code}_export_{export.stamp()}.zip",
        mime="application/zip",
        type="primary",
        use_container_width=True,
        key="export_all",
    )
    with sb.expander("Download one board at a time"):
        for name, content in files.items():
            st.download_button(name, data=content, file_name=name, mime="text/csv", key=f"export_{name}", use_container_width=True)

    sb.divider()
    base_url = sb.text_input(
        "Deployed app URL",
        value=st.secrets.get("APP_BASE_URL", ""),
        placeholder="https://your-app-name.streamlit.app",
        help="Used only to build the join link/QR below — paste your app's live URL once it's deployed.",
    )
    join_link = f"{base_url.rstrip('/')}/?session={session_code}" if base_url else None
    if join_link:
        sb.text_input("Join link", value=join_link, disabled=True)
        qr_img = qrcode.make(join_link)
        buf = BytesIO()
        qr_img.save(buf, format="PNG")
        sb.image(buf.getvalue(), caption="Scan to join", width=180)
    else:
        sb.info("Paste your deployed app URL above to generate the QR code and join link.")

    sb.divider()
    with sb.expander("⚙️ Session settings"):
        st.caption(f"Saved for {session_code} only.")
        tabs = st.multiselect(
            "Tabs shown",
            sessions.ALL_TABS,
            default=cfg["tabs"],
            format_func=lambda k: sessions.tab_label(k, cfg),
            key=f"cfg_tabs_{session_code}",
        )
        summary_on = st.toggle("Summary enabled (facilitator only)", value=cfg["summary_enabled"], key=f"cfg_summary_{session_code}")
        if st.button("Save settings", key="cfg_save"):
            new_cfg = dict(cfg, tabs=[t for t in sessions.ALL_TABS if t in tabs] or ["join"], summary_enabled=summary_on)
            store.set_config(session_code, new_cfg)
            st.rerun()

    if not cfg["anonymous"]:
        with sb.expander("🔍 Raw session data (recovery)"):
            st.caption(
                "Read-only. Shows everything actually stored for this session, including any fields "
                "no longer used by the current screens."
            )
            st.json(data)

    sb.divider()
    if sb.button("End session / start a new one"):
        st.query_params.clear()
        st.rerun()

    if sb.button("Log out of facilitator mode"):
        auth.logout(cookies)
        st.rerun()


# --------------------------------------------------------- agree controls --
def render_agree_controls(session_code, device_id, data, collection, item_id, on_label="✓ Agreed", off_label="Agree", count_word="agree"):
    counts = data["agree_counts"].get(collection, {})
    mine = data["my_agree"].get(collection, {}).get(device_id, {})
    agreed = item_id in mine
    count = counts.get(item_id, 0)
    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button(on_label if agreed else off_label, key=f"agree_{collection}_{item_id}"):
            def mutate(d, collection=collection, item_id=item_id, device_id=device_id):
                store.toggle_agree(d, collection, item_id, device_id)
            store.update(session_code, mutate)
            st.rerun()
    with c2:
        st.markdown(f'<div style="padding-top:8px; font-size:11px; color:var(--pencil);">{count} {count_word}</div>', unsafe_allow_html=True)
    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)


def render_agree_item(session_code, device_id, data, collection, item, tag_label=None, quad=None, show_tag=True):
    quad_class = f" q-{quad}" if quad else ""
    tag_html = ""
    if show_tag:
        label = tag_label if tag_label is not None else esc(item.get("tag") or "Unspecified")
        tag_html = f'<span class="tag">{label}</span>'
    st.markdown(f'<div class="note{quad_class}">{esc(item["text"])}{tag_html}</div>', unsafe_allow_html=True)
    render_agree_controls(session_code, device_id, data, collection, item["id"])


# ------------------------------------------------------------------ join --
def render_join(session_code, device_id, data, cfg, is_facilitator):
    if cfg["anonymous"]:
        render_join_anonymous(session_code, device_id, data, cfg)
    else:
        render_join_tagged(session_code, device_id, data, cfg)
    if is_facilitator:
        render_facilitator_join_block(session_code, data, cfg)


def render_join_tagged(session_code, device_id, data, cfg):
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
            "joined": time.time(),
        }
        _upsert_roster(session_code, device_id, entry)
        # auto-advance straight to the next screen — no separate continue step
        st.session_state.active_screen = next_tab(cfg, "join")
        st.rerun()

    if my_entry:
        st.success(f"You're in as {my_entry.get('service_line', '')} · {my_entry.get('title') or 'no title'} · {my_entry['level']}.")

    st.markdown(
        '<div class="prompt-box" style="margin-top:20px;"><div class="label">Who\'s here</div>'
        "<p style=\"font-size:13px;\">Everyone who's joined so far, shown by service line, title, and level.</p></div>",
        unsafe_allow_html=True,
    )
    roster = data["roster"]
    if roster:
        chips = "".join(
            f'<span class="roster-chip">{esc(p.get("service_line", ""))} <span class="lvl">· {esc(p.get("title") or "no title")} · {esc(p["level"])}</span></span>'
            for p in roster
        )
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-note">No one has joined yet.</div>', unsafe_allow_html=True)


def render_join_anonymous(session_code, device_id, data, cfg):
    st.markdown(
        '<div class="prompt-box"><div class="label">Step 1</div>'
        "<p>No name is collected, and nothing you post shows who wrote it. Your level is used only for "
        "reporting and is never shown on screen.</p></div>",
        unsafe_allow_html=True,
    )
    my_entry = my_roster_entry(data, device_id)

    with st.form("join_form", clear_on_submit=True):
        level = st.selectbox("Level (used only for reporting, never shown)", LEVELS, index=0)
        submitted = st.form_submit_button("Join the room", type="primary")

    if submitted:
        _upsert_roster(session_code, device_id, {"device_id": device_id, "level": level, "joined": time.time()})
        st.session_state.active_screen = next_tab(cfg, "join")
        st.rerun()

    if my_entry:
        st.success("You're in.")

    n = len(data["roster"])
    st.markdown(
        '<div class="prompt-box" style="margin-top:20px;"><div class="label">Who\'s here</div>'
        f'<p class="join-count">{n} {"person has" if n == 1 else "people have"} joined</p></div>',
        unsafe_allow_html=True,
    )


def _upsert_roster(session_code, device_id, entry):
    def mutate(d):
        roster = d["roster"]
        idx = next((i for i, p in enumerate(roster) if p["device_id"] == device_id), None)
        if idx is not None:
            entry.setdefault("joined", roster[idx].get("joined"))
            roster[idx] = entry
        else:
            roster.append(entry)

    store.update(session_code, mutate)


def render_facilitator_join_block(session_code, data, cfg):
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.divider()
    st.markdown('<div class="board-eyebrow">Facilitator only</div>', unsafe_allow_html=True)

    files = export.board_files(session_code, data, cfg)
    st.download_button(
        "⬇️ Export all boards (CSV)",
        data=export.zip_files(files),
        file_name=f"{session_code}_export_{export.stamp()}.zip",
        mime="application/zip",
        key="export_all_main",
    )
    st.caption("Also in the sidebar (») on every tab.")

    # Summary lives here when the session has no Closing tab (e.g. PA-01).
    if cfg["summary_enabled"] and "closing" not in cfg["tabs"]:
        st.markdown("#### Summary")
        render_summary(session_code, data, cfg, is_facilitator=True)
        st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

    now = time.time()
    armed_at = st.session_state.get("reset_armed_at")
    armed = armed_at is not None and (now - armed_at) < RESET_CONFIRM_WINDOW
    if armed:
        remaining = max(0, RESET_CONFIRM_WINDOW - (now - armed_at))
        if st.button(f"⚠️ Click again to confirm reset ({remaining:.0f}s)", key="reset_confirm_btn", type="primary"):
            store.reset(session_code)
            st.session_state.pop("reset_armed_at", None)
            st.rerun()
        st.caption(
            f"This clears all posts, agree counts, and the roster for {session_code} only. Other sessions are "
            "untouched. A copy is archived in the database first."
        )
    else:
        if armed_at is not None:
            st.session_state.pop("reset_armed_at", None)
        if st.button("Reset board", key="reset_arm_btn"):
            st.session_state["reset_armed_at"] = now
            st.rerun()


# ----------------------------------------------------------------- notes --
def render_notes(session_code, device_id, data, cfg):
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
        post = new_post(data, device_id, cfg, text.strip(), "n")
        data = store.update(session_code, lambda d: d["notes"].append(post))

    notes = data["notes"]
    if notes:
        for n in reversed(notes):
            render_agree_item(session_code, device_id, data, "notes", n, show_tag=not cfg["anonymous"])
    else:
        st.markdown('<div class="empty-note">No notes yet, be the first to post.</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------- map --
def render_map(session_code, device_id, data, cfg):
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
            post = dict(new_post(data, device_id, cfg, text.strip(), "m"), x=x, y=y)
            store.update(session_code, lambda d: d["map"].append(post))
            st.session_state.pop("pending_map_xy", None)
            st.session_state["map_selected_task"] = ""
            st.rerun()
        elif cancel:
            st.session_state.pop("pending_map_xy", None)
            st.rerun()

    if notes:
        st.markdown("#### Placed so far")
        for n in reversed(notes):
            render_agree_item(session_code, device_id, data, "map", n, quad=quad_of(n["x"], n["y"]), show_tag=not cfg["anonymous"])


# ----------------------------------------------------------------- ideas --
def render_ideas(session_code, device_id, data, cfg):
    friction = cfg["ideas_style"] == "friction"
    if friction:
        st.markdown(
            '<div class="prompt-box"><div class="label">Prompt</div>'
            "<p>Think of a task you do regularly. Where does time or effort get lost? Describe the task and "
            "where it slows down.</p></div>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<div class=\"prompt-sub\">Agreeing with a post shows it's shared. It does not rank it. Different "
            "roles will hit different friction.</div>",
            unsafe_allow_html=True,
        )
        placeholder, button, empty = (
            "Describe a task and where it slows you down",
            "Add friction point",
            "No friction points posted yet, be the first.",
        )
    else:
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
        placeholder, button, empty = (
            "What slows you down that AI could realistically help with?",
            "Add bottleneck",
            "No bottlenecks posted yet, be the first.",
        )

    with st.form("idea_form", clear_on_submit=True):
        idea_text = st.text_area(button, label_visibility="collapsed", placeholder=placeholder, height=80)
        add_idea = st.form_submit_button(button, type="primary")
    if add_idea and idea_text.strip():
        post = new_post(data, device_id, cfg, idea_text.strip(), "u")
        data = store.update(session_code, lambda d: d["ideas"].append(post))

    ideas = data.get("ideas") or []
    if ideas:
        for idea in reversed(ideas):
            if cfg["anonymous"]:
                render_agree_item(session_code, device_id, data, "ideas", idea, show_tag=False)
            else:
                label = f"Shared by {esc(idea['tag'])}" if idea.get("tag") else "Unspecified"
                render_agree_item(session_code, device_id, data, "ideas", idea, tag_label=label)
    else:
        st.markdown(f'<div class="empty-note">{empty}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------ AI in our work --
OUTCOME_CLASS = {"Worked well": "good", "Partly": "mixed", "Didn't work": "bad"}


def render_ailog(session_code, device_id, data, cfg):
    st.markdown(
        '<div class="prompt-box"><div class="label">AI in Our Work</div>'
        "<p>Things that didn't work are as useful as things that did.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="prompt-sub">Share where you use AI, what worked, what didn\'t, and the biggest barrier to making '
        "it useful for you. One entry is one experience — add as many as you like.</div>",
        unsafe_allow_html=True,
    )

    entries = data.get("ailog") or []
    render_ailog_summary(entries)
    render_ailog_form(session_code, device_id, data)

    st.markdown("#### Shared so far")
    if not entries:
        st.markdown('<div class="empty-note">No entries yet, be the first to share one.</div>', unsafe_allow_html=True)
        return

    c1, c2 = st.columns(2)
    outcome_f = c1.selectbox("Outcome", ["All outcomes"] + AI_OUTCOMES, key="ai_filter_outcome")
    barrier_f = c2.selectbox("Barrier", ["All barriers"] + AI_BARRIERS, key="ai_filter_barrier")
    shown = [
        e for e in entries
        if (outcome_f == "All outcomes" or e.get("outcome") == outcome_f)
        and (barrier_f == "All barriers" or e.get("barrier") == barrier_f)
    ]
    if len(shown) != len(entries):
        st.caption(f"Showing {len(shown)} of {len(entries)} entries.")
    if not shown:
        st.markdown('<div class="empty-note">No entries match these filters.</div>', unsafe_allow_html=True)
    for e in reversed(shown):
        render_ailog_card(session_code, device_id, data, e)


def render_ailog_summary(entries):
    n = len(entries)
    outcome_counts = {o: sum(1 for e in entries if e.get("outcome") == o) for o in AI_OUTCOMES}
    stats = "".join(
        f'<div class="stat stat-{OUTCOME_CLASS[o]}"><div class="num">{outcome_counts[o]}</div><div class="lbl">{esc(o)}</div></div>'
        for o in AI_OUTCOMES
    )
    barrier_counts = {b: sum(1 for e in entries if e.get("barrier") == b) for b in AI_BARRIERS}
    ranked = sorted((kv for kv in barrier_counts.items() if kv[1]), key=lambda kv: kv[1], reverse=True)
    if ranked:
        rows = "".join(f'<li><span class="cnt">{c}</span>{esc(b)}</li>' for b, c in ranked)
        barriers = f'<ol class="barrier-rank">{rows}</ol>'
    else:
        barriers = '<div class="empty-note">No barriers yet.</div>'
    st.markdown(
        f'<div class="prompt-box ai-summary"><div class="label">Live summary · {n} {"entry" if n == 1 else "entries"}</div>'
        f'<div class="stat-row">{stats}</div>'
        f'<div class="label" style="margin-top:12px;">Biggest barriers</div>{barriers}</div>',
        unsafe_allow_html=True,
    )


def render_ailog_form(session_code, device_id, data):
    # Not an st.form: the "Other" box has to appear as soon as Other is picked.
    # Widget keys carry a generation number so a successful post clears them.
    g = st.session_state.setdefault("ai_form_gen", 0)
    st.markdown("#### Add an experience")
    if st.session_state.pop("ai_flash", False):
        st.success("Added. Thank you.")
    st.markdown(
        '<div class="warn-box">Do not enter client names, client data, or confidential information.</div>',
        unsafe_allow_html=True,
    )
    task = st.text_input("Task *", key=f"ai_task_{g}", max_chars=150, placeholder="e.g. Drafting a first pass of a briefing note")
    tool = st.selectbox("Tool used", AI_TOOLS, index=None, placeholder="Choose a tool", key=f"ai_tool_{g}")
    how = st.text_input("How you used it", key=f"ai_how_{g}", max_chars=300)
    outcome = st.radio("Outcome *", AI_OUTCOMES, index=None, horizontal=True, key=f"ai_outcome_{g}")
    worked = st.text_area("What worked", key=f"ai_worked_{g}", height=70, max_chars=600)
    didnt = st.text_area("What didn't", key=f"ai_didnt_{g}", height=70, max_chars=600)
    barrier = st.selectbox("Biggest barrier *", AI_BARRIERS, index=None, placeholder="Choose the biggest barrier", key=f"ai_barrier_{g}")
    barrier_other = ""
    if barrier == "Other":
        barrier_other = st.text_input("Other barrier (optional)", key=f"ai_barrier_other_{g}", max_chars=200)
    time_impact = st.selectbox(
        "Rough time saved or lost (optional)", AI_TIME_IMPACT, index=None, placeholder="Choose one", key=f"ai_time_{g}"
    )
    confirm = st.checkbox("I have not entered any client-identifiable or confidential data.", key=f"ai_confirm_{g}")
    if st.session_state.get("ai_error"):
        st.error(st.session_state["ai_error"])

    if st.button("Add entry", type="primary", key=f"ai_submit_{g}"):
        missing = []
        if not (task or "").strip():
            missing.append("Task")
        if not outcome:
            missing.append("Outcome")
        if not barrier:
            missing.append("Biggest barrier")
        if not confirm:
            missing.append("the confirmation checkbox")
        if missing:
            # Kept in session state so the next 4-second refresh doesn't wipe it.
            st.session_state["ai_error"] = "Please complete: " + ", ".join(missing) + "."
            st.rerun()
        entry = my_roster_entry(data, device_id)
        record = {
            "id": "a" + uuid.uuid4().hex[:8],
            "task": task.strip(),
            "tool": tool or "",
            "how": (how or "").strip(),
            "outcome": outcome,
            "worked": (worked or "").strip(),
            "didnt": (didnt or "").strip(),
            "barrier": barrier,
            "barrier_other": (barrier_other or "").strip() if barrier == "Other" else "",
            "time_impact": time_impact or "",
            "level": (entry or {}).get("level", ""),
            "created": time.time(),
        }
        store.update(session_code, lambda d: d["ailog"].append(record))
        st.session_state["ai_form_gen"] = g + 1
        st.session_state["ai_flash"] = True
        st.session_state.pop("ai_error", None)
        st.rerun()


def render_ailog_card(session_code, device_id, data, e):
    detail = []
    for label, key in (("Tool", "tool"), ("How", "how"), ("What worked", "worked"), ("What didn't", "didnt")):
        if e.get(key):
            detail.append(f'<div class="ai-line"><b>{label}:</b> {esc(e[key])}</div>')
    if e.get("barrier") == "Other" and e.get("barrier_other"):
        detail.append(f'<div class="ai-line"><b>Barrier:</b> {esc(e["barrier_other"])}</div>')
    if e.get("time_impact"):
        detail.append(f'<div class="ai-line"><b>Time:</b> {esc(e["time_impact"])}</div>')
    st.markdown(
        f'<div class="note ai-entry"><div class="ai-task">{esc(e["task"])}</div>'
        f'<div class="chips"><span class="chip chip-{OUTCOME_CLASS.get(e.get("outcome"), "mixed")}">{esc(e.get("outcome", ""))}</span>'
        f'<span class="chip">{esc(e.get("barrier", ""))}</span></div>'
        f'{"".join(detail)}</div>',
        unsafe_allow_html=True,
    )
    render_agree_controls(
        session_code, device_id, data, "ailog", e["id"],
        on_label="✓ Same for me", off_label="Same for me", count_word="same for me",
    )


# --------------------------------------------------------------- summary --
def render_summary(session_code, data, cfg, is_facilitator):
    pulse = cfg["summary_style"] == "pulse"
    existing = data.get("summary")

    if is_facilitator and cfg["summary_enabled"]:
        if st.session_state.get("summary_error"):
            st.error(st.session_state["summary_error"])

        if st.button("Generate summary from live board", type="primary", key="summary_btn"):
            st.session_state.pop("summary_error", None)
            if pulse:
                board_data, prompt, max_tokens = build_pulse_data(data), PULSE_SYSTEM_PROMPT, 900
            else:
                board_data, prompt, max_tokens = build_board_data(data), None, 1200
            placeholder = st.empty()
            accumulated = ""
            try:
                kwargs = {"system_prompt": prompt} if prompt else {}
                for chunk in stream_summary(board_data, max_tokens=max_tokens, **kwargs):
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
    elif is_facilitator:
        st.caption("The summary is switched off for this session. Turn it on in ⚙️ Session settings.")

    if existing and existing.get("text"):
        st.markdown(f'<div class="summary-output">{esc(existing["text"])}</div>', unsafe_allow_html=True)
    elif not is_facilitator:
        st.markdown('<div class="empty-note">Waiting for your facilitator to generate the closing summary.</div>', unsafe_allow_html=True)


def render_closing(session_code, device_id, data, cfg, is_facilitator):
    st.markdown(
        '<div class="prompt-box"><div class="label">Closing</div>'
        "<p>This pulls everything the room posted into one synthesis for leadership, grounded in what was "
        "actually said. Best run live, projected on a shared screen, as the closing moment of the session.</p></div>",
        unsafe_allow_html=True,
    )
    render_summary(session_code, data, cfg, is_facilitator)


# -------------------------------------------------------------- everyone --
def render_everyone():
    st.markdown(
        '<div class="prompt-box"><div class="label">N = Everyone</div>'
        "<p>Today's session gives us a live snapshot of the room. N = Everyone is the longer, anonymous "
        "follow-up survey that goes to the whole company, it's what turns today's conversation into a real "
        "signal leadership can act on, current tool usage, effectiveness, and where you'd actually want AI "
        "in your workflow.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="prompt-sub">About 12 to 15 minutes, anonymous, results reported by service line and '
        "title, not by name.</div>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/1_N_Everyone_Survey.py", label="Take the N = Everyone survey", icon="📝", use_container_width=True)


# ------------------------------------------------------------------- nav --
def render_nav(cfg):
    tabs = cfg["tabs"]
    if st.session_state.get("active_screen") not in tabs:
        st.session_state.active_screen = tabs[0]

    for i in range(0, len(tabs), 3):
        cols = st.columns(3)
        for col, key in zip(cols, tabs[i:i + 3]):
            active = st.session_state.active_screen == key
            if col.button(sessions.tab_label(key, cfg), key=f"nav_{key}", type="primary" if active else "secondary", use_container_width=True):
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

    # Facilitator status is a signed cookie set by passphrase login, never
    # a URL flag.
    is_facilitator = auth.is_facilitator(safe_cookie_get(cookies, auth.COOKIE))

    session_param = st.query_params.get("session", "")
    if not session_param:
        render_facilitator_setup(cookies, is_facilitator)
        return

    session_code = store.normalize_code(session_param)

    # Device identity lives in a browser cookie, not the URL — a cookie
    # persists across refreshes but is scoped to that one browser, so it
    # can never ride along when a join link gets copied or forwarded
    # after someone has already joined.
    cookie_device_id = safe_cookie_get(cookies, "workshop_device_id")
    if cookie_device_id:
        device_id = cookie_device_id
        st.session_state.device_id = cookie_device_id
    else:
        if "device_id" not in st.session_state:
            st.session_state.device_id = uuid.uuid4().hex[:9]
        device_id = st.session_state.device_id
        if had_prior_cookie_sync:
            cookies.set("workshop_device_id", device_id, max_age=60 * 60 * 24 * 30)

    st_autorefresh(interval=4000, key="board_autorefresh")

    try:
        data = store.load(session_code)
    except Exception as e:
        st.error(f"Can't reach the board's database right now, so nothing can be shown or saved. Try again in a moment. ({type(e).__name__})")
        st.stop()
    cfg = sessions.config_for(session_code, data)

    # Participants in sessions without the survey tab see no sidebar at all
    # (no page links to the survey or its results).
    if not is_facilitator and "everyone" not in cfg["tabs"]:
        theme.hide_sidebar()

    st.markdown('<div class="board-eyebrow">Live Session Board</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="board-title">{esc(APP_TITLE)}</div>', unsafe_allow_html=True)

    last_updated = data.get("last_updated")
    if last_updated:
        secs = max(0, int(time.time() - last_updated))
        status = "updated just now" if secs < 5 else f"updated {secs}s ago"
    else:
        status = "no activity yet"
    st.markdown(f'<div class="board-status">{status} · syncs every few seconds</div>', unsafe_allow_html=True)

    if is_facilitator:
        render_facilitator_sidebar(session_code, data, cfg, cookies)

    render_nav(cfg)
    screen = st.session_state.active_screen

    if screen == "join":
        render_join(session_code, device_id, data, cfg, is_facilitator)
    elif screen == "notes":
        render_notes(session_code, device_id, data, cfg)
    elif screen == "map":
        render_map(session_code, device_id, data, cfg)
    elif screen == "ideas":
        render_ideas(session_code, device_id, data, cfg)
    elif screen == "ailog":
        render_ailog(session_code, device_id, data, cfg)
    elif screen == "everyone":
        render_everyone()
    elif screen == "closing":
        render_closing(session_code, device_id, data, cfg, is_facilitator)


if __name__ == "__main__":
    main()

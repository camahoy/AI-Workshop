"""Field Notes: AI Optimization Workshop — live, cross-level workshop board.

Session code is passed via ?session=CODE in the URL (baked into the QR
join link by the facilitator) and namespaces all stored data. Facilitator
mode is unlocked via ?admin=1, set automatically when a facilitator
creates a session from the landing screen.
"""
import html
import time
import uuid

import qrcode
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from streamlit_cookies_controller import CookieController
from io import BytesIO

from lib import store, groups as groupslib
from lib.agency_map import QUAD_LABELS, build_map_figure, quad_of
from lib.claude_summary import SEED_VOTE_IDEAS, build_board_data, stream_summary

LEVELS = ["Analyst", "Manager", "Director", "Client Officer", "VP", "SVP", "President", "CEO"]
PULSE_YNS_QUESTIONS = [
    ("q1", "Do you feel AI is currently being applied to the right parts of your work?"),
    ("q2", "Do you feel you have a say in how AI gets applied to your work going forward?"),
]
PULSE_TRUST_QUESTION = ("q4", "Do you trust AI-assisted research findings as much as fully human-led research?")
PULSE_OPTIONS = ["Yes", "Somewhat", "No"]

TAB_KEYS = ["join", "notes", "map", "vote", "pulse", "summary"]
TAB_LABELS = {
    "join": "Join & Groups",
    "notes": "Good Research",
    "map": "Agency Map",
    "vote": "Dot Vote",
    "pulse": "Closing Pulse",
    "summary": "Summary",
}

st.set_page_config(
    page_title="Field Notes: AI Workshop Board",
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
.board-title { font-family: Georgia, serif; font-size: 26px; font-weight: 700; margin: 2px 0 6px; color: var(--ink); }
.board-status { font-size: 11px; color: var(--pencil); margin-bottom: 12px; }
.prompt-box { border: 2px solid var(--ink); background: var(--card); padding: 14px 16px; margin-bottom: 16px; border-radius: 6px; }
.prompt-box.soft { border: 1px solid var(--line); background: transparent; box-shadow: none; padding: 10px 14px; }
.prompt-box .label { font-size: 11px; text-transform: uppercase; letter-spacing: .1em; color: var(--moss); font-weight: 700; margin-bottom: 4px; }
.prompt-box p { margin: 0; font-family: Georgia, serif; font-size: 15px; line-height: 1.5; color: var(--ink); }
.prompt-box.soft p { font-family: 'Courier New', monospace; font-size: 12.5px; line-height: 1.55; }
.wall { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; margin-top: 10px; }
.note { background: var(--card); border: 1.5px solid var(--ink); border-radius: 3px; padding: 12px; font-size: 13px; line-height: 1.4; color: var(--ink); box-shadow: 2px 2px 0 var(--line); }
.roster-chip { display: inline-block; background: var(--card); border: 1px solid var(--ink); border-radius: 12px; padding: 4px 11px; font-size: 11.5px; margin: 2px 4px 2px 0; color: var(--ink); }
.roster-chip .lvl { color: var(--rust); font-weight: 700; }
.group-card { border: 1.5px solid var(--ink); background: var(--card); border-radius: 5px; padding: 12px 14px; margin-bottom: 10px; }
.group-card h4 { margin: 0 0 6px; font-family: Georgia, serif; border-bottom: 1px solid var(--line); padding-bottom: 5px; color: var(--ink); }
.group-member { font-size: 12.5px; display: flex; justify-content: space-between; padding: 2px 0; color: var(--ink); }
.group-member .lvl { color: var(--rust); font-size: 10.5px; text-transform: uppercase; }
.pulse-bar-row { display: flex; align-items: center; gap: 8px; margin-top: 4px; font-size: 12px; color: var(--ink); }
.pulse-bar-track { flex: 1; height: 9px; background: var(--line); border-radius: 5px; overflow: hidden; }
.pulse-bar-fill { height: 100%; background: var(--moss); }
.pulse-label { width: 78px; }
.empty-note { color: var(--pencil); font-style: italic; font-size: 13px; }
.summary-output { border: 2px solid var(--ink); background: var(--card); border-radius: 6px; padding: 18px; font-family: Georgia, serif; font-size: 14.5px; line-height: 1.65; color: var(--ink); white-space: pre-wrap; }
div[data-testid="stButton"] button[kind="primary"] { background-color: var(--mustard); border-color: var(--ink); color: var(--ink); }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def esc(s: str) -> str:
    return html.escape(s or "")


# ---------------------------------------------------------------- landing --
def render_facilitator_setup():
    st.markdown('<div class="board-eyebrow">Live Session Board</div>', unsafe_allow_html=True)
    st.markdown('<div class="board-title">Field Notes: AI Optimization Workshop</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="prompt-box"><div class="label">Facilitator setup</div>'
        "<p>This link has no active session. Start one below, then share the "
        "QR code or join link with the room — no one needs to see the code itself.</p></div>",
        unsafe_allow_html=True,
    )
    default_code = "SF-01"
    code_input = st.text_input("Session code", value=default_code, help="e.g. SF-01, NYC-02 — short and unique per workshop")
    if st.button("Start session", type="primary"):
        code = store.normalize_code(code_input)
        st.query_params["session"] = code
        st.query_params["admin"] = "1"
        st.rerun()
    st.caption("Already have a join link or QR code as a participant? Ask your facilitator — this screen is for starting a new session.")


# ------------------------------------------------------------- sidebar ui --
def render_facilitator_sidebar(session_code, data):
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
    st.sidebar.markdown("**Groups**")
    group_size = st.sidebar.number_input(
        "People per table", min_value=3, max_value=8, value=int(data.get("group_size", 5))
    )
    if st.sidebar.button("Generate mixed-level groups"):
        roster = data.get("roster", [])
        new_groups = groupslib.generate_groups(roster, group_size)

        def mutate(d):
            d["groups"] = new_groups
            d["group_size"] = group_size

        store.update(session_code, mutate)
        st.rerun()

    st.sidebar.divider()
    st.sidebar.markdown("**Reset**")
    confirm = st.sidebar.checkbox("Yes, clear all data for this session")
    if st.sidebar.button("Reset board", disabled=not confirm):
        store.reset(session_code)
        st.rerun()

    st.sidebar.divider()
    if st.sidebar.button("End session / start a new one"):
        st.query_params.clear()
        st.rerun()


# ------------------------------------------------------------------ join --
def render_join(session_code, device_id, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Step 1</div>'
        "<p>Enter your name and level so we can mix breakout groups across the room.</p></div>",
        unsafe_allow_html=True,
    )

    my_entry = next((p for p in data["roster"] if p["device_id"] == device_id), None)

    with st.form("join_form", clear_on_submit=True):
        name = st.text_input("Name", value="", placeholder="First name is fine")
        level = st.selectbox("Level", LEVELS, index=0)
        submitted = st.form_submit_button("Join the room", type="primary")

    if submitted and name.strip():
        entry = {"device_id": device_id, "name": name.strip(), "level": level}

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
        st.success(f"You're in as {my_entry['name']} ({my_entry['level']}).")

    st.markdown(
        '<div class="prompt-box" style="margin-top:20px;"><div class="label">Who\'s here</div>'
        "<p style=\"font-size:13px;\">Everyone who's joined so far — this list feeds the breakout groups.</p></div>",
        unsafe_allow_html=True,
    )
    roster = data["roster"]
    if roster:
        chips = "".join(
            f'<span class="roster-chip">{esc(p["name"])} <span class="lvl">· {esc(p["level"])}</span></span>'
            for p in roster
        )
        st.markdown(chips, unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-note">No one has joined yet.</div>', unsafe_allow_html=True)

    groups = data.get("groups")
    if groups:
        st.markdown("<br>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, g in enumerate(groups):
            members = "".join(
                f'<div class="group-member">{esc(p["name"])} <span class="lvl">{esc(p["level"])}</span></div>'
                for p in g
            )
            with cols[i % 2]:
                st.markdown(
                    f'<div class="group-card"><h4>Table {i + 1}</h4>{members}</div>',
                    unsafe_allow_html=True,
                )


# ----------------------------------------------------------------- notes --
def render_notes(session_code, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Prompt</div>'
        '<p>Good research means ___. Be specific — not "rigor" alone, but a moment where it showed up.</p></div>',
        unsafe_allow_html=True,
    )
    with st.form("note_form", clear_on_submit=True):
        text = st.text_area("Your note", label_visibility="collapsed", placeholder="Type your note and post it to the wall…", height=80)
        submitted = st.form_submit_button("Post", type="primary")
    if submitted and text.strip():
        def mutate(d):
            d["notes"].append({"text": text.strip()})
        data = store.update(session_code, mutate)

    notes = data["notes"]
    if notes:
        cards = "".join(f'<div class="note">{esc(n["text"])}</div>' for n in reversed(notes))
        st.markdown(f'<div class="wall">{cards}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-note">No notes yet — be the first to post.</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------- map --
def render_map(session_code, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Prompt</div>'
        "<p>Pick a task from your work — click the exact spot on the grid that matches how much AI "
        "is involved and what it removes, then name the task. Notes land exactly where you click.</p></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="prompt-box soft"><p>'
        "<strong>Low AI involvement</strong> = a person does this start to finish. "
        "<strong>High AI involvement</strong> = AI does the first pass and a person reviews it.<br>"
        "<strong>Removes drudgery</strong> = tedious work nobody misses. "
        "<strong>Removes judgment</strong> = a decision point where a person's read of the situation mattered."
        "</p></div>",
        unsafe_allow_html=True,
    )

    notes = data.get("map", [])
    if not notes:
        st.caption("Click anywhere on the grid to place the first note.")

    seq = st.session_state.get("map_chart_seq", 0)
    fig = build_map_figure(notes)
    event = st.plotly_chart(fig, on_select="rerun", key=f"map_chart_{seq}", use_container_width=True)

    points = event.selection.points if event else []
    if points and points[0].get("curve_number") == 0:
        st.session_state["pending_map_xy"] = (points[0]["x"], points[0]["y"])
        st.session_state["map_chart_seq"] = seq + 1

    pending = st.session_state.get("pending_map_xy")
    if pending:
        x, y = pending
        q = quad_of(x, y)
        with st.form("map_note_form", clear_on_submit=True):
            st.caption(f"Naming the task at this spot — {QUAD_LABELS[q]}")
            text = st.text_input(
                "Task", label_visibility="collapsed",
                placeholder="e.g. Spotting a contradiction between two data sources",
            )
            c1, c2 = st.columns(2)
            save = c1.form_submit_button("Add note", type="primary")
            cancel = c2.form_submit_button("Cancel")
        if save and text.strip():
            def mutate(d, x=x, y=y, t=text.strip()):
                d["map"].append({"x": x, "y": y, "text": t})
            store.update(session_code, mutate)
            st.session_state.pop("pending_map_xy", None)
            st.rerun()
        elif cancel:
            st.session_state.pop("pending_map_xy", None)
            st.rerun()


# ------------------------------------------------------------------ vote --
def render_vote(session_code, device_id, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Prompt</div>'
        "<p>Vote for the ideas you'd most want built first to grow revenue or make our AI use "
        "more sustainable — no need to explain your pick. One vote per idea, vote on as many "
        "as you want.</p></div>",
        unsafe_allow_html=True,
    )

    with st.form("idea_form", clear_on_submit=True):
        idea_text = st.text_area("Add your own idea", label_visibility="collapsed", placeholder="Add your own idea to the board…", height=68)
        add_idea = st.form_submit_button("Add idea")
    if add_idea and idea_text.strip():
        def mutate(d, t=idea_text.strip()):
            d.setdefault("ideas", [])
            if not d["ideas"]:
                d["ideas"] = [{"id": f"seed{i}", "text": s} for i, s in enumerate(SEED_VOTE_IDEAS)]
            d["ideas"].append({"id": "u" + uuid.uuid4().hex[:6], "text": t})
        data = store.update(session_code, mutate)
    else:
        data["ideas"] = store.ensure_ideas(session_code, SEED_VOTE_IDEAS)["ideas"]

    my_votes = data["my_votes"].get(device_id, {})

    votes = data["votes"]
    for idea in data["ideas"]:
        idea_id = idea["id"]
        count = votes.get(idea_id, 0)
        already_voted = idea_id in my_votes
        col1, col2 = st.columns([5, 1])
        with col1:
            dots = "●" * count if count else ""
            st.markdown(f"{esc(idea['text'])}  \n:orange[{dots}] *{count} vote{'s' if count != 1 else ''}*")
        with col2:
            if st.button("Voted" if already_voted else "+1", key=f"vote_{idea_id}", disabled=already_voted):
                def mutate(d, idea_id=idea_id, device_id=device_id):
                    mv = d["my_votes"].setdefault(device_id, {})
                    if idea_id in mv:
                        return
                    d["votes"][idea_id] = d["votes"].get(idea_id, 0) + 1
                    mv[idea_id] = 1
                store.update(session_code, mutate)
                st.rerun()


# ----------------------------------------------------------------- pulse --
def render_pulse(session_code, device_id, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">Anonymous — pick one for each</div>'
        "<p>Be honest. This is the number we're actually tracking after today.</p></div>",
        unsafe_allow_html=True,
    )
    my_pulse = data["my_pulse"].get(device_id, {})

    def render_yns(q, question):
        st.markdown(f"**{question}**")
        cols = st.columns(3)
        for i, opt in enumerate(PULSE_OPTIONS):
            selected = my_pulse.get(q) == opt
            label = f"✅ {opt}" if selected else opt
            if cols[i].button(label, key=f"pulse_{q}_{opt}"):
                def mutate(d, q=q, opt=opt, device_id=device_id):
                    mine = d["my_pulse"].setdefault(device_id, {})
                    prev = mine.get(q)
                    results = d["pulse"].setdefault(q, {})
                    if prev:
                        results[prev] = max(0, results.get(prev, 1) - 1)
                    results[opt] = results.get(opt, 0) + 1
                    mine[q] = opt
                store.update(session_code, mutate)
                st.rerun()

        results = data["pulse"].get(q, {})
        total = sum(results.values())
        bar_rows = ""
        for opt in PULSE_OPTIONS:
            c = results.get(opt, 0)
            pct = round((c / total) * 100) if total else 0
            bar_rows += (
                f'<div class="pulse-bar-row"><span class="pulse-label">{opt}</span>'
                f'<div class="pulse-bar-track"><div class="pulse-bar-fill" style="width:{pct}%"></div></div>'
                f"<span>{pct}% ({c})</span></div>"
            )
        st.markdown(bar_rows, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    q1_key, q1_text = PULSE_YNS_QUESTIONS[0]
    q2_key, q2_text = PULSE_YNS_QUESTIONS[1]
    render_yns(q1_key, q1_text)
    render_yns(q2_key, q2_text)

    st.markdown("**How easy or hard is it to integrate AI into your day-to-day workflow right now?**")
    slider_val = st.slider(
        "Ease of integration", min_value=1, max_value=5,
        value=int(my_pulse.get("q3", 3)), label_visibility="collapsed",
    )
    st.caption("1 · Very hard　　　3 · Manageable　　　5 · Very easy")
    if st.button("Submit", key="pulse_q3_submit"):
        def mutate(d, val=slider_val, device_id=device_id):
            mine = d["my_pulse"].setdefault(device_id, {})
            q3list = d["pulse"].setdefault("q3", [])
            if "q3" in mine:
                try:
                    q3list.remove(mine["q3"])
                except ValueError:
                    pass
            q3list.append(val)
            mine["q3"] = val
        store.update(session_code, mutate)
        st.rerun()
    if "q3" in my_pulse:
        st.caption(f"Your answer: {my_pulse['q3']}")
    q3vals = data["pulse"].get("q3", [])
    if q3vals:
        st.caption(f"Room average: {sum(q3vals) / len(q3vals):.1f} / 5 · {len(q3vals)} responses")
    else:
        st.caption("No responses yet")
    st.markdown("<br>", unsafe_allow_html=True)

    q4_key, q4_text = PULSE_TRUST_QUESTION
    render_yns(q4_key, q4_text)


# --------------------------------------------------------------- summary --
def render_summary(session_code, is_facilitator, data):
    st.markdown(
        '<div class="prompt-box"><div class="label">For facilitators</div>'
        "<p>Pull everything the room posted — notes, agency map, votes, pulse — into one "
        "synthesis focused on two questions: how do we raise revenue, and how do we implement "
        "AI in a mindful, sustainable way that doesn't rely on headcount cuts.</p></div>",
        unsafe_allow_html=True,
    )

    existing = data.get("summary")

    if is_facilitator:
        if st.session_state.get("summary_error"):
            st.error(st.session_state["summary_error"])

        if st.button("Generate summary from live board", type="primary"):
            st.session_state.pop("summary_error", None)
            ideas = data.get("ideas") or store.ensure_ideas(session_code, SEED_VOTE_IDEAS)["ideas"]
            board_data = build_board_data(
                data["roster"], data["notes"], data["map"], ideas, data["votes"], data["pulse"]
            )
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
    qp = st.query_params
    session_param = qp.get("session", "")

    if not session_param:
        render_facilitator_setup()
        return

    session_code = store.normalize_code(session_param)
    is_facilitator = qp.get("admin", "") == "1"

    # Device identity lives in a browser cookie, not the URL. A cookie
    # persists across refreshes but is scoped to that one browser, so
    # (unlike a ?u=... query param) it can never ride along when a join
    # link gets copied or forwarded after someone has already joined —
    # that was the earlier bug where names prefilled wrong and votes/
    # pulse answers collided across participants.
    # The cookie component's first read on a fresh browser session is
    # asynchronous: on the very first script run it can't yet know whether
    # a cookie exists (the browser round-trip hasn't landed). If we treated
    # that "not yet known" state as "no cookie" and wrote a fresh id right
    # away, a real reload would race its own restore and stomp the id it
    # was trying to recover. So: only ever persist a *new* id once we've
    # confirmed, on a later rerun, that the round-trip already completed
    # and there's still genuinely nothing there.
    had_prior_cookie_sync = "cookies" in st.session_state
    cookies = CookieController()
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

    st_autorefresh(interval=4000, key="board_autorefresh")

    st.markdown('<div class="board-eyebrow">Live Session Board</div>', unsafe_allow_html=True)
    st.markdown('<div class="board-title">Field Notes: AI Optimization Workshop</div>', unsafe_allow_html=True)

    data = store.load(session_code)

    last_updated = data.get("last_updated")
    if last_updated:
        secs = max(0, int(time.time() - last_updated))
        status = "updated just now" if secs < 5 else f"updated {secs}s ago"
    else:
        status = "no activity yet"
    st.markdown(f'<div class="board-status">{status} · syncs every few seconds</div>', unsafe_allow_html=True)

    if is_facilitator:
        render_facilitator_sidebar(session_code, data)
        data = store.load(session_code)

    render_nav()
    screen = st.session_state.active_screen

    if screen == "join":
        render_join(session_code, device_id, data)
    elif screen == "notes":
        render_notes(session_code, data)
    elif screen == "map":
        render_map(session_code, data)
    elif screen == "vote":
        render_vote(session_code, device_id, data)
    elif screen == "pulse":
        render_pulse(session_code, device_id, data)
    elif screen == "summary":
        render_summary(session_code, is_facilitator, data)


if __name__ == "__main__":
    main()

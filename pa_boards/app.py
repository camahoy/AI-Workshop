"""Live boards for the US Public Affairs AI session.

A separate Streamlit app from the SF board (../app.py): its own entry
point, storage and secrets, so it can be deployed and wiped on its own.

URLs:
  /                         index of the three boards
  /?board=a|b|c             participant view (what the QR codes open)
  /?board=a|b|c&view=present  presenter view (projector, passcode-gated)

Browser identity is a random id in a cookie (pa_browser_id). It is the
only thing used to cap one vote per person per post.
"""
import base64
import hashlib
import os
import sys
import time
import uuid
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path

if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st
from streamlit_cookies_controller import CookieController

from palib import ai_summary, config, export, qr, store, summary
from palib.ui import bars_html, esc, inject

# Phones redraw on their own only every 30 s (plus instantly on any tap and
# via "↻ Refresh"); the projector is the live view. All sessions share one
# Python process, and a 40-phone load test showed an 8 s phone refresh
# alone could saturate it. PA_PHONE_REFRESH_S=0 turns the timer off.
PARTICIPANT_REFRESH_S = float(os.environ.get("PA_PHONE_REFRESH_S", "30")) or None
FEED_LIMIT = 15  # posts shown on a phone before "Show all"
PRESENTER_REFRESH_S = 2
CONFIRM_WINDOW = 6  # seconds to confirm a destructive action
PRESENTER_COOKIE = "pa_presenter"
BROWSER_COOKIE = "pa_browser_id"
NOT_SET = "—"


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def safe_cookie_get(cookies, key):
    """Same guard as the SF board: the cookie component can raise before
    its first browser round-trip has landed. Treat that as "unknown"."""
    try:
        return cookies.get(key)
    except TypeError:
        return None


def secret(name, default=None):
    try:
        return st.secrets.get(name, default)
    except Exception:  # no secrets.toml at all
        return default


# Set by ../pages/3_PA_Live_Boards.py when the boards run as a page of the
# SF app, so QR codes and links include the page path.
PAGE = os.environ.get("PA_BOARDS_PAGE", "")


def passcode_token() -> str | None:
    # As a page of the SF app, its FACILITATOR_PASSWORD also works.
    code = secret("PRESENTER_PASSCODE") or secret("FACILITATOR_PASSWORD")
    if not code:
        return None
    return hashlib.sha256(f"pa-boards:{code}".encode()).hexdigest()[:24]


def ai_config():
    try:
        return ai_summary.provider_config(st.secrets)
    except Exception:  # no secrets.toml at all
        return None


def base_url(data) -> str:
    configured = data["settings"].get("base_url") or secret("APP_BASE_URL", "")
    if configured:
        return configured.rstrip("/")
    try:
        host = st.context.headers.get("Host", "")
    except Exception:
        host = ""
    if not host:
        return ""
    scheme = "http" if host.startswith(("localhost", "127.0.0.1")) else "https"
    return f"{scheme}://{host}"


def safe_cookie_write(cookies, method, *args, **kwargs) -> bool:
    """set()/remove() raise TypeError while the component's first
    round-trip is still pending (seen under load). Skipping is safe: the
    caller tries again on the next rerun, which comes within seconds."""
    try:
        getattr(cookies, method)(*args, **kwargs)
        return True
    except TypeError:
        return False


def browser_identity(cookies) -> str:
    """Cookie-backed random id. Only writes a new cookie once the
    component has round-tripped, so a reload can't stomp its own restore
    (same reasoning as main() in ../app.py)."""
    had_prior_sync = st.session_state.get("_cookie_synced", False)
    st.session_state["_cookie_synced"] = True
    existing = safe_cookie_get(cookies, BROWSER_COOKIE)
    if existing:
        temporary = st.session_state.get("browser_id")
        if temporary and temporary != existing:
            # Tapped before the cookie arrived: hand those taps to the real id.
            store.merge_browser(temporary, existing)
        st.session_state.browser_id = existing
        return existing
    if "browser_id" not in st.session_state:
        st.session_state.browser_id = "b" + uuid.uuid4().hex[:12]
    if had_prior_sync:
        safe_cookie_write(cookies, "set", BROWSER_COOKIE, st.session_state.browser_id, max_age=60 * 60 * 24 * 60)
    return st.session_state.browser_id


def set_state(name, value):
    st.session_state[name] = value


def armed(name: str) -> bool:
    at = st.session_state.get(f"armed_{name}")
    return at is not None and time.time() - at < CONFIRM_WINDOW


def confirm_button(container, name, label, confirm_label, on_confirm):
    """Two-click destructive control: first click arms it, a second click
    within CONFIRM_WINDOW seconds runs it, otherwise it disarms."""
    if armed(name):
        if container.button(confirm_label, key=f"{name}_confirm", type="primary", use_container_width=True):
            st.session_state.pop(f"armed_{name}", None)
            on_confirm()
            st.rerun()
    else:
        st.session_state.pop(f"armed_{name}", None)
        if container.button(label, key=f"{name}_arm", use_container_width=True):
            st.session_state[f"armed_{name}"] = time.time()
            st.rerun()


# =============================================================== index ==
def render_index():
    inject(st)
    st.markdown('<div class="pa-eyebrow">US Public Affairs · AI session</div>', unsafe_allow_html=True)
    st.markdown('<div class="pa-question">Live boards</div>', unsafe_allow_html=True)
    for key in config.BOARD_KEYS:
        b = config.BOARDS[key]
        st.link_button(f"Board {b['letter']}: {b['name']}", f"?board={key}", use_container_width=True)
    st.caption("Presenter: add &view=present to a board link.")


# ======================================================== participant ==
def render_header(key, data):
    b = config.BOARDS[key]
    st.markdown(f'<div class="pa-eyebrow">Board {b["letter"]} · {esc(b["name"])}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="pa-question">{esc(b["question"])}</div>', unsafe_allow_html=True)


def post_meta_html(key, post) -> str:
    chips = []
    if post.get("seed"):
        chips.append(f'<span class="pa-chip seed">{esc(config.SEED_LABEL)}</span>')
    if key == "a":
        for field in ("tool", "task"):
            if post.get(field):
                chips.append(f'<span class="pa-chip">{esc(post[field])}</span>')
    else:
        if post.get("freq"):
            chips.append(f'<span class="pa-chip">{esc(post["freq"])}</span>')
        if post.get("minutes"):
            chips.append(f'<span class="pa-chip">{post["minutes"]} min each time</span>')
    who = esc(post["name"]) if post.get("name") else ("" if post.get("seed") else "Anonymous")
    n_votes, n_comments = len(post["votes"]), len(store.visible_comments(post))
    counts = f'{n_votes} vote{"" if n_votes == 1 else "s"} · {n_comments} comment{"" if n_comments == 1 else "s"}'
    who_part = f"{who} · " if who else ""
    return "".join(chips) + f'<div class="meta">{who_part}{counts}</div>'


def submit_post(key):
    """Form callback: runs before the rerun, so the post is saved even if
    the rerun itself is interrupted (see render_post)."""
    ss = st.session_state
    b = config.BOARDS[key]
    fields = {f: ss.get(f"pf_{f}_{key}") for f in (("tool", "task") if key == "a" else ("freq", "minutes"))}
    fields = {k: (None if v == NOT_SET else v) for k, v in fields.items()}
    text = ss.get(f"pf_text_{key}") or ""
    if not text.strip():
        ss.post_msg = ("error", f"Please fill in “{b['text_label']}”.")
    elif store.add_post(key, ss.browser_id, text, ss.get(f"pf_name_{key}") or "", **fields):
        ss.post_msg = ("ok", "Posted. Thank you!")
    else:
        ss.post_msg = ("error", "Posting has just closed.")


def render_post_form(key):
    b = config.BOARDS[key]
    with st.form(f"post_form_{key}", clear_on_submit=True):
        st.text_area(f"{b['text_label']} (required)", max_chars=config.MAX_POST_CHARS, height=100, key=f"pf_text_{key}")
        if key == "a":
            st.selectbox("Tool (optional)", [NOT_SET] + config.TOOLS, key="pf_tool_a")
            st.selectbox("Task type (optional)", [NOT_SET] + config.TASK_TYPES, key="pf_task_a")
        else:
            st.selectbox("How often (optional)", [NOT_SET] + list(config.FREQUENCIES), key="pf_freq_b")
            st.number_input("Minutes each time (optional)", min_value=0, max_value=1440, value=None, step=5, key="pf_minutes_b")
        st.text_input("Name (optional, leave blank to stay anonymous)", max_chars=config.MAX_NAME_CHARS, key=f"pf_name_{key}")
        st.markdown(f'<div class="pa-privacy">{esc(config.PRIVACY_LINE)}</div>', unsafe_allow_html=True)
        st.form_submit_button("Post", type="primary", use_container_width=True, on_click=submit_post, args=(key,))
    msg = st.session_state.pop("post_msg", None)
    if msg and msg[0] == "ok":
        st.toast(msg[1])
    elif msg:
        st.error(msg[1])


def submit_comment(key, post_id):
    ss = st.session_state
    text = ss.get(f"cf_text_{post_id}") or ""
    if text.strip():
        store.add_comment(key, post_id, ss.browser_id, text, ss.get(f"cf_name_{post_id}") or "")


def comment_html(c) -> str:
    who = esc(c["name"]) if c.get("name") else "Anonymous"
    return f'<div class="pa-comment">{esc(c["text"])} <span class="who">— {who}</span></div>'


def render_comments(key, post, browser_id, is_open):
    comments = store.visible_comments(post)
    for c in comments:
        st.markdown(comment_html(c), unsafe_allow_html=True)
    if not comments:
        st.markdown('<div class="pa-empty">No comments yet.</div>', unsafe_allow_html=True)
    if is_open:
        with st.form(f"comment_form_{post['id']}", clear_on_submit=True):
            st.text_input("Add a comment", max_chars=config.MAX_COMMENT_CHARS, key=f"cf_text_{post['id']}")
            st.text_input("Name (optional)", max_chars=config.MAX_NAME_CHARS, key=f"cf_name_{post['id']}")
            st.caption(config.PRIVACY_LINE)
            st.form_submit_button("Add comment", use_container_width=True,
                                  on_click=submit_comment, args=(key, post["id"]))


def render_post(key, post, browser_id, is_open):
    st.markdown(
        f'<div class="pa-post"><div class="text">{esc(post["text"])}</div>{post_meta_html(key, post)}</div>',
        unsafe_allow_html=True,
    )
    mine = browser_id in post["votes"]
    label = config.BOARDS[key]["vote_label"]
    n = len(post["votes"])
    btn = f"✓ {label} · {n}  (tap to undo)" if mine else f"▲ {label} · {n}"
    vote_col, comment_col = st.columns([3, 2])
    # on_click, not `if st.button(...)`: callbacks run before the rerun, so
    # a tap is saved even if a second tap interrupts the rerun under load.
    vote_col.button(btn, key=f"vote_{post['id']}", type="primary" if mine else "secondary",
                    disabled=not is_open, use_container_width=True,
                    on_click=store.toggle_vote, args=(key, post["id"], browser_id))
    # One comment thread open at a time keeps the page light enough for
    # 40 phones refreshing every few seconds.
    showing = st.session_state.get("open_comments") == post["id"]
    comment_col.button("Hide comments" if showing else f"💬 Comments ({len(store.visible_comments(post))})",
                       key=f"comments_{post['id']}", use_container_width=True,
                       on_click=set_state, args=("open_comments", None if showing else post["id"]))
    if showing:
        render_comments(key, post, browser_id, is_open)


def board_state_changed(key, data) -> bool:
    """True when the presenter opened/closed or revealed since this page
    last fully rendered, so the form outside the live fragment updates."""
    board = data["boards"][key]
    state = (board["open"], board.get("revealed"))
    last = st.session_state.get(f"board_state_{key}")
    st.session_state[f"board_state_{key}"] = state
    return last is not None and last != state


@st.fragment(run_every=PARTICIPANT_REFRESH_S)
def posts_feed(key, browser_id):
    data = store.load()
    if board_state_changed(key, data):
        st.rerun()
    is_open = data["boards"][key]["open"]
    posts = store.visible_posts(data, key)
    status_col, refresh_col = st.columns([3, 1], vertical_alignment="center")
    status_col.markdown(f'<div class="pa-status">{plural(len(posts), "post")} · most votes first</div>', unsafe_allow_html=True)
    refresh_col.button("↻ Refresh", key=f"refresh_{key}", use_container_width=True)
    if not posts:
        st.markdown('<div class="pa-empty">Nothing yet. Be the first to post.</div>', unsafe_allow_html=True)
    show_all = st.session_state.get(f"show_all_{key}", False)
    # Top posts, plus always your own: a new post starts at 0 votes and
    # would otherwise sit below the fold on a busy board.
    shown = posts if show_all else posts[:FEED_LIMIT] + [p for p in posts[FEED_LIMIT:] if p["browser_id"] == browser_id]
    for post in shown:
        render_post(key, post, browser_id, is_open)
    if len(posts) > FEED_LIMIT:
        # Fixed label: a label that changes with every new post makes
        # Streamlit swap the button out, which can swallow a tap.
        label = f"Show top {FEED_LIMIT} only" if show_all else "Show all posts"
        st.button(label, key=f"show_all_btn_{key}", use_container_width=True,
                  on_click=set_state, args=(f"show_all_{key}", not show_all))


def render_participant_posts(key, data, browser_id):
    board_state_changed(key, data)
    if data["boards"][key]["open"]:
        render_post_form(key)
    else:
        st.markdown('<div class="pa-closed">Posting is closed for this board. Thank you!</div>', unsafe_allow_html=True)
    posts_feed(key, browser_id)


def submit_option_comment(index):
    """Adding a detail ("showcases of what?") also ticks that option."""
    ss = st.session_state
    text = ss.get(f"oc_text_{index}") or ""
    if text.strip() and store.add_comment("c", store.option_parent(index), ss.browser_id, text,
                                          ss.get(f"oc_name_{index}") or ""):
        if index not in store.load()["boards"]["c"]["picks"].get(ss.browser_id, []):
            store.toggle_pick(ss.browser_id, index)


def render_option_comment(c, browser_id, is_open):
    st.markdown(comment_html(c), unsafe_allow_html=True)
    mine = browser_id in c.get("votes", [])
    n = len(c.get("votes", []))
    st.button(f"✓ Upvoted · {n}" if mine else f"▲ Upvote · {n}", key=f"vote_{c['id']}",
              disabled=not is_open, on_click=store.toggle_vote, args=("c", c["id"], browser_id))


@st.fragment(run_every=PARTICIPANT_REFRESH_S)
def next_options(browser_id):
    """The five option cards: tick state, the details people added (with
    upvotes), and an always-visible "in what?" input. Option vote counts
    stay hidden until revealed."""
    data = store.load()
    if board_state_changed("c", data):
        st.rerun()
    board = data["boards"]["c"]
    is_open = board["open"]
    mine = board["picks"].get(browser_id, [])
    st.button("↻ Refresh", key="refresh_c")
    for i, label in enumerate(config.NEXT_OPTIONS):
        picked = i in mine
        with st.container(border=True):
            st.button(f"{'☑' if picked else '☐'}  {label}", key=f"pick_{i}", type="primary" if picked else "secondary",
                      disabled=not is_open, use_container_width=True,
                      on_click=store.toggle_pick, args=(browser_id, i))
            for c in store.ranked(store.option_comments(data, i)):
                render_option_comment(c, browser_id, is_open)
            if is_open:
                question, example = config.OPTION_PROMPTS[i]
                with st.form(f"oc_form_{i}", clear_on_submit=True):
                    st.text_input(f"{question} (optional)", placeholder=example,
                                  max_chars=config.MAX_COMMENT_CHARS, key=f"oc_text_{i}")
                    st.text_input("Name (optional)", max_chars=config.MAX_NAME_CHARS, key=f"oc_name_{i}")
                    st.caption(config.PRIVACY_LINE)
                    st.form_submit_button("Add", use_container_width=True,
                                          on_click=submit_option_comment, args=(i,))
    if board["revealed"]:
        s = summary.summarize_next(data)
        n = s["totals"]["participants"]
        st.markdown(f"### Results · {n} {'person' if n == 1 else 'people'}")
        st.markdown(bars_html(s["options"]), unsafe_allow_html=True)
    else:
        st.markdown('<div class="pa-status" style="margin-top:16px">Vote counts appear here when the presenter reveals them.</div>', unsafe_allow_html=True)


@st.fragment(run_every=PARTICIPANT_REFRESH_S)
def other_entries(browser_id):
    data = store.load()
    is_open = data["boards"]["c"]["open"]
    others = store.visible_others(data)
    st.markdown(f'<div class="pa-status" style="margin-top:12px">{plural(len(others), "Other idea")} · most upvotes first</div>', unsafe_allow_html=True)
    for o in others:
        render_post("c", o, browser_id, is_open)


def submit_other():
    ss = st.session_state
    text = ss.get("of_text") or ""
    if text.strip():
        store.add_other(ss.browser_id, text, ss.get("of_name") or "")


def render_participant_next(data, browser_id):
    board_state_changed("c", data)
    is_open = data["boards"]["c"]["open"]
    if is_open:
        st.markdown("Pick as many as you like. Tap again to untick. Use the box on each card to say what exactly you'd like.")
    else:
        st.markdown('<div class="pa-closed">Voting is closed. Thank you!</div>', unsafe_allow_html=True)
    next_options(browser_id)
    st.markdown(f'<div class="pa-eyebrow" style="margin-top:22px">{esc(config.BOARDS["c"]["other_label"])}</div>', unsafe_allow_html=True)
    if is_open:
        with st.form("other_form", clear_on_submit=True):
            st.text_area(config.BOARDS["c"]["other_label"], max_chars=config.MAX_POST_CHARS, height=80, key="of_text")
            st.text_input("Name (optional, leave blank to stay anonymous)", max_chars=config.MAX_NAME_CHARS, key="of_name")
            st.markdown(f'<div class="pa-privacy">{esc(config.PRIVACY_LINE)}</div>', unsafe_allow_html=True)
            st.form_submit_button("Add", type="primary", use_container_width=True, on_click=submit_other)
    other_entries(browser_id)


def render_participant(key, data, browser_id):
    inject(st)
    render_header(key, data)
    if key == "c":
        render_participant_next(data, browser_id)
    else:
        render_participant_posts(key, data, browser_id)


# ========================================================== presenter ==
def summary_html(s: dict, themes: dict | None) -> str:
    key = s["board"]
    t = s["totals"]
    when = time.strftime("%H:%M", time.localtime(s["generated_at"]))
    out = [f'<div class="pp-summary"><h3>Summary</h3><div class="note">Generated {when} · rule-based, counts only</div>']
    if key == "c":
        out.append(f"<p>{t['participants']} participants · {t['votes']} option votes · "
                   f"{t['others']} Other entries · {t['comments']} comments</p>")
        for o in s["options"]:
            out.append(f"<div><b>{o['votes']} ({o['pct']:.0f}%)</b> · {esc(o['label'])}</div>")
            out += [f"<div class='note' style='margin-left:28px'>“{esc(c['text'])}” · {c['votes']} upvotes</div>" for c in o["comments"]]
        if s["others"]:
            out.append("<h4>Other entries</h4>")
            for o in s["others"]:
                out.append(f"<div>• {esc(o['text'])} <b>({o['votes']} upvotes)</b></div>")
                out += [f"<div class='note' style='margin-left:28px'>“{esc(c['text'])}”</div>" for c in o["comments"]]
        return "".join(out) + "</div>"

    seed = f" (+{t['seed_posts']} seed rows)" if t.get("seed_posts") else ""
    out.append(f"<p>{t['posts']} posts{seed} · {t['votes']} votes · {t['comments']} comments · {t['participants']} participants</p>")
    out.append("<h4>Top 5 by votes</h4>")
    for i, row in enumerate(s["top"], 1):
        hours = f" · {esc(summary.fmt_hours(row['hours']))}" if key == "b" and row.get("hours") is not None else ""
        out.append(f"<div>{i}. {esc(row['text'])} <b>({row['votes']} votes{hours})</b></div>")
    if key == "a":
        cols = []
        for title, items in (("By tool", s["by_tool"]), ("By task type", s["by_task"])):
            cols.append(f"<div style='flex:1'><h4>{title}</h4>" + "".join(f"<div>{esc(n)}: {c}</div>" for n, c in items) + "</div>")
        out.append("<div style='display:flex; gap:40px'>" + "".join(cols) + "</div>")
    else:
        out.append("<h4>Biggest drains, hours per month (estimate)</h4>")
        if s["by_hours"]:
            out += [f"<div>{r['hours']:.1f} h · {esc(r['text'])}</div>" for r in s["by_hours"]]
            out.append(f"<div class='note'>Total across estimated items: {s['estimated_total_hours']:.1f} h/month. "
                       "Estimate = times per month × minutes ÷ 60 × (upvoters + poster).</div>")
        else:
            out.append("<div class='note'>None yet: needs both “How often” and “Minutes each time”.</div>")
    if themes:
        out.append(themes_html(themes, key))
    return "".join(out) + "</div>"


def themes_html(themes: dict, key: str) -> str:
    out = ["<h4>AI themes (counts calculated in code, quotes word for word)</h4>"]
    for t in themes.get(key, []):
        quotes = "".join(f"<div class='note'>“{esc(q)}”</div>" for q in t["quotes"])
        out.append(f"<div><b>{esc(t['name'])}</b> · {t['posts']} posts · {t['votes']} votes{quotes}</div>")
    out.append(f"<p><b>{esc(ai_summary.build_next_line(themes))}</b></p>")
    return "".join(out)


def render_presenter_login():
    inject(st)
    st.markdown('<div class="pa-question">Presenter view</div>', unsafe_allow_html=True)
    token = passcode_token()
    if not token:
        st.error("Neither PRESENTER_PASSCODE nor FACILITATOR_PASSWORD is set in this app's secrets, so the presenter view is locked. Add it under Settings → Secrets.")
        return
    with st.form("presenter_login"):
        code = st.text_input("Presenter passcode", type="password")
        ok = st.form_submit_button("Unlock", type="primary")
    if ok:
        if hashlib.sha256(f"pa-boards:{code}".encode()).hexdigest()[:24] == token:
            st.session_state.presenter = token
            st.session_state.cookie_presenter_pending = True
            st.rerun()
        else:
            st.error("Incorrect passcode.")


@st.fragment(run_every=8)
def live_sidebar(key):
    """Export buttons and the moderation list refresh on their own so
    they always reflect the latest posts without a page reload."""
    data = store.load()
    board = data["boards"][key]
    st.divider()
    st.markdown("**Export**")
    st.download_button("Export CSV (this board)", export.board_csv(data, key), export.filename(data, key),
                       mime="text/csv", use_container_width=True)
    st.download_button("Export all boards + summary (.zip)", export.all_zip(data), "pa-boards-export.zip",
                       mime="application/zip", use_container_width=True)
    url = base_url(data)
    if url:
        st.download_button("QR code PNG (this board)", qr_png(qr.participant_url(url, key, PAGE)),
                           f"qr-board-{key}.png", mime="image/png", use_container_width=True)
        st.download_button("QR code PNGs (all 3, .zip)", qr_zip(url), "pa-boards-qr.zip",
                           mime="application/zip", use_container_width=True)

    with st.expander("Moderate (hide a post or comment)"):
        items = sorted(store.iter_items(board), key=lambda i: -i["created_at"])
        if not items:
            st.caption("Nothing posted yet.")
        for item in items:
            kind = "comment" if item["id"].startswith("c") else "post"
            label = ("Unhide " if item.get("hidden") else "Hide ") + f"{kind}: " + item["text"][:60]
            st.button(label, key=f"mod_{item['id']}", use_container_width=True,
                      on_click=store.set_hidden, args=(key, item["id"], not item.get("hidden")))


@st.cache_data(max_entries=16)
def qr_png(link: str, size: int = qr.SLIDE_SIZE) -> bytes:
    return qr.png(link, size)


@st.cache_data(max_entries=4)
def qr_zip(url: str) -> bytes:
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for k in config.BOARD_KEYS:
            z.writestr(f"qr-board-{k}.png", qr_png(qr.participant_url(url, k, PAGE)))
    return buf.getvalue()


def generate_summary(key):
    store.save_summary(key, summary.summarize(store.load(), key))


def close_board(key):
    store.set_board_flag(key, "open", False)
    generate_summary(key)


def render_presenter_controls(key, data, cookies):
    sb = st.sidebar
    board = data["boards"][key]
    b = config.BOARDS[key]
    sb.markdown(f"### Board {b['letter']} controls")

    other_links = " · ".join(
        f"[{config.BOARDS[k]['letter']}](?board={k}&view=present)" for k in config.BOARD_KEYS if k != key
    )
    sb.markdown(f"Switch board: {other_links}")

    if board["open"]:
        verb = "voting" if key == "c" else "posting"
        sb.button(f"Close {verb} (and generate summary)", type="primary", use_container_width=True,
                  on_click=close_board, args=(key,))
    else:
        sb.button("Reopen voting" if key == "c" else "Reopen posting", use_container_width=True,
                  on_click=store.set_board_flag, args=(key, "open", True))

    if key == "c":
        sb.button("Hide results" if board["revealed"] else "Reveal results", type="primary", use_container_width=True,
                  on_click=store.set_board_flag, args=("c", "revealed", not board["revealed"]))

    sb.button("Hide QR code" if board["show_qr"] else "Show QR code", use_container_width=True,
              on_click=store.set_board_flag, args=(key, "show_qr", not board["show_qr"]))

    sb.button("Generate summary", use_container_width=True, on_click=generate_summary, args=(key,))
    if board.get("summary") and sb.button("Remove summary from screen", use_container_width=True):
        store.save_summary(key, None)
        st.rerun()

    if key in ("a", "b"):
        cfg = ai_config()
        if cfg and data["settings"].get("ai_summary"):
            if sb.button("Generate AI themes (A + B)", use_container_width=True):
                with st.spinner("Grouping posts into themes…"):
                    try:
                        store.save_ai_themes(ai_summary.generate(store.load(), cfg))
                    except Exception as e:  # show the reason, keep the board running
                        st.session_state.ai_error = f"AI themes failed: {e}"
                st.rerun()
            if st.session_state.get("ai_error"):
                sb.error(st.session_state.pop("ai_error"))

    with sb:
        live_sidebar(key)

    with sb.expander("Settings"):
        s = data["settings"]
        current = date.fromisoformat(s["session_date"]) if s.get("session_date") else None
        picked = st.date_input("Session date (used in exports)", value=current, format="YYYY-MM-DD")
        if picked and picked.isoformat() != s.get("session_date"):
            store.set_setting("session_date", picked.isoformat())
            st.rerun()
        new_url = st.text_input("App URL for QR codes", value=s.get("base_url") or "", placeholder=base_url(data) or "https://…")
        if new_url.strip().rstrip("/") != (s.get("base_url") or ""):
            store.set_setting("base_url", new_url.strip().rstrip("/"))
            st.rerun()
        seed = st.toggle("Board B seed rows (13 Aug session)", value=bool(s.get("seed_b")))
        if seed != bool(s.get("seed_b")):
            store.set_setting("seed_b", seed)
            st.rerun()
        days = st.number_input("Delete all data this many days after the session", min_value=1, max_value=365,
                               value=int(s.get("retention_days") or config.DEFAULT_RETENTION_DAYS))
        if days != s.get("retention_days"):
            store.set_setting("retention_days", int(days))
            st.rerun()
        st.caption("Auto-delete on " + time.strftime("%Y-%m-%d", time.localtime(store.delete_after(data))))
        if ai_config():
            ai_on = st.toggle("AI themes (approved model only)", value=bool(s.get("ai_summary")))
            if ai_on != bool(s.get("ai_summary")):
                store.set_setting("ai_summary", ai_on)
                st.rerun()
        else:
            st.caption("AI themes: off. No approved model is configured in secrets.")

    sb.divider()
    confirm_button(sb, f"reset_{key}", f"Reset Board {b['letter']}", f"⚠️ Confirm: wipe Board {b['letter']}", lambda: store.reset_board(key))
    confirm_button(sb, "delete_all", "Delete all data (all boards)", "⚠️ Confirm: delete everything", store.delete_all)
    if sb.button("Lock presenter view on this device", use_container_width=True):
        st.session_state.pop("presenter", None)
        safe_cookie_write(cookies, "remove", PRESENTER_COOKIE)
        st.rerun()


def render_presenter(key, data, cookies):
    inject(st, presenter=True)
    render_presenter_controls(key, data, cookies)
    presenter_display(key)


@st.fragment(run_every=PRESENTER_REFRESH_S)
def presenter_display(key):
    data = store.load()
    board = data["boards"][key]
    b = config.BOARDS[key]

    url = base_url(data)
    main_col, qr_col = st.columns([3, 1]) if board["show_qr"] else (st.container(), None)
    with main_col:
        st.markdown(f'<div class="pa-eyebrow" style="font-size:22px">Board {b["letter"]} · {esc(b["name"])}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pp-question">{esc(b["question"])}</div>', unsafe_allow_html=True)
        state = "open" if board["open"] else "closed"
        if key == "c":
            n = len(store.participants(data, "c"))
            st.markdown(f'<div class="pp-count">{n} {"person has" if n == 1 else "people have"} voted · voting {state}</div>', unsafe_allow_html=True)
            s = summary.summarize_next(data)
            if board["revealed"]:
                st.markdown(bars_html(s["options"], "pp-bars"), unsafe_allow_html=True)
                top_comments = [
                    f"<div><b>{esc(o['label'])}:</b> “{esc(o['comments'][0]['text'])}” · {plural(o['comments'][0]['votes'], 'upvote')}</div>"
                    for o in s["options"] if o["comments"]
                ]
                if top_comments:
                    st.markdown('<div class="pp-summary"><h4>Most-upvoted comment per option</h4>' + "".join(top_comments) + "</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="pp-summary">Vote counts are hidden. Use “Reveal results” in the sidebar.</div>', unsafe_allow_html=True)
                live = [
                    f"<div><b>{esc(o['label'])}:</b> “{esc(c['text'])}”</div>"
                    for o in sorted(s["options"], key=lambda o: config.NEXT_OPTIONS.index(o["label"])) for c in o["comments"][:2]
                ]
                if live:
                    st.markdown('<div class="pp-summary"><h4>Comments so far</h4>' + "".join(live) + "</div>", unsafe_allow_html=True)
            if s["others"]:
                cards = "".join(
                    f'<div class="pp-card"><div class="votes">{o["votes"]}<small>upvotes</small></div>'
                    f'<div><div class="text">{esc(o["text"])}</div>'
                    f'<div class="meta">{esc(plural(len(o["comments"]), "comment")) if o["comments"] else ""}</div></div></div>'
                    for o in s["others"][:6]
                )
                st.markdown('<h3 style="margin-top:22px">Top Other ideas</h3><div class="pp-grid">' + cards + "</div>", unsafe_allow_html=True)
        else:
            posts = store.visible_posts(data, key)
            real = sum(1 for p in posts if not p.get("seed"))
            st.markdown(f'<div class="pp-count">{plural(real, "post")} · {plural(sum(len(p["votes"]) for p in posts), "vote")} · posting {state}</div>', unsafe_allow_html=True)
            cards = []
            for p in posts[:12]:
                tags = [p.get(f) for f in (("tool", "task") if key == "a" else ("freq",)) if p.get(f)]
                if key == "b" and p.get("minutes"):
                    tags.append(f"{p['minutes']} min")
                if p.get("seed"):
                    tags.append("seed, 13 Aug")
                if p["comments"]:
                    tags.append(plural(len(p["comments"]), "comment"))
                cards.append(
                    f'<div class="pp-card"><div class="votes">{len(p["votes"])}<small>votes</small></div>'
                    f'<div><div class="text">{esc(p["text"])}</div><div class="meta">{esc(" · ".join(tags))}</div></div></div>'
                )
            if cards:
                st.markdown('<div class="pp-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div class="pp-summary">Waiting for the first post…</div>', unsafe_allow_html=True)
        if board.get("summary"):
            st.markdown(summary_html(board["summary"], data.get("ai_themes") if key != "c" else None), unsafe_allow_html=True)

    if qr_col is not None:
        with qr_col:
            if url:
                link = qr.participant_url(url, key, PAGE)
                img = base64.b64encode(qr_png(link, 600)).decode()
                short = link.split("://", 1)[-1]
                st.markdown(
                    f'<div class="pp-qr"><img src="data:image/png;base64,{img}" alt="QR code to join Board {b["letter"]}">'
                    f'<div class="link">{esc(short)}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info("Set the app URL under Settings to show the QR code.")


# =============================================================== main ==
def main():
    qp = st.query_params
    key = (qp.get("board") or "").lower()
    presenting = qp.get("view") == "present"
    title = f"Board {config.BOARDS[key]['letter']} · {config.BOARDS[key]['name']}" if key in config.BOARDS else "PA live boards"
    st.set_page_config(
        page_title=title,
        page_icon="🗳️",
        layout="wide" if presenting else "centered",
        initial_sidebar_state="expanded" if presenting else "collapsed",
    )
    if key not in config.BOARDS:
        render_index()
        return

    cookies = CookieController()
    browser_id = browser_identity(cookies)
    data = store.load()

    if not presenting:
        render_participant(key, data, browser_id)
        return

    token = passcode_token()
    if token and st.session_state.get("cookie_presenter_pending"):
        if safe_cookie_write(cookies, "set", PRESENTER_COOKIE, token, max_age=60 * 60 * 12):
            st.session_state.pop("cookie_presenter_pending")
    authed = token is not None and (
        st.session_state.get("presenter") == token or safe_cookie_get(cookies, PRESENTER_COOKIE) == token
    )
    if authed:
        st.session_state.presenter = token
        render_presenter(key, data, cookies)
    else:
        render_presenter_login()


main()

"""Page chrome for the PA boards: same palette as the SF board (lib/theme.py),
plus the accessibility floor from the handoff: 16px+ text, 44px+ tap
targets, and text colours that pass WCAG AA on the paper background."""
import html

PARTICIPANT_CSS = """
<style>
:root {
  --ink: #1c2b2d; --paper: #f6f2e9; --card: #fffdf7; --line: #d8cfb8;
  --mustard: #c98a2c; --moss: #3f5b49; --rust: #8f4426; --pencil: #545a58;
}
.stApp { background: var(--paper); color: var(--ink); }
html, body, .stApp, .stMarkdown, p, label, input, textarea { font-size: 16px; }
.block-container { padding-left: 16px; padding-right: 16px; max-width: 760px; }
.pa-eyebrow { font-size: 14px; letter-spacing: .1em; text-transform: uppercase; color: var(--rust); font-weight: 700; }
.pa-question { font-family: Georgia, serif; font-size: 26px; line-height: 1.25; font-weight: 700; margin: 4px 0 12px; color: var(--ink); }
.pa-status { font-size: 14px; color: var(--pencil); margin-bottom: 12px; }
.pa-privacy { border-left: 4px solid var(--rust); background: var(--card); padding: 10px 12px; font-size: 16px; line-height: 1.45; margin: 4px 0 10px; color: var(--ink); }
.pa-post { background: var(--card); border: 1.5px solid var(--ink); border-radius: 6px; padding: 14px; margin-top: 14px; color: var(--ink); }
.pa-post .text { font-size: 17px; line-height: 1.45; overflow-wrap: anywhere; }
.pa-post .meta { margin-top: 8px; font-size: 14px; color: var(--pencil); }
.pa-chip { display: inline-block; border: 1px solid var(--pencil); border-radius: 12px; padding: 2px 9px; margin: 6px 6px 0 0; font-size: 14px; color: var(--ink); background: var(--paper); }
.pa-chip.seed { border-color: var(--rust); color: var(--rust); }
.pa-comment { font-size: 16px; line-height: 1.4; padding: 6px 0; border-bottom: 1px solid var(--line); overflow-wrap: anywhere; }
.pa-comment .who { color: var(--pencil); font-size: 14px; }
.pa-empty { color: var(--pencil); font-style: italic; }
.pa-closed { border: 2px solid var(--ink); background: var(--card); border-radius: 6px; padding: 12px 14px; font-size: 16px; }
.pa-bar-row { margin: 10px 0; }
.pa-bar-label { font-size: 16px; margin-bottom: 4px; color: var(--ink); }
.pa-bar-track { background: var(--card); border: 1.5px solid var(--ink); border-radius: 4px; height: 36px; position: relative; overflow: hidden; }
.pa-bar-fill { background: var(--mustard); height: 100%; }
.pa-bar-value { position: absolute; left: 10px; top: 0; line-height: 36px; font-weight: 700; color: var(--ink); font-size: 16px; }
.stButton button, .stDownloadButton button, .stFormSubmitButton button { min-height: 48px; font-size: 16px; }
div[data-testid="stButton"] button[kind="primary"], div[data-testid="stFormSubmitButton"] button[kind="primary"] { background-color: var(--mustard); border-color: var(--ink); color: var(--ink); }
.stSelectbox div[data-baseweb="select"] > div { min-height: 48px; }
</style>
"""

PRESENTER_CSS = PARTICIPANT_CSS + """
<style>
.block-container { max-width: 1840px; padding-top: 24px; }
.pp-question { font-family: Georgia, serif; font-size: 58px; line-height: 1.1; font-weight: 700; color: var(--ink); margin: 0 0 8px; }
.pp-count { font-size: 26px; color: var(--pencil); margin-bottom: 18px; }
.pp-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(380px, 1fr)); gap: 18px; }
.pp-card { background: var(--card); border: 2.5px solid var(--ink); border-radius: 8px; padding: 18px 20px; display: flex; gap: 16px; align-items: flex-start; }
.pp-card .votes { min-width: 84px; text-align: center; font-size: 46px; font-weight: 700; line-height: 1; color: var(--ink); }
.pp-card .votes small { display: block; font-size: 16px; font-weight: 400; color: var(--pencil); margin-top: 4px; }
.pp-card .text { font-size: 27px; line-height: 1.3; color: var(--ink); overflow-wrap: anywhere; }
.pp-card .meta { font-size: 18px; color: var(--pencil); margin-top: 8px; }
.pp-qr { background: #fff; border: 2.5px solid var(--ink); border-radius: 8px; padding: 18px; text-align: center; }
.pp-qr img { width: 100%; max-width: 420px; }
.pp-qr .link { font-size: 24px; font-weight: 700; word-break: break-all; color: var(--ink); }
.pp-summary { background: var(--card); border: 2.5px solid var(--ink); border-radius: 8px; padding: 22px 26px; font-size: 22px; line-height: 1.45; color: var(--ink); margin-top: 22px; }
.pp-summary h3 { font-family: Georgia, serif; font-size: 30px; margin: 0 0 10px; }
.pp-summary h4 { font-size: 22px; margin: 16px 0 6px; color: var(--moss); }
.pp-summary .note { font-size: 17px; color: var(--pencil); }
.pp-bars .pa-bar-label { font-size: 30px; }
.pp-bars .pa-bar-track { height: 64px; }
.pp-bars .pa-bar-value { line-height: 64px; font-size: 28px; }
</style>
"""


def esc(s) -> str:
    return html.escape("" if s is None else str(s))


def inject(st, presenter: bool = False):
    st.markdown(PRESENTER_CSS if presenter else PARTICIPANT_CSS, unsafe_allow_html=True)


def bars_html(options: list[dict], css_class: str = "") -> str:
    """Horizontal bars with the count and percentage written on each bar,
    so the reading never depends on colour."""
    top = max((o["votes"] for o in options), default=0) or 1
    rows = []
    for o in options:
        width = 100 * o["votes"] / top
        votes = "vote" if o["votes"] == 1 else "votes"
        rows.append(
            f'<div class="pa-bar-row"><div class="pa-bar-label">{esc(o["label"])}</div>'
            f'<div class="pa-bar-track"><div class="pa-bar-fill" style="width:{width:.1f}%"></div>'
            f'<div class="pa-bar-value">{o["votes"]} {votes} · {o["pct"]:.0f}%</div></div></div>'
        )
    return f'<div class="{css_class}">' + "".join(rows) + "</div>"

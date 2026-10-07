"""Shared page chrome (CSS + a couple of tiny helpers) so the live board
and both N = Everyone pages look like one product, even though Streamlit
multi-page apps don't share injected CSS across pages automatically."""
import html

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
.quality-flag { display: inline-block; background: #fbe9df; border: 1px solid var(--rust); color: var(--rust); border-radius: 10px; padding: 2px 9px; font-size: 10px; text-transform: uppercase; letter-spacing: .04em; margin-left: 6px; }
div[data-testid="stButton"] button[kind="primary"] { background-color: var(--mustard); border-color: var(--ink); color: var(--ink); }
div[data-testid="stDownloadButton"] button[kind="primary"] { background-color: var(--mustard); border-color: var(--ink); color: var(--ink); }
.join-count { font-family: Georgia, serif; font-size: 22px !important; }
.warn-box { border: 1.5px solid var(--rust); background: #fbe9df; color: var(--rust); border-radius: 6px; padding: 10px 12px; font-size: 12.5px; font-weight: 700; line-height: 1.45; margin: 4px 0 12px; }
.stat-row { display: flex; gap: 8px; margin-top: 6px; }
.stat { flex: 1; border: 1.5px solid var(--ink); border-radius: 4px; padding: 8px 6px; text-align: center; background: var(--paper); }
.stat .num { font-family: Georgia, serif; font-size: 24px; font-weight: 700; line-height: 1.1; color: var(--ink); }
.stat .lbl { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; color: var(--pencil); }
.stat-good { border-color: var(--moss); } .stat-good .num { color: var(--moss); }
.stat-mixed { border-color: var(--mustard); } .stat-mixed .num { color: var(--mustard); }
.stat-bad { border-color: var(--rust); } .stat-bad .num { color: var(--rust); }
.barrier-rank { margin: 6px 0 0; padding-left: 0; list-style: none; font-size: 13px; color: var(--ink); }
.barrier-rank li { padding: 4px 0; border-bottom: 1px dashed var(--line); }
.barrier-rank li:last-child { border-bottom: none; }
.barrier-rank .cnt { display: inline-block; min-width: 26px; font-weight: 700; color: var(--rust); }
.ai-entry .ai-task { font-family: Georgia, serif; font-size: 15px; font-weight: 700; margin-bottom: 6px; }
.ai-entry .ai-line { font-size: 12.5px; margin-top: 4px; }
.chips { margin-bottom: 4px; }
.chip { display: inline-block; font-size: 9.5px; text-transform: uppercase; letter-spacing: .04em; font-weight: 700; border: 1px solid var(--pencil); color: var(--pencil); border-radius: 10px; padding: 1px 8px; margin: 0 4px 4px 0; }
.chip-good { border-color: var(--moss); color: var(--moss); }
.chip-mixed { border-color: var(--mustard); color: #8a5d16; }
.chip-bad { border-color: var(--rust); color: var(--rust); }
</style>
"""


def inject():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def hide_sidebar():
    """Hides the sidebar and its page links (survey, results) entirely."""
    import streamlit as st
    st.markdown(
        '<style>[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], '
        '[data-testid="stSidebarNav"], [data-testid="collapsedControl"] { display: none !important; }</style>',
        unsafe_allow_html=True,
    )


def esc(s: str) -> str:
    return html.escape(s or "")


def header(eyebrow: str, title: str):
    import streamlit as st
    st.markdown(f'<div class="board-eyebrow">{esc(eyebrow)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="board-title">{esc(title)}</div>', unsafe_allow_html=True)

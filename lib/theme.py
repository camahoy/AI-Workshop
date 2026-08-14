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
</style>
"""


def inject():
    import streamlit as st
    st.markdown(CSS, unsafe_allow_html=True)


def esc(s: str) -> str:
    return html.escape(s or "")


def header(eyebrow: str, title: str):
    import streamlit as st
    st.markdown(f'<div class="board-eyebrow">{esc(eyebrow)}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="board-title">{esc(title)}</div>', unsafe_allow_html=True)

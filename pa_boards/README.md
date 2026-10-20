# PA live boards: US Public Affairs AI session

Three live boards (A: How we use AI, B: Time drains, C: What's next) that
people open from a QR code. Each board has a phone-first participant view,
a 1920×1080 presenter view and a rule-based summary. See
[FACILITATOR_GUIDE.md](FACILITATOR_GUIDE.md) for running the session.

This is a **separate Streamlit app** from the SF working-session board in
the repo root. It has its own entry point (`pa_boards/app.py`), storage,
secrets and URL, and shares nothing with `app.py` or the N = Everyone
survey.

## Deploy (Streamlit Community Cloud)
1. On share.streamlit.io, choose **Create app**, pick this repo and branch, and set the main file path to `pa_boards/app.py`.
   Streamlit installs `pa_boards/requirements.txt` and uses the repo's `.streamlit/config.toml` theme.
2. Under **Settings → Secrets**, paste from `secrets.toml.example`. At minimum, set `PRESENTER_PASSCODE`.
3. Deploy, open `…/?board=a&view=present`, unlock, and set the session date under Settings.

## Run locally
```bash
pip install -r pa_boards/requirements.txt
echo 'PRESENTER_PASSCODE = "test"' > .streamlit/secrets.toml   # gitignored
streamlit run pa_boards/app.py
```

## Tests
```bash
pip install pytest playwright
python -m pytest pa_boards/tests                                  # rules, summary, export, 40-thread load
streamlit run pa_boards/app.py --server.port 8600 &               # with PRESENTER_PASSCODE set
python pa_boards/tests/browser_check.py http://localhost:8600 <passcode> /tmp/shots   # phone + projector flow
python pa_boards/tests/load_check.py   http://localhost:8600 <passcode> 40          # 40 real browsers
```
Set `CHROMIUM_PATH` if Playwright should use an already-installed Chromium.

### Load test result (40 real browsers, one 4-core test box, 2026-10-20)
- **Passed:**
  - Every post was saved (40 participants + markers + 6 seeds), and no vote was ever doubled.
  - The projector stayed under 2 s behind (measured 0.01–1.8 s across runs).
  - The 40-thread data-layer test passes in under 10 s.
- **Not passed:** when all 40 browsers tap at the same moment, the single Streamlit process (one CPU core) falls behind. Server response times reached 5–20 s and most scripted votes weren't confirmed within the test window.
- **What changed because of this:**
  - Taps and form submissions are saved in `on_click` callbacks, so a second tap can't cancel the first.
  - Phones redraw every 30 s instead of every few seconds.
  - Phones show the top 15 posts by default.
- Streamlit Community Cloud gives about the same single core, so expect the same limit there.

## Data
- One JSON file: `pa_boards/data/pa_boards.json` (gitignored). It holds post text, optional tags and name, timestamps, votes and comments as random browser ids, and nothing else. No emails, and the app logs no IPs.
- **Delete all data** removes the file. It is also deleted automatically N days (default 30) after the session date.
- Streamlit Community Cloud's disk does not survive a reboot or redeploy, so export right after the session. Don't push to this branch while a session is running.

## Summary
- **Rule-based (always on):** totals; top 5 by votes; Board A counts by tool and task type; Board B hours per month, estimated as occurrences per month (Daily 21, Weekly 4.3, Monthly 1, Quarterly ⅓) × minutes ÷ 60 × (upvoters + poster), and labelled "estimate".
- **AI themes (off):** `palib/ai_summary.py` calls an Azure OpenAI deployment only when `AI_SUMMARY_PROVIDER = "azure_openai"` plus its endpoint, deployment and key are in Secrets **and** the presenter switches it on.
  - The model receives post ids and text only, never names, and returns groupings of ids.
  - Theme counts and vote totals are computed in code, and quotes are the original post text looked up by id.

## Layout
```
pa_boards/
  app.py               routing, participant + presenter views
  palib/config.py      board questions, dropdown options, Board C options, seeds
  palib/store.py       shared JSON store, votes/comments/moderation/retention
  palib/summary.py     rule-based summaries
  palib/ai_summary.py  optional AI themes (off by default)
  palib/export.py      CSV + zip export (Excel-safe)
  palib/qr.py          1200×1200 QR PNGs
  palib/ui.py          CSS (16px+ text, 48px tap targets)
  tests/               pytest suite, browser_check.py, load_check.py
```

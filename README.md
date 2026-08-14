# Field Notes: AI Working Session — Live Board + N = Everyone Survey

A two-part Streamlit app:

1. **The live board** (`app.py`) — a live, cross-level, cross-division
   working-session tool. Participants join on their phones under a service
   line and title — never a name — post to a shared research wall, place
   tasks on a meaning/delegation map, and surface bottlenecks, all updating
   live across devices, all agree-able rather than voted on. The
   facilitator can trigger a Claude-generated closing synthesis that
   streams onto a shared screen.
2. **N = Everyone** (`pages/1_N_Everyone_Survey.py`) — a real, standalone,
   anonymous survey app for the whole company (not just workshop
   attendees), with its own gated results/tabulation page
   (`pages/2_Survey_Results.py`). It's a separate flow with its own
   persistent storage — see "How the two parts relate" below.

## Part 1: the live board

### Identity model

No name is ever collected. Joining asks only for **Service Line /
Division** (free text), **Title** (free text), and **Level** (used only
for segmentation/reporting — never shown on posts, and never used to form
groups; there are no breakout groups). Every post anywhere in the app is
tagged `{Service Line} · {Title}`, never a name or device id. Individual
per-person tracking (who already agreed with what, who already joined) is
stored privately per device; only aggregate counts are shared.

### Screens

1. **Join** — Service Line, Title, Level. Joining auto-advances to the next
   screen. A facilitator-only "Reset board" control sits at the bottom:
   click once to arm it, then click again within 5 seconds to confirm —
   otherwise it auto-disarms. Confirming clears all posts, agree counts,
   and the roster for this session only.
2. **Good Research** — one fixed prompt, sticky-note wall, tagged posts,
   each with an Agree toggle and live count (one agree per person per
   note — a shared-sentiment signal, not a ranking).
3. **Meaning & Delegation Map** — a true scatter plot (x = non-delegable →
   delegable, y = not meaningful → meaningful): click the exact spot to
   name a task, plus a 17-item task bank of chips that prefill the note
   field. Placed tasks are color-coded by quadrant and agree-able.
4. **Bottleneck Bank** — starts completely empty ("No bottlenecks posted
   yet, be the first."), fills with unlimited participant-submitted ones,
   each agree-able (no vote budget, no cap).
5. **N = Everyone** — a standing reference screen, available throughout the
   session (not part of the sequential flow). Explains what the survey is
   and links out to the real survey app (Part 2) — it does not embed the
   survey itself.
6. **Closing** — only a facilitator-only streamed Claude synthesis of the
   entire board (Good Research, Meaning & Delegation Map, Bottleneck Bank),
   for projecting as the session's closing moment. No participant composer
   on this screen, and no survey data feeds into this particular synthesis
   — the survey has its own separate results/synthesis view (Part 2).

A "last updated Xs ago" indicator in the header reflects the most recent
activity across the whole session.

### How sessions work

Data is namespaced by a session code passed as `?session=CODE` in the URL.
Multiple concurrent sessions (different cities/cohorts) never see each
other's data.

- **Facilitator**: open the app's base URL with no `?session=` param. You'll
  land on a setup screen to create a session code (e.g. `SF-01`) — if
  `FACILITATOR_PASSWORD` is set in secrets, you'll need it here. Starting a
  session unlocks a sidebar with the join link/QR code, plus a "Reset board"
  control at the bottom of the Join screen (arm with one click, confirm with
  a second click within 5 seconds, or it auto-disarms). Facilitator status is
  stored as a browser cookie, so it survives refreshes on that device.
- **Co-facilitators / a different device**: on any screen inside a session,
  open "🔒 Facilitator login" (bottom of the sidebar) and enter the
  password to unlock the same controls on that browser too.
- **Participants**: never see or type the session code — they just scan the
  QR code (or open the join link) the facilitator shares, which already has
  `?session=CODE` baked in. They never see a facilitator login either.

## Part 2: N = Everyone survey

A real, functioning, standalone survey — every question in
`questionnaire/AI-Perceptions-Questionnaire-Draft.docx` is a live form
input (open text, radios, multi-selects, matrix grids, an approximate
MaxDiff exercise), not a static list. No login required; anyone with the
link can respond. Meant to run as its own ~2-week field window across the
whole company, independent of any single live-board session.

### Flow

`pages/1_N_Everyone_Survey.py` is a 6-step wizard:

1. Section A (classification) + Section B (current AI usage — B1 tool
   multi-select, B2 frequency grid, B3/B3a–c conditional on "Yes", B4)
2. Section C (per-tool effectiveness grid, C2, C3) + D1 (task filter)
3. D1a — a matrix grid, but **only for the tasks you picked at D1**,
   capped at 8 rows (randomly sampled if you picked more) + D2, D3
4. Section E (trust and readiness)
5. Section F (org voice, F3, and F4 — the investment-priority exercise)
6. Section G (closing) + submit

Each submission is a new row in SQLite — no edit-in-place, no per-device
identity. A `st.session_state` flag blocks a second submission within the
same browser session (reload the page to submit again) — deliberately not
over-engineered, per the spec.

### Two flagged simplifications

Both are called out again on the results page itself:

- **F4 (investment priority)** is not a true balanced-incomplete-block
  MaxDiff design. With only 5 priority items there are exactly 5 unique
  4-item subsets (each leaving one out), so `generate_maxdiff_sets()` in
  `lib/survey.py` just shows all 5 leave-one-out subsets, shuffled —
  giving every item balanced exposure for free. Scoring is the standard
  lightweight approximation: (times chosen best − times chosen worst) /
  times shown, per item. Good enough to rank priorities, not to defend a
  precise statistical score.
- **D1a is capped at 8 rows** per respondent to keep a self-administered
  mobile form from running too long, even if more tasks were selected at
  D1.

### Results page

`pages/2_Survey_Results.py`, gated by `SURVEY_RESULTS_PASSWORD` (a
different secret than the live board's facilitator password — this page
is for whoever's running the initiative, not respondents). Shows:

- Tabulated results for every closed-ended question: attitude averages,
  tool usage and per-tool B2/C1 grids, D1 task time and the D1a
  could-AI/meaningfulness breakdown, and MaxDiff best-minus-worst scores
- A service-line breakdown, rolling any service line below a configurable
  minimum N into "Other" rather than showing an unreliable small-sample
  number
- **Every open-ended response, listed in full and grouped by question**
  (C2, D2, D3, E5, F3, G1) — unattributed, matching the questionnaire's
  own stricter anonymity model (individual answers are never shown
  attributed to a service line/title, unlike the live board's tagged
  posts)
- A "Generate synthesis" button that streams a Claude-written summary
  structured around: usage/effectiveness patterns, where people want AI
  most vs. least, trust/readiness signals, the MaxDiff priority ranking,
  and open-ended themes

### Data quality flags

Recorded per response, never used to block submission or auto-exclude:

- **Time to complete** — wall-clock time from starting the wizard to
  submitting
- **Straightlining** — flagged if a respondent gave the identical
  "could AI take this on" answer for every row of D1a
- Open-ended fields under 15 characters get a gentle inline nudge
  ("could you add a bit more detail?") — never a hard block

## How the two parts relate

They're two independent flows in one deployment, not one continuous
session:

- The live board's per-session data (`data/<CODE>.json`) is ephemeral by
  design — reset between workshops, fine to lose on redeploy.
- The survey's responses (`data/survey_responses.db`, SQLite) are meant to
  outlive any single workshop and survive the full field window
  independently — they're never cleared by the live board's "Reset board"
  control, and the live board's closing synthesis doesn't read them (the
  survey has its own separate results/synthesis view).
- The live board's "N = Everyone" tab is just a signpost pointing at the
  survey (`st.page_link`) — it doesn't share identity, session code, or
  any state with it.

## Local development

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and add your real ANTHROPIC_API_KEY
streamlit run app.py
```

This is a multi-page Streamlit app — `streamlit run app.py` serves the
live board plus both `pages/*.py` files automatically (Streamlit
auto-discovers `pages/`). `.streamlit/secrets.toml` is gitignored — it
never gets committed.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (private is fine).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at this repo, branch, and `app.py` as the main file — the
   `pages/` directory is picked up automatically.
3. In the app's **Settings → Secrets**, paste:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-real-key"
   FACILITATOR_PASSWORD = "choose-a-password"
   SURVEY_RESULTS_PASSWORD = "choose-a-different-password"
   APP_BASE_URL = "https://your-app-name.streamlit.app"
   ```

   `FACILITATOR_PASSWORD` is strongly recommended — without it, anyone who
   opens the app's base URL can start sessions and unlock facilitator
   controls. `SURVEY_RESULTS_PASSWORD` is equally recommended — without it,
   anyone with the results page's URL can read every open-ended response.
   `APP_BASE_URL` is optional — it just prefills the QR/join-link field in
   the facilitator sidebar.

   If either closing/results synthesis ever fails, the error shown in the
   UI will say why (most commonly: `ANTHROPIC_API_KEY` missing or invalid).

4. Deploy. The live board is stateless/file-backed and fine to let sleep
   between sessions. The survey's SQLite file persists on the same disk —
   fine for Streamlit Community Cloud's single-process deployment, but
   note that Streamlit Cloud's disk is **not guaranteed to survive a
   redeploy**; if you need the survey data to survive a redeploy mid-field-
   window, export it (`lib/survey_db.all_responses()`) before redeploying,
   or point `lib/survey_db.DB_PATH` at a mounted persistent volume if your
   hosting target provides one.

## Data & storage notes

- Live board updates use polling (every 4 seconds), not websockets.
- Board data is stored as JSON files under `data/`, one per session code —
  ephemeral by design, fine to lose on redeploy.
- Survey responses are stored in `data/survey_responses.db` (SQLite, WAL
  mode) — meant to persist through a full field window, gitignored like
  the rest of `data/`.
- Anonymous by design: no name is ever collected anywhere in either part.
  The live board tags posts with Service Line · Title; the survey is
  stricter still — individual responses are never displayed anywhere in
  the UI, not even tagged, only aggregate stats and unattributed open-text
  excerpts.
- The `ANTHROPIC_API_KEY` is read server-side via `st.secrets` and is never
  sent to the browser.
- Each live-board device's identity (used to cap one agree per person per
  item) lives in a browser cookie (`workshop_device_id`, ~30 day expiry)
  rather than the URL, so it can't leak between devices via a copied/
  forwarded link. The survey has no such identity — no login, no cookie,
  just a per-browser-session flag against resubmission.

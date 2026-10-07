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

### Sessions and per-session settings

Data is namespaced by a session code passed as `?session=CODE` in the URL.
Every session is its own row in the database, so sessions never see each
other's data (SF-01 and PA-01 never mix), and every read, write, export and
reset is scoped to the one session.

Each session also stores its own **settings** (`lib/sessions.py`): which
tabs show, what Join asks, whether posts carry an identity tag, and whether
the summary is on. A new session starts from a template, picked on the
setup screen:

| Template | Tabs | Join asks | Posts show | Summary |
|---|---|---|---|---|
| **Field Notes workshop** (SF-01 style) | Join, Good Research, Meaning & Delegation, Bottleneck Bank, N = Everyone, Closing | Service Line, Title, Level | `Service Line · Title` tag | On (Closing tab) |
| **Team pulse** (PA-01 style) | Join, Friction Points, AI in Our Work | Level only | No identity at all | Off by default |

`SF-01` and `PA-01` are pinned to those templates. Any other code (e.g. `PA-02`,
`NYC-03`) gets whichever template the facilitator picks, with no code changes.
After starting, the facilitator can change that session's tabs and switch the
summary on or off from **⚙️ Session settings** in the sidebar. Sessions created
before per-session settings existed behave exactly as they did (workshop template).

### Identity and anonymity

No name is ever collected in any session.

- **Workshop sessions** (SF-01): Join asks Service Line, Title and Level; every
  post is tagged `{Service Line} · {Title}`. Level is used only for reporting.
- **Team pulse sessions** (PA-01): Join asks Level only, and the Join screen shows
  a count of people who've joined instead of a roster. No post or AI-log entry
  shows any identity. Level is stored privately with each post and appears only
  in the CSV export, never on screen (the facilitator's raw-data viewer is
  hidden for these sessions, and Level is never sent to the summary).

Who agreed with what is stored privately per device; only counts are shown.

### Screens

- **Join**: see above. Joining auto-advances to the next tab.
- **Good Research**: one fixed prompt, sticky-note wall, each note with an Agree
  toggle and live count (one agree per person per note, a shared-sentiment
  signal, not a ranking).
- **Meaning & Delegation Map**: a scatter plot (delegable × meaningful); click
  a spot to name a task, or tap one of 17 task-bank chips to prefill it.
- **Bottleneck Bank / Friction Points**: the same agree-able wall with
  different wording per template. Friction Points (PA-01) asks "Think of a
  task you do regularly. Where does time or effort get lost?" and never
  mentions AI. Both start empty.
- **AI in Our Work** (PA-01): one entry is one experience. Fields: Task
  (required), Tool used, How you used it, Outcome (required: Worked well /
  Partly / Didn't work), What worked, What didn't, Biggest barrier (required;
  choosing "Other" shows an optional text box), Rough time saved or lost
  (optional), and a required confirmation that no client-identifiable or
  confidential data was entered. There's a warning above the form, and no
  link or attachment field. The top of the tab shows a live summary (entries
  by outcome, barriers ranked by count). Entries show as cards, newest first,
  with Outcome and Barrier labels, a "Same for me" toggle with a count (one
  per person per entry), and filters for Outcome and Barrier.
- **N = Everyone**: a signpost to the survey (Part 2).
- **Closing**: the facilitator-only streamed Claude synthesis of the board.

A "last updated Xs ago" indicator reflects the most recent activity, and every
screen polls for updates every 4 seconds.

### Facilitator access

Facilitator controls (Export, Reset board, Summary, session settings, join
link/QR) appear only after entering the passphrase set as
`FACILITATOR_PASSWORD` in Streamlit secrets. There is no URL flag, and
participant links never show a login box or any control.

- **Facilitator**: open the app's base URL with no `?session=`. Enter a session
  code, pick a template if it's a new code, enter the passphrase, and press
  **Start or reopen session**. The same screen reopens an existing session,
  which is how a co-facilitator on another device gets in.
- The browser remembers the login for a day with a signed cookie (an HMAC of
  the passphrase), so it can't be forged by hand, and changing the
  passphrase logs every device out.
- If `FACILITATOR_PASSWORD` isn't set, no one can get facilitator controls.

**Export**: "⬇️ Export all boards (CSV)" is in the sidebar on every tab and
also in the Facilitator block on the Join tab. It downloads a zip with one
CSV per board for the current session (plus a Participants file), any time.
Individual CSVs are under "Download one board at a time". Columns use plain
names with no spaces, ready for a SharePoint List import:

- `AILog.csv`: Task, Tool, HowUsed, Outcome, WhatWorked, WhatDidnt, Barrier,
  BarrierOther, TimeImpact, SameForMeCount, Level, Created
- `FrictionPoints.csv`: Post, AgreeCount, Level, Created
- Workshop boards: `GoodResearch.csv` and `BottleneckBank.csv` (Post, Tag,
  AgreeCount, Level, Created) and `MeaningDelegation.csv` (Task, X, Y,
  Quadrant, Tag, AgreeCount, Level, Created)
- `Participants.csv`: Level, Joined (pulse) or ServiceLine, Title, Level,
  Joined (workshop)

`Created` and `Joined` are UTC ISO 8601. Posts made before this change have
no Level or Created value. Files are UTF-8 with a BOM, so Excel shows
accents correctly.

**Reset board** (Join tab, facilitator only): click once to arm it, then
again within 5 seconds to confirm. It clears posts, agrees, roster and summary
for the current session only, keeps the session's settings, and first saves a
full copy to the `board_archive` table, so a mistaken reset can be recovered.

**Summary**: for workshop sessions, it's in the Closing tab, as before. For
sessions without a Closing tab (PA-01), it appears in the Join tab's
Facilitator block, but only when switched on in Session settings. It's off by
default for PA-01. The PA-01 summary uses its own system prompt (in
`lib/claude_summary.py`): friction themes with post and agree counts, then
outcome counts, ranked barriers, and what worked and what didn't by task type.
It makes no recommendations.

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
is for whoever's running the initiative, not respondents). If that secret
isn't set, the page stays locked. Shows:

- An "⬇️ Export all responses (CSV)" button: one row per response, with
  grid and MaxDiff answers kept as JSON text in their columns

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

They're two independent flows in one deployment that share one durable
database (separate tables):

- Board sessions live in `board_sessions` (one row per session code), with
  reset snapshots in `board_archive`.
- Survey responses live in `survey_responses`. They're never cleared by the
  live board's "Reset board" control, and the live board's closing synthesis
  doesn't read them.
- The live board's "N = Everyone" tab is just a signpost pointing at the
  survey (`st.page_link`); it doesn't share identity, session code, or any
  state with it. In sessions that hide that tab (PA-01), participants don't
  see the sidebar at all, so the survey and results pages aren't linked.

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
   DATABASE_URL = "postgresql://postgres.xxxx:db-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
   ANTHROPIC_API_KEY = "sk-ant-your-real-key"
   FACILITATOR_PASSWORD = "choose-a-passphrase"
   SURVEY_RESULTS_PASSWORD = "choose-a-different-password"
   APP_BASE_URL = "https://your-app-name.streamlit.app"
   SHEETS_WEBHOOK_URL = "https://script.google.com/macros/s/XXXXXXXX/exec"
   ```

   `DATABASE_URL` is required for anything you want to keep (see "Durable
   storage" below). `FACILITATOR_PASSWORD` is required for any facilitator
   control. `SURVEY_RESULTS_PASSWORD` is required to open the survey results
   page. `APP_BASE_URL` is optional; it prefills the QR/join-link field.
   `SHEETS_WEBHOOK_URL` is an optional extra off-site copy of survey
   responses.

   If a summary ever fails, the error shown in the UI says why (most
   commonly: `ANTHROPIC_API_KEY` missing or invalid).

4. Deploy, then open the base URL. The facilitator sidebar should say
   "✓ Saved to the durable database". If it shows a red "Storage is NOT
   durable" warning, `DATABASE_URL` isn't set.

### Durable storage (`DATABASE_URL`)

Streamlit Community Cloud doesn't keep local files across app restarts,
sleeps or redeploys. The board used to store each session in
`data/<CODE>.json` on that disk, which is how SF-01's posts were lost. All
board and survey data now goes to a hosted Postgres database.

Setup with Supabase (free tier, about 5 minutes):

1. Create a project at supabase.com and set a database password.
2. Click **Connect** (top of the project page) and copy the **Transaction
   pooler** connection string (port 6543). Replace `[YOUR-PASSWORD]` with
   your database password.
3. Paste it into Streamlit secrets as `DATABASE_URL` and reboot the app. The
   tables are created automatically on first run.

To see the data directly, open Supabase → **Table Editor**:
`board_sessions` (one row per session; the `data` column holds everything),
`board_archive` (copies taken before each reset), `survey_responses`. Any
Postgres host works (Neon, Railway, RDS, etc.). Supabase also takes daily
backups on its side.

On startup, the app also imports anything still sitting in the old local
files (`data/*.json`, `data/survey_responses.db`) if the container still has
them, without overwriting newer data. Without `DATABASE_URL` (local
development), data goes to `data/app.db`, which is fine on your own machine
but not durable on Streamlit Cloud.

### Backing up survey responses to Google Sheets (`SHEETS_WEBHOOK_URL`)

Every N = Everyone submission is also POSTed to this URL if it's set
(`lib/sheets_backup.py`) — a redundant copy that lives on Google's
infrastructure, completely independent of this app's container. It's
best-effort and non-blocking: if the webhook is unset, slow, or down, the
submission still saves normally to SQLite; the respondent just doesn't
see the "backed up" confirmation.

Setup (about 3 minutes, no Google Cloud project or service account
needed):

1. Create a new Google Sheet (sheets.new).
2. **Extensions → Apps Script**, replace the placeholder with:

   ```javascript
   function doPost(e) {
     var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
     var payload = JSON.parse(e.postData.contents);

     var flat = {};
     for (var key in payload) {
       var val = payload[key];
       flat[key] = (typeof val === 'object' && val !== null) ? JSON.stringify(val) : val;
     }
     flat['_received_at'] = new Date().toISOString();

     var headerRow = sheet.getRange(1, 1, 1, Math.max(sheet.getLastColumn(), 1)).getValues()[0];
     var headers = headerRow.filter(function(h) { return h !== ""; });

     for (var k in flat) {
       if (headers.indexOf(k) === -1) {
         headers.push(k);
         sheet.getRange(1, headers.length).setValue(k);
       }
     }

     var row = headers.map(function(h) { return (h in flat) ? flat[h] : ""; });
     sheet.appendRow(row);

     return ContentService.createTextOutput(JSON.stringify({status: "ok"})).setMimeType(ContentService.MimeType.JSON);
   }
   ```

   This dynamically adds a column for any new field it sees, so it
   doesn't need updating if the survey's questions change later.

3. **Deploy → New deployment → type "Web app"**. Set **Execute as: Me**,
   **Who has access: Anyone**. Deploy, authorize with your Google account,
   copy the resulting URL (ends in `/exec`).
4. Paste that URL into Streamlit secrets as `SHEETS_WEBHOOK_URL`.

## Data & storage notes

- Live board updates use polling (every 4 seconds), not websockets.
- Board and survey data are stored durably in Postgres via `DATABASE_URL`
  (`lib/db.py`). Writes are atomic per session, so simultaneous posts and
  agrees never overwrite each other.
- Survey responses are also POSTed to `SHEETS_WEBHOOK_URL` if configured, as
  an extra off-site copy.
- No name is ever collected anywhere. See "Identity and anonymity" above for
  what each session type shows.
- The `ANTHROPIC_API_KEY` and `DATABASE_URL` are read server-side via
  `st.secrets` and never sent to the browser.
- Each live-board device's identity (used to cap one agree / "same for me" per
  person per item) lives in a browser cookie (`workshop_device_id`, ~30 day
  expiry), not the URL, so it can't leak between devices via a forwarded link.

---

## ORBOU (`orbou/`)

A separate project in this repo: ORBOU, a personal "living brief" app (Expo + Expo Router, deployed as a PWA on Vercel). It has nothing to do with the workshop app above. See [`orbou/README.md`](orbou/README.md).

# Field Notes: AI Working Session — Live Board

A live, cross-level, cross-division working-session tool built with
Streamlit. Participants join on their phones under a service line and
title — never a name — post to a shared research wall, place tasks on a
meaning/delegation map, surface bottlenecks, and submit closing asks, all
updating live across devices, all agree-able rather than voted on. The
facilitator can trigger a Claude-generated closing synthesis that streams
onto a shared screen.

## Identity model

No name is ever collected. Joining asks only for **Service Line /
Division** (free text), **Title** (free text), and **Level** (used only to
balance breakout groups — never shown on posts). Every post anywhere in
the app is tagged `{Service Line} · {Title}`, never a name or device id.
Individual per-person tracking (who already agreed with what, who already
joined) is stored privately per device; only aggregate counts are shared.

## Screens

1. **Join & Groups** — Service Line, Title, Level. Joining auto-advances to
   the next screen. Mixed-level breakout groups, bucketed by level and
   round-robined across tables.
2. **Good Research** — one fixed prompt, sticky-note wall, tagged posts,
   each with an Agree toggle and live count (one agree per person per
   note — a shared-sentiment signal, not a ranking).
3. **Meaning & Delegation Map** — a true scatter plot (x = non-delegable →
   delegable, y = meaningful → meaningless): click the exact spot to name
   a task, plus a 17-item task bank of chips that prefill the note field.
   Placed tasks are color-coded by quadrant and agree-able.
4. **Bottleneck Bank** — 8 seeded starter bottlenecks plus unlimited
   participant-submitted ones, each agree-able (no vote budget, no cap).
5. **Closing** — a "what should leadership fund" wall (same agree
   mechanic), plus a facilitator-only streamed Claude synthesis of the
   entire board for projecting as the session's closing moment.

A "last updated Xs ago" indicator in the header reflects the most recent
activity across the whole session.

## How sessions work

Data is namespaced by a session code passed as `?session=CODE` in the URL.
Multiple concurrent sessions (different cities/cohorts) never see each
other's data.

- **Facilitator**: open the app's base URL with no `?session=` param. You'll
  land on a setup screen to create a session code (e.g. `SF-01`) — if
  `FACILITATOR_PASSWORD` is set in secrets, you'll need it here. Starting a
  session unlocks a sidebar with the join link/QR code, group-size control,
  and a reset-board control (clears everything back to a fresh state).
  Facilitator status is stored as a browser cookie, so it survives
  refreshes on that device.
- **Co-facilitators / a different device**: on any screen inside a session,
  open "🔒 Facilitator login" (bottom of the sidebar) and enter the
  password to unlock the same controls on that browser too.
- **Participants**: never see or type the session code — they just scan the
  QR code (or open the join link) the facilitator shares, which already has
  `?session=CODE` baked in. They never see a facilitator login either.

## Local development

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edit .streamlit/secrets.toml and add your real ANTHROPIC_API_KEY
streamlit run app.py
```

`.streamlit/secrets.toml` is gitignored — it never gets committed.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (private is fine).
2. On [share.streamlit.io](https://share.streamlit.io), create a new app
   pointing at this repo, branch, and `app.py`.
3. In the app's **Settings → Secrets**, paste:

   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-real-key"
   FACILITATOR_PASSWORD = "choose-a-password"
   APP_BASE_URL = "https://your-app-name.streamlit.app"
   ```

   `FACILITATOR_PASSWORD` is strongly recommended — without it, anyone who
   opens the app's base URL can start sessions and unlock facilitator
   controls. `APP_BASE_URL` is optional — it just prefills the QR/join-link
   field in the facilitator sidebar; you can also paste the URL in manually
   after deploying, once you know it.

   If the closing summary ever fails, the error shown in the Closing tab
   will say why (most commonly: `ANTHROPIC_API_KEY` missing or invalid) —
   check that secret first.

4. Deploy. The app is stateless/file-backed and fine to let sleep between
   sessions — no need to keep it warm.

## Data & storage notes

- Live updates use polling (every 4 seconds), not websockets.
- Board data is stored as JSON files under `data/`, one per session code.
  This is fine for Streamlit Community Cloud's single-process deployment,
  but data does **not** survive a redeploy or app restart — that's expected
  for a tool meant to be reset between sessions.
- Anonymous by design: no name is ever collected, only Service Line, Title,
  and Level. Posts are tagged with Service Line · Title; individual
  agree/join tracking is private per device, only aggregate counts are
  shared.
- The `ANTHROPIC_API_KEY` is read server-side via `st.secrets` and is never
  sent to the browser.
- Each device's identity (used to cap one agree per person per item) lives
  in a browser cookie (`workshop_device_id`, ~30 day expiry) rather than
  the URL, so it can't leak between devices via a copied/forwarded link.

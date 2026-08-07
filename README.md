# Field Notes: AI Optimization Workshop — Live Board

A live, cross-level workshop tool built with Streamlit. Participants join
on their phones, post to a shared research wall, map tasks on an agency
grid, dot-vote on ideas, and answer an anonymous closing pulse — all
updating live across devices. The facilitator can trigger a Claude-generated
closing synthesis that streams onto a shared screen.

## Screens

1. **Join & Groups** — name + level (8 distinct levels), live roster, mixed-level
   breakout groups. Joining auto-advances straight to the next screen.
2. **Good Research** — anonymous sticky-note wall
3. **Agency Map** — a true scatter plot (not quadrant buttons): click the exact
   spot on the grid, name the task, it lands at that precise x/y, color-coded
   by quadrant, live for everyone
4. **Dot Vote** — 8 pre-seeded ideas plus participant-submitted ideas, 3 votes
   per person across all of them
5. **Closing Pulse** — four anonymous questions: two yes/somewhat/no, a 1–5
   ease-of-integration slider with a live room average, and a trust question
6. **Summary** — facilitator-triggered, streamed synthesis from Claude

A "last updated Xs ago" indicator in the header reflects the most recent
activity across any screen in the session.

## How sessions work

Data is namespaced by a session code passed as `?session=CODE` in the URL.
Multiple concurrent workshops (different cities/cohorts) never see each
other's data.

- **Facilitator**: open the app's base URL with no `?session=` param. You'll
  land on a setup screen to create a session code (e.g. `SF-01`). This
  unlocks facilitator mode (`?admin=1`) and a sidebar with the join
  link/QR code, group-size control, and a reset-board control.
- **Participants**: never see or type the session code — they just scan the
  QR code (or open the join link) the facilitator shares, which already has
  `?session=CODE` baked in.

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
   APP_BASE_URL = "https://your-app-name.streamlit.app"
   ```

   (`APP_BASE_URL` is optional — it just prefills the QR/join-link field in
   the facilitator sidebar; you can also paste the URL in manually after
   deploying, once you know it.)

4. Deploy. The app is stateless/file-backed and fine to let sleep between
   sessions — no need to keep it warm.

## Data & storage notes

- Live updates use polling (every 4 seconds), not websockets.
- Board data is stored as JSON files under `data/`, one per session code.
  This is fine for Streamlit Community Cloud's single-process deployment,
  but data does **not** survive a redeploy or app restart — that's expected
  for a tool meant to be reset between workshops.
- Anonymous by design: notes, agency-map entries, votes, and pulse answers
  are never linked to a name — only the roster/grouping step is.
- The `ANTHROPIC_API_KEY` is read server-side via `st.secrets` and is never
  sent to the browser.

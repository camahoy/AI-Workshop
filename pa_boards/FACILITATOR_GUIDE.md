# Facilitator guide: US Public Affairs AI session live boards

**App:** `https://<your-boards-app>.streamlit.app` (fill in once deployed)
**Presenter passcode:** set as `PRESENTER_PASSCODE` in the app's Secrets. Don't write it on slides.

| Board | Participant link (QR) | Presenter (projector) | Slide |
|---|---|---|---|
| A · How we use AI | `…/?board=a` | `…/?board=a&view=present` | Part 1 |
| B · Time drains | `…/?board=b` | `…/?board=b&view=present` | Part 2 |
| C · What's next | `…/?board=c` | `…/?board=c&view=present` | Part 5 |

## The day before
1. Open any presenter link, enter the passcode, then open **Settings** in the left sidebar:
   - **Session date**: used in the CSV `Source` column ("Live board, YYYY-MM-DD") and for auto-delete.
   - **Board B seed rows**: on by default (6 rows from the 13 Aug session, 0 votes). Switch off if you don't want them.
   - **Delete … days after the session**: 30 by default.
2. Download **QR code PNGs (all 3, .zip)** (1200×1200 px each) and drop them into the deck placeholders.
3. Check each board is empty: **Reset Board A/B/C**, or **Delete all data**.

## During the session
- Put the presenter link for the current board on the projector. Collapse the sidebar (`«`) so only the board shows. The projector updates about every 2 seconds. Phones redraw whenever someone taps, or with **↻ Refresh**, and on their own every 30 seconds, so point people to the projector for the live view.
- The **QR code** stays on screen until you press **Hide QR code**.
- **Close posting** when the time is up. This stops new posts, votes and comments and generates the summary on screen. **Reopen posting** undoes it.
- **Generate summary** gives totals, the top 5, tool and task counts (Board A), and estimated hours per month (Board B). **Remove summary from screen** hides it again.
- **Board C:** results stay hidden until you press **Reveal results**. Phones see them too once revealed.
- **Moderate (hide a post):** tap a post to hide it. It disappears from phones, the projector, the summary and the export. Tap again to unhide.
- Switch boards with the **A · B · C** links at the top of the sidebar. You stay logged in.

## After the session
1. **Export all boards + summary (.zip)** gives three CSVs plus `summary.txt`. The Board B CSV columns match the Wishlist tab (`Time drain, How often, Minutes each time, Votes, Comments, Source`), so you can paste the rows straight in.
2. Press **Delete all data (all boards)**, then confirm within 6 seconds. If you don't, everything is deleted automatically on the date shown under Settings.

## Good to know
- Two-click safety: reset and delete need a second click within 6 seconds.
- Votes are one per browser per post, and tapping again undoes. Someone using two browsers could vote twice. This is acceptable for a team session.
- **Don't push code changes to the repo during the session.** Streamlit restarts the app on a push, and the boards live on the app's local disk.
- Participants see this reminder above every form: "Describe the task, not the client. No client names, people's names or confidential figures."

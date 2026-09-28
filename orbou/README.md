# ORBOU — Phase 1: The Living Core

Your orb, your guardian. It holds the plan and shows you what's next. This is Phase 1 of the living brief, built as an Expo (React Native) app that ships as an installable PWA first, with iOS/Android from the same code later.

## What's in Phase 1

| Brief item | Where |
|---|---|
| Expo project + navigation | Expo SDK 57, Expo Router, `src/app/` |
| AI onboarding conversation | `src/app/onboarding.tsx` → `api/chat.ts` (Vercel function, Anthropic API) |
| Home — today view + daily schedule | `src/app/(tabs)/index.tsx` |
| Fitness — 6-day plan + logging | `src/app/(tabs)/fitness.tsx` |
| Nutrition — planner + grocery | `src/app/(tabs)/nutrition.tsx` |
| Protocol — supplements + skin tracker | `src/app/(tabs)/protocol.tsx` |
| AsyncStorage + Supabase sync | `src/lib/store.tsx`, `src/lib/supabase.ts`, `supabase/schema.sql` |
| Supabase auth (email magic link) | River tab → "Your data" |
| PWA config → Vercel deploy | `vercel.json`, `public/`, `scripts/pwa.mjs` |

Also there: a River tab with a 12-week river of dots (a record of days you showed up, not a streak), your vision statement (editable), and a way to redo onboarding.

**How it works:**
- **Onboarding.** ORBOU opens with "Hey. What's been on your mind lately.", reflects back and follows threads, then asks "Want me to organize this into your orb?". Structured output then turns the conversation into your vision, domains and what the orb will hold. If the chat API isn't reachable, a shorter scripted conversation in the same voice runs instead, so onboarding never gets stuck.
- **Today.** The current block (live progress bar) is the hero. Below it: a Full / Light / Rest mode selector that changes the wording of the blocks, a week strip, and the whole day. Past blocks fade. Tap any block to expand it and check it off.
- **Fitness.** Warm-up, then the session in order with cable exercises grouped together. Every set has a weight field. Your last weight fills in automatically next time. The ab finisher appears on Mon, Fri and Sat. Thursday is active rest and Sunday is rest.
- **Nutrition.** Today's plate, calories planned vs. 1,300, an adjustable macro split, and a 2.5L water tracker. Also: a week planner (pick a meal for each slot on each day), the recipe library, and a de-duplicated grocery list built from the week.
- **Protocol.** Supplements split into morning, with lunch and evening, each with dose, timing and why, and a progress bar that fills as you take them. Also AM and PM skin steps, and hair nightly and weekly.
- **Data.** Everything is saved on the device first and works offline. If you sign in with a magic link, your whole orb syncs to one Supabase row that only you can read (row-level security). When two copies differ, the most recent one wins.

## Run it locally

```bash
cd orbou
npm install
npm run web          # Expo dev server → press w
```

The dev server doesn't serve `/api`, so onboarding runs the scripted conversation. To use the real guardian locally, run `npx vercel dev` with `ANTHROPIC_API_KEY` set, or point `EXPO_PUBLIC_API_BASE` at a deployed copy.

Checks: `npm run typecheck`.

## Deploy to Vercel (get it on your iPhone)

1. Import the repo in Vercel and set **Root Directory = `orbou`**. `vercel.json` provides the build command (`npm run build:web`) and the output directory (`dist`).
2. Environment variables (see `.env.example`):
   - `ANTHROPIC_API_KEY`: needed for the onboarding chat. It's only used server-side.
   - `ORBOU_MODEL`: optional. Defaults to `claude-sonnet-4-6`, as the brief specifies.
   - `EXPO_PUBLIC_SUPABASE_URL`, `EXPO_PUBLIC_SUPABASE_ANON_KEY`: optional. Without them the app runs local-only.
3. Deploy. On your iPhone, open the link in Safari, tap Share, then Add to Home Screen.

### Supabase (optional, for sync)

1. Create a project and run `supabase/schema.sql` in the SQL editor.
2. Under Auth → URL Configuration, add your Vercel URL as the Site URL and as a Redirect URL. The magic link sends you back there.
3. Put the project URL and anon key into the two `EXPO_PUBLIC_…` variables and redeploy.

## Editing your plan

Your plan lives as plain data in `src/data/`: `schedule.ts`, `fitness.ts`, `nutrition.ts`, `protocol.ts`. Change a time, an exercise or a meal there. The **warm-ups** in `fitness.ts` are sensible defaults I wrote because the brief doesn't list them, so swap in your own. Design tokens (the colors, the two type families, the radii) are in `src/theme/index.ts`.

## Not in Phase 1 (by design)

Morning ritual and stretch timers, timed water prompts, exercise library and plan builder, weight charts, Sunday prep sequencing, Orb Intelligence suggestions, push notifications and Partner Orb are all Phase 2. Native magic-link deep links are also left for when the app runs as a native build.

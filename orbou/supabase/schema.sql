-- ORBOU sync table. Run once in the Supabase SQL editor.
-- One row per person holding their whole orb as JSON; the app syncs last-write-wins.
create table if not exists public.orbou_state (
  user_id uuid primary key references auth.users (id) on delete cascade,
  data jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.orbou_state enable row level security;

-- Row-level security: you can only ever see or touch your own row.
create policy "own row: select" on public.orbou_state for select using (auth.uid() = user_id);
create policy "own row: insert" on public.orbou_state for insert with check (auth.uid() = user_id);
create policy "own row: update" on public.orbou_state for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "own row: delete" on public.orbou_state for delete using (auth.uid() = user_id);

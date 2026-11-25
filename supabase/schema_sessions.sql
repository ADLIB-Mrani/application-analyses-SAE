-- Proposition : réglages d'analyse appartenant à chaque utilisateur authentifié.
-- Ne contient aucune ligne individuelle de questionnaires.
create table if not exists public.sae_analysis_settings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (length(name) between 1 and 100),
  fingerprint text not null check (length(fingerprint) = 64),
  groups jsonb not null default '{}'::jsonb,
  targets jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists sae_analysis_settings_user_idx
  on public.sae_analysis_settings (user_id, updated_at desc);
alter table public.sae_analysis_settings enable row level security;
create policy "sae_select_own" on public.sae_analysis_settings
  for select to authenticated using (user_id = (select auth.uid()));
create policy "sae_insert_own" on public.sae_analysis_settings
  for insert to authenticated with check (user_id = (select auth.uid()));
create policy "sae_update_own" on public.sae_analysis_settings
  for update to authenticated using (user_id = (select auth.uid()))
  with check (user_id = (select auth.uid()));
create policy "sae_delete_own" on public.sae_analysis_settings
  for delete to authenticated using (user_id = (select auth.uid()));

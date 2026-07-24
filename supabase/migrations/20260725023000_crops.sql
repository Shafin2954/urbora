create table crops (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  crop text,
  farm_id text not null unique,
  session_id text not null unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table crops enable row level security;

create policy "own crops" on crops
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

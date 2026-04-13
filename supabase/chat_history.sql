create extension if not exists pgcrypto;

create table if not exists public.chat_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'New chat',
  program text not null default '',
  course_filter text not null default '',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.chat_messages (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.chat_sessions(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant')),
  content text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create index if not exists chat_sessions_user_updated_idx
  on public.chat_sessions (user_id, updated_at desc);

create index if not exists chat_messages_session_created_idx
  on public.chat_messages (session_id, created_at asc);

alter table public.chat_sessions enable row level security;
alter table public.chat_messages enable row level security;

drop policy if exists "Users can read their own chat sessions" on public.chat_sessions;
create policy "Users can read their own chat sessions"
  on public.chat_sessions
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert their own chat sessions" on public.chat_sessions;
create policy "Users can insert their own chat sessions"
  on public.chat_sessions
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update their own chat sessions" on public.chat_sessions;
create policy "Users can update their own chat sessions"
  on public.chat_sessions
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete their own chat sessions" on public.chat_sessions;
create policy "Users can delete their own chat sessions"
  on public.chat_sessions
  for delete
  using (auth.uid() = user_id);

drop policy if exists "Users can read their own chat messages" on public.chat_messages;
create policy "Users can read their own chat messages"
  on public.chat_messages
  for select
  using (auth.uid() = user_id);

drop policy if exists "Users can insert their own chat messages" on public.chat_messages;
create policy "Users can insert their own chat messages"
  on public.chat_messages
  for insert
  with check (auth.uid() = user_id);

drop policy if exists "Users can update their own chat messages" on public.chat_messages;
create policy "Users can update their own chat messages"
  on public.chat_messages
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

drop policy if exists "Users can delete their own chat messages" on public.chat_messages;
create policy "Users can delete their own chat messages"
  on public.chat_messages
  for delete
  using (auth.uid() = user_id);

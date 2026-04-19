-- Run this in the Supabase SQL editor to enable separate chat histories.
-- Existing rows in chatbot_conversations can stay as they are.

create table if not exists public.chat_sessions (
    id uuid primary key default gen_random_uuid(),
    -- Keep this flexible because existing projects may use uuid, int, or text user ids.
    user_id text null,
    title text not null default 'New chat',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

alter table public.chatbot_conversations
add column if not exists conversation_id uuid null references public.chat_sessions(id) on delete cascade;

create index if not exists idx_chat_sessions_user_updated
on public.chat_sessions(user_id, updated_at desc);

create index if not exists idx_chatbot_conversations_conversation_time
on public.chatbot_conversations(conversation_id, timestamp asc);

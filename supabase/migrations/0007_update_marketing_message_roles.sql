-- Allow additional ChatKit item roles (workflow/context) in marketing_messages
alter table if exists public.marketing_messages
  drop constraint if exists marketing_messages_role_check;

alter table if exists public.marketing_messages
  add constraint marketing_messages_role_check
  check (
    role in (
      'system',
      'user',
      'assistant',
      'tool',
      'progress',
      'event',
      'workflow',
      'context'
    )
  );

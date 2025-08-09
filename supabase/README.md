Supabase setup

- Required env vars:
  - SUPABASE_URL
  - SUPABASE_SERVICE_ROLE_KEY (prefer) or SUPABASE_ANON_KEY

- Apply migrations:
  - Use the Supabase CLI or UI. For CLI:
    - supabase link --project-ref <ref>
    - supabase db push (or supabase migration up)
  - Alternatively, run the SQL in supabase/migrations/*.sql via SQL editor.

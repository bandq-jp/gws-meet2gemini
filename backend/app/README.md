Meet2Gemini FastAPI (Cloud Run)

- Local auth: uses service_account.json with domain-wide delegation; set GOOGLE_SUBJECT_EMAILS as comma list
- Cloud Run: workload identity (no key) + env GOOGLE_SUBJECT_EMAILS
- Supabase: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
- Gemini: set GEMINI_API_KEY
 - Optional (Notta xlsx in shared drive):
   - MEETING_SOURCE=notta (or both)
   - NOTTA_FOLDER_ID (or NOTTA_FOLDER_NAME)
   - NOTTA_ORGANIZER_EMAIL (fixed value used for filtering)
 - Optional (Zoho write): ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ZOHO_API_BASE_URL, ZOHO_ACCOUNTS_BASE_URL
 - Optional (Auto process):
   - CANDIDATE_TITLE_REGEX: regex to extract candidate name from Docs title (use group 'name' or group(1)). If empty, the whole title is used.
   - AUTOPROC_MAX_ITEMS: default max items to process per run (default 20)
   - TASKS_AUTOPROC_WORKER_URL: Cloud Tasks worker URL for auto process (falls back from TASKS_WORKER_URL if unset)

Run locally:
- uvicorn app.main:app --reload

Endpoints:
- POST /api/v1/meetings/collect?accounts=foo@bar,alice@bar
- GET  /api/v1/meetings
- GET  /api/v1/meetings/{id}
- POST /api/v1/structured/process/{meeting_id}
- GET  /api/v1/structured/{meeting_id}
 - POST /api/v1/structured/auto-process (background run, title x Zoho name strict match only)
 - POST /api/v1/structured/auto-process-task (enqueue to Cloud Tasks)
 - POST /api/v1/structured/auto-process/worker (Cloud Tasks worker)

Auto process behavior:
- Skip when no transcription (text_content is empty) or when structured_outputs already exists
- Skip when Docs title does not contain "初回"
- Extract candidate name from title via CANDIDATE_TITLE_REGEX or request.title_regex
- Strict equals match against Zoho APP-hc 求職者名; proceed only with exactly 1 result
- Runs ProcessStructuredDataUseCase (extract + save + Zoho write) for matched meetings

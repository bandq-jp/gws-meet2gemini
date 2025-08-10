Meet2Gemini FastAPI (Cloud Run)

- Local auth: uses service_account.json with domain-wide delegation; set GOOGLE_SUBJECT_EMAILS as comma list
- Cloud Run: workload identity (no key) + env GOOGLE_SUBJECT_EMAILS
- Supabase: set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
- Gemini: set GEMINI_API_KEY

Run locally:
- uvicorn app.main:app --reload

Endpoints:
- POST /api/v1/meetings/collect?accounts=foo@bar,alice@bar
- GET  /api/v1/meetings
- GET  /api/v1/meetings/{id}
- POST /api/v1/structured/process/{meeting_id}
- GET  /api/v1/structured/{meeting_id}

# Repository Guidelines

## Project Structure & Tech Stack
- `app/`: FastAPI service (DDD/onion).
  - `presentation/api/v1/`: Routers (`meetings.py`, `structured.py`); entrypoint `app.main:app`.
  - `presentation/schemas/`: Pydantic I/O models.
  - `application/use_cases/`: Orchestration (no external I/O).
  - `domain/{entities,services,repositories}`: Pure domain logic.
  - `infrastructure/{google,gemini,supabase,config}`: Clients/integration code.
- `supabase/migrations/`: DB schema SQL (e.g., `meeting_documents`, `structured_outputs`).
- `docs/`: `ENDPOINTS.md`, `test-client.html` for manual checks.
- `tests/`: Utility scripts and sample data.
- Root `main.py`: optional Drive webhook (Cloud Functions 2nd gen) using Firestore.
- Tech: Python 3.12, FastAPI, Uvicorn, Supabase (HTTP API), Google Drive/Docs, Google GenAI (Gemini), Docker/Cloud Run, dotenv.

## Processing Flow
1) Collect: `POST /api/v1/meetings/collect?accounts=a@x&accounts=b@x`
   - Impersonates target accounts, scans Google Docs under Meet-related folders, upserts text and metadata to Supabase (`doc_id+organizer_email` unique).
2) Structure: `POST /api/v1/structured/process/{meeting_id}`
   - Loads `text_content`, extracts structured JSON via Gemini (split schema groups for stability), saves to `structured_outputs`.
3) Retrieve: `GET /api/v1/meetings`, `GET /api/v1/meetings/{id}`, `GET /api/v1/structured/{id}`.
4) Webhook (optional): Root `main.py` consumes Drive changes, persists pageTokens in Firestore, and can export Docs text for downstream processing.

## Build, Test, and Development
- Install: `pip install -e .`  • Run: `uvicorn app.main:app --reload`
- Validate Drive access: `python tests/validate_setup.py`
- Docker: `docker build -t meet2gemini . && docker run --env-file .env -p 8080:8080 meet2gemini`
- Deploy (Cloud Run): see `README.md` for `gcloud run deploy`.

## Coding Style & Conventions
- 4-space indent, type hints, `snake_case` for modules/functions, `PascalCase` for classes.
- Place new routers in `presentation/api/v1`, schemas in `presentation/schemas`, use cases in `application/use_cases`.
- Keep use cases pure; perform external I/O in `infrastructure/*`. Respect `LOG_LEVEL`.

## Testing Guidelines
- Prefer `pytest` with `tests/test_*.py`; mock Google/Supabase/Gemini.
- Manual checks via `docs/test-client.html` at `http://localhost:8000`.

## Commit & PR
- Commits: imperative, concise (EN/JP). Example: `feat(api): add meetings list` / 「ログ強化: Drive収集処理のデバッグ追加」
- PRs: purpose, changes, test steps (cURL/commands), related issues, screenshots/sample responses. Update `.env.example` and migrations as needed.

## Security & Config
- Do not commit secrets (`service_account.json`); use `.env` locally, Secret Manager in production.
- Required env: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY` or `GOOGLE_API_KEY`, `SERVICE_ACCOUNT_JSON` (local), optional `CORS_ALLOW_ORIGINS`.

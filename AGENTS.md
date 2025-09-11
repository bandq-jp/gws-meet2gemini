# Repository Guidelines

Concise instructions for contributors to keep changes small, safe, and consistent with the project’s architecture.

## Project Structure & Module Organization
- `backend/` (FastAPI, DDD/onion)
  - `app/presentation/api/v1/`: Routers (`meetings.py`, `structured.py`)
  - `app/presentation/schemas/`: Pydantic I/O models
  - `app/application/use_cases/`: Orchestration (pure, no external I/O)
  - `app/domain/{entities,services,repositories}`: Pure domain logic
  - `app/infrastructure/{google,gemini,zoho,supabase,config}`: Clients/I-O
  - Entrypoint: `app.main:app` (Uvicorn)
- `backend/docs/`: `ENDPOINTS.md`, `test-client.html`
- `supabase/migrations/`: SQL schemas (`meeting_documents`, `structured_outputs`)
- `frontend/`: optional UI/dev tools

## Build, Test, and Development Commands
- Setup (Python 3.12)
  - `cd backend && python -m venv .venv && source .venv/bin/activate`
  - `pip install -e .`
- Run API: `uvicorn app.main:app --reload`
- Quick validation: `python tests/validate_setup.py`
- Docker: `docker build -t meet2gemini backend && docker run --env-file ../.env -p 8080:8080 meet2gemini`

## Coding Style & Naming Conventions
- 4-space indent, type hints; `snake_case` modules/functions; `PascalCase` classes.
- Keep use cases pure; external I/O only in `infrastructure/*`.
- Respect `LOG_LEVEL` (prefer INFO for commits; avoid noisy DEBUG).

## Testing Guidelines
- Use `pytest` (`tests/test_*.py`); mock Google/Supabase/Gemini/Zoho.
- Manual checks: open `backend/docs/test-client.html` and call local endpoints.
- Safe dry-run: `POST /api/v1/structured/auto-process` with `{ "dry_run": true, "sync": true }`.

## Commit & Pull Request Guidelines
- Commits: short, imperative (EN/JP). Examples: `feat(api): add meetings list` / `ログ強化: Drive収集処理のデバッグ追加`.
- PRs: purpose, changes, test steps（cURL/commands）, related issues, screenshots/sample responses. Update `.env.example` and migrations when needed.

## Security & Configuration Tips
- Never commit secrets (e.g., `service_account.json`, API keys). Use `.env` locally and Secret Manager in production.
- Required (backend): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY|GOOGLE_API_KEY`, `SERVICE_ACCOUNT_JSON`; optional `CORS_ALLOW_ORIGINS`, Zoho creds for write paths.

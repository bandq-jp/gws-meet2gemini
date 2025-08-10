# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A FastAPI-based service that collects Google Meet transcripts from Google Drive, stores them in Supabase, and generates structured summaries using Gemini AI. Designed for Cloud Run deployment with DDD/Onion Architecture principles.

## Development Commands

### Local Development
```bash
# Install dependencies
pip install -e .

# Start development server
uvicorn app.main:app --reload

# Alternative with custom port
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Testing
Access the test client at `http://localhost:8000/test-client` or open `docs/test-client.html` directly in a browser.

### Cloud Run Deployment
```bash
# Build container
gcloud builds submit --tag gcr.io/<PROJECT>/meet2gemini

# Deploy
gcloud run deploy meet2gemini \
  --image gcr.io/<PROJECT>/meet2gemini \
  --region <REGION> \
  --set-env-vars SUPABASE_URL=... \
  --set-env-vars SUPABASE_SERVICE_ROLE_KEY=... \
  --set-env-vars GOOGLE_SUBJECT_EMAILS=... \
  --set-env-vars GEMINI_API_KEY=... \
  --allow-unauthenticated
```

## Architecture

### DDD/Onion Structure
- **app/presentation/**: FastAPI routers and API schemas (input/output transformation)
- **app/application/use_cases/**: Business logic orchestration (collect_meetings.py, process_structured_data.py, etc.)
- **app/domain/**: Core entities and domain services (meeting_document.py, structured_data.py)
- **app/infrastructure/**: External integrations
  - `google/`: Google Drive/Docs API clients
  - `supabase/`: Database repositories using HTTP API
  - `gemini/`: AI extraction with structured output
  - `config/`: Settings and environment variables

### Key Integration Points
- Google API authentication uses service account JSON locally, Workload Identity in Cloud Run
- Supabase integration via HTTP API only (no direct Postgres connection)
- Gemini extraction uses split/parallel processing for large schemas
- CORS middleware configured for local test client

### Database Schema
Tables in Supabase:
- `meeting_documents`: Meeting transcripts with metadata (unique on doc_id + organizer_email)
- `structured_outputs`: Processed Gemini extractions

Apply migrations by running `supabase/migrations/0001_init.sql` in Supabase SQL editor.

## Environment Configuration

Required environment variables:
- `SERVICE_ACCOUNT_JSON`: Path to service account file (local only)
- `GOOGLE_SUBJECT_EMAILS`: Comma-separated email accounts to impersonate
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`: Gemini AI API key
- `LOG_LEVEL`: Logging level (default: INFO)
- `CORS_ALLOW_ORIGINS`: CORS allowed origins (default: *)

Copy `.env.example` to `.env` for local development.

## API Endpoints

Base path: `/api/v1`

- `POST /meetings/collect?accounts=email1&accounts=email2`: Collect Google Docs from specified accounts
- `GET /meetings`: List stored meeting documents
- `GET /meetings/{id}`: Get specific meeting document
- `POST /structured/process/{meeting_id}`: Process meeting with Gemini AI
- `GET /structured/{meeting_id}`: Retrieve structured output

## Development Notes

- The service uses domain-wide delegation to impersonate Google Workspace users
- Meeting documents are detected by folder structure (Meet Recordings folder)
- Gemini processing splits large documents for better reliability
- All database operations use Supabase HTTP API, not direct SQL connections
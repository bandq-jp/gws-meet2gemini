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
  --no-allow-unauthenticated
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

## Security Configuration

### Backend (Cloud Run) - 社内限定アクセス

Cloud Run は認証必須 (`--no-allow-unauthenticated`) で設定され、Vercel の BFF 経由のみアクセス可能。

### Frontend (Vercel) - 社内ドメイン制限

Clerk認証に加えて、社内ドメイン（@bandq.jp）のみアクセス許可。

## Service Account Setup (Vercel用)

1. **Vercel用サービスアカウント作成**:
```bash
gcloud iam service-accounts create vercel-bff \
  --display-name="Vercel BFF Invoker"
```

2. **Cloud Run Invoker権限付与**:
```bash
gcloud run services add-iam-policy-binding meet2gemini \
  --region <REGION> \
  --member=serviceAccount:vercel-bff@<PROJECT>.iam.gserviceaccount.com \
  --role=roles/run.invoker
```

3. **サービスアカウントキー生成**:
```bash
gcloud iam service-accounts keys create vercel-sa-key.json \
  --iam-account=vercel-bff@<PROJECT>.iam.gserviceaccount.com
```

## Environment Configuration

### Backend Environment Variables:
- `SERVICE_ACCOUNT_JSON`: Path to service account file (local only)
- `GOOGLE_SUBJECT_EMAILS`: Comma-separated email accounts to impersonate
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY`: Supabase service role key
- `GEMINI_API_KEY` or `GOOGLE_API_KEY`: Gemini AI API key
- `LOG_LEVEL`: Logging level (default: INFO)
- `CORS_ALLOW_ORIGINS`: 社内VercelドメインのみCC例: `https://your-app.vercel.app`
- `ENV`: Environment type (`local` for development, `production` for Cloud Run)

### Frontend Environment Variables:

**Local Development (`.env.local`)**:
```bash
USE_LOCAL_BACKEND=true
DEV_BACKEND_BASE=http://localhost:8000
ALLOWED_EMAIL_DOMAINS=@bandq.jp
```

**Production (Vercel Environment Variables)**:
```bash
USE_LOCAL_BACKEND=false
CLOUD_RUN_BASE=https://<service>-<hash>-<region>.run.app
GCP_SA_JSON=<vercel-sa-key.jsonの内容>
ALLOWED_EMAIL_DOMAINS=@bandq.jp
```

Copy `.env.example` to `.env` for local development.

## API Endpoints

Base path: `/api/v1`

- `POST /meetings/collect?accounts=email1&accounts=email2`: Collect Google Docs from specified accounts
- `GET /meetings`: List stored meeting documents
- `GET /meetings/{id}`: Get specific meeting document
- `POST /structured/process/{meeting_id}`: Process meeting with Gemini AI
- `GET /structured/{meeting_id}`: Retrieve structured output

## Security Verification Checklist

### 本番切替前の確認事項:

1. **Cloud Run 設定確認**:
   - [ ] `--no-allow-unauthenticated` でデプロイされている
   - [ ] Vercel用サービスアカウントに `roles/run.invoker` 権限が付与されている
   - [ ] 直接 `run.app` URL にアクセスすると 401/403 エラーが返る

2. **Vercel BFF 確認**:
   - [ ] `USE_LOCAL_BACKEND=false` で本番Cloud Runを呼び出し
   - [ ] `GCP_SA_JSON` にサービスアカウントキーが設定されている
   - [ ] ID Token が正しく付与されてCloud Runにリクエストされている

3. **社内ドメイン制限確認**:
   - [ ] `@bandq.jp` 以外のメールアドレスでログインすると `/unauthorized` にリダイレクト
   - [ ] ローカル開発では社内ドメイン制限が無効化されている

4. **CORS 制限確認**:
   - [ ] 本番バックエンドの `CORS_ALLOW_ORIGINS` にVercelドメインのみ設定
   - [ ] 他のドメインからのブラウザアクセスが拒否される

### ローカル開発テスト:
```bash
# バックエンド
cd backend
uvicorn app.main:app --reload --port 8000

# フロントエンド
cd frontend
bun run dev  # http://localhost:3000
```

### 本番Cloud Run プロキシテスト（認証必要）:
```bash
gcloud run services proxy meet2gemini --region <REGION> --port 8085
# → http://localhost:8085 で認証付きアクセス可能
```

## Development Notes

- The service uses domain-wide delegation to impersonate Google Workspace users
- Meeting documents are detected by folder structure (Meet Recordings folder)  
- Gemini processing splits large documents for better reliability
- All database operations use Supabase HTTP API, not direct SQL connections
- **Security**: Direct access to Cloud Run is blocked; access only via Vercel BFF
- **Access Control**: Company domain (@bandq.jp) restriction via Clerk middleware
from __future__ import annotations
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from app.presentation.api.v1 import router as api_v1_router

# Configure logging level from env (default INFO). Ensures DEBUG logs show when desired.
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()

# ルートロガーの設定
logging.basicConfig(
    level=_log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)

# アプリケーション内のロガーを明示的に設定
logging.getLogger("app").setLevel(_log_level)
logging.getLogger("app.infrastructure.zoho.client").setLevel(_log_level)
logging.getLogger("app.application.use_cases").setLevel(_log_level)

# uvicorn のロガー設定
for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(_name).setLevel(_log_level)

# httpx のHTTPリクエストログを無効化（Supabase等の大量リクエストログを抑制）
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Meet2Gemini API")

# アプリケーション開始時のログ
logger = logging.getLogger("app.main")
logger.info("🚀 Meet2Gemini API サーバー起動中...")
logger.info(f"📊 ログレベル: {_log_level}")
logger.info("🎯 Zoho書き込みログが有効です")

@app.get("/health")
def health():
    return {"status": "ok"}

# CORS (社内ドメインのみ許可、本番では明示的な設定必須)
_cors_origins_env = os.getenv("CORS_ALLOW_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

# デフォルトはローカル開発用のみ
if not _cors_origins and os.getenv("ENV", "local") == "local":
    _cors_origins = ["http://localhost:3000"]

if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )

app.include_router(api_v1_router, prefix="/api/v1")

# Serve test client HTML via FastAPI
_root_dir = Path(__file__).resolve().parents[1]
_docs_dir = _root_dir / "docs"

# Optionally expose docs directory for future assets
if _docs_dir.exists():
    app.mount("/_docs", StaticFiles(directory=str(_docs_dir)), name="docs")

@app.get("/test-client")
def serve_test_client(request: Request):
    path = _docs_dir / "test-client.html"
    if not path.exists():
        return {"error": "test-client.html not found"}, 404
    return FileResponse(str(path), media_type="text/html")

# Read-only: OAuth callback helper for Zoho (displays code only)
@app.get("/oauth/zoho/callback")
def zoho_oauth_callback(request: Request):
    code = request.query_params.get("code")
    error = request.query_params.get("error")
    accounts_server = request.query_params.get("accounts-server", "https://accounts.zoho.jp")
    if error:
        html = f"""
        <html><body>
        <h3>Zoho 認可エラー</h3>
        <p>error={error}</p>
        </body></html>
        """
        return FileResponse(None, status_code=400)
    if not code:
        return {"detail": "code not found"}, 400
    # Show code and example curl to exchange (read-only helper)
    html = f"""
    <!doctype html><html lang=ja><meta charset=utf-8>
    <body style='font-family:system-ui, sans-serif; padding:16px'>
      <h3>Zoho 認可コードを取得しました</h3>
      <p><b>code:</b> <code>{code}</code></p>
      <p>以下のコマンドで refresh_token を取得できます（JP DCの例）。</p>
      <pre style='background:#f8f9fb; padding:12px; border:1px solid #e5e7eb; border-radius:6px; overflow:auto'>
curl -sS -X POST "{accounts_server}/oauth/v2/token" \
  -d "grant_type=authorization_code&client_id=$ZOHO_CLIENT_ID&client_secret=$ZOHO_CLIENT_SECRET&redirect_uri=http://localhost:8000/oauth/zoho/callback&code={code}"
      </pre>
      <p>取得した <code>refresh_token</code> を .env の <code>ZOHO_REFRESH_TOKEN</code> に保存してください。</p>
    </body></html>
    """
    return html

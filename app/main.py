from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

from app.presentation.api.v1 import router as api_v1_router

app = FastAPI(title="Meet2Gemini API")

# Configure logging level from env (default INFO). Ensures DEBUG logs show when desired.
_log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.getLogger().setLevel(_log_level)
for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    logging.getLogger(_name).setLevel(_log_level)

@app.get("/health")
def health():
    return {"status": "ok"}

# CORS (for local HTML test client, Swagger, etc.)
_cors_origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_v1_router, prefix="/api/v1")

# Serve test client HTML via FastAPI
_root_dir = Path(__file__).resolve().parents[1]
_docs_dir = _root_dir / "docs"

# Optionally expose docs directory for future assets
if _docs_dir.exists():
    app.mount("/_docs", StaticFiles(directory=str(_docs_dir)), name="docs")

@app.get("/test-client")
def serve_test_client():
    path = _docs_dir / "test-client.html"
    if not path.exists():
        return {"error": "test-client.html not found"}, 404
    return FileResponse(str(path), media_type="text/html")

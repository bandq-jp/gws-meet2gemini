from __future__ import annotations
import os
from fastapi import FastAPI
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

app.include_router(api_v1_router, prefix="/api/v1")

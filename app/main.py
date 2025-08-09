from __future__ import annotations
import os
from fastapi import FastAPI

from app.presentation.api.v1 import router as api_v1_router

app = FastAPI(title="Meet2Gemini API")

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(api_v1_router, prefix="/api/v1")

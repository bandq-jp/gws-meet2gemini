# backend/app/infrastructure/gemini/error_utils.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple
import re

@dataclass(frozen=True)
class FallbackDecision:
    should_fallback: bool
    reason: str  # "rate_limit" | "server_error" | "permission" | "not_found" | "other"

def classify_gemini_error(code: int | None, message: str | None) -> FallbackDecision:
    msg = (message or "").lower()
    # 明確なレート制限・クォータ超過
    if code == 429 or "resource_exhausted" in msg or "rate limit" in msg or "quota" in msg:
        return FallbackDecision(True, "rate_limit")
    # 一時的障害
    if code in (500, 503):
        return FallbackDecision(True, "server_error")
    # モデル権限や利用不可
    if code == 403 and ("permission" in msg or "not authorized" in msg or "access" in msg):
        return FallbackDecision(True, "permission")
    # モデル未提供/間違い
    if code == 404 and ("model" in msg or "not found" in msg):
        return FallbackDecision(True, "not_found")
    return FallbackDecision(False, "other")
from __future__ import annotations
from typing import Any
from supabase import create_client, Client
from app.infrastructure.config.settings import get_settings

_client: Client | None = None

def get_supabase() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("Supabase URL and Key are required")
        _client = create_client(settings.supabase_url, settings.supabase_key)
    return _client

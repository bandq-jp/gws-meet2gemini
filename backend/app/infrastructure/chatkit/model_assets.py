from __future__ import annotations

from typing import Any, Dict, Optional, List
from uuid import uuid4

from app.infrastructure.supabase.client import get_supabase


TABLE = "marketing_model_assets"


def get_model_asset(asset_id: str | None) -> Optional[Dict[str, Any]]:
    """Fetch a model asset preset by id. Returns None if not found."""
    if not asset_id:
        return None
    sb = get_supabase()
    res = (
        sb.table(TABLE)
        .select("*")
        .eq("id", asset_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    return rows[0]


def list_model_assets() -> List[Dict[str, Any]]:
    sb = get_supabase()
    res = sb.table(TABLE).select("*").order("created_at", desc=True).execute()
    return res.data or []


def upsert_model_asset(payload: Dict[str, Any]) -> Dict[str, Any]:
    sb = get_supabase()
    data = payload.copy()
    if not data.get("id"):
        data["id"] = str(uuid4())
    res = sb.table(TABLE).upsert(data, returning="representation").execute()
    rows = res.data or []
    if not rows:
        return data
    return rows[0]


def set_thread_model_asset(thread_id: str, asset_id: str | None) -> None:
    """Persist selected model asset on conversation metadata."""
    if not thread_id or not asset_id:
        return
    sb = get_supabase()
    # merge metadata
    current = (
        sb.table("marketing_conversations")
        .select("metadata")
        .eq("id", thread_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    metadata = (current[0].get("metadata") if current else {}) or {}
    if metadata.get("model_asset_id") == asset_id:
        return
    metadata["model_asset_id"] = asset_id
    sb.table("marketing_conversations").update({"metadata": metadata}).eq("id", thread_id).execute()

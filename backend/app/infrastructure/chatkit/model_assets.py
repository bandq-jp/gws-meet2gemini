from __future__ import annotations

from typing import Any, Dict, Optional, List
from uuid import uuid4

from app.infrastructure.supabase.client import get_supabase
from app.infrastructure.chatkit.context import MarketingRequestContext


TABLE = "marketing_model_assets"


def get_model_asset(asset_id: str | None, context: Optional["MarketingRequestContext"] = None) -> Optional[Dict[str, Any]]:
    """Fetch a model asset preset by id, honoring visibility when context is provided."""
    if not asset_id:
        return None
    sb = get_supabase()

    query = sb.table(TABLE).select("*").eq("id", asset_id)
    if context:
        # Allow access if public/legacy (null) or owner
        or_filter = "visibility.eq.public,visibility.is.null,created_by.eq." + context.user_id
        query = query.or_(or_filter)

    res = query.limit(1).execute()
    rows = res.data or []
    if not rows:
        return None
    asset = rows[0]
    if context and asset.get("visibility") == "private" and asset.get("created_by") != context.user_id:
        return None
    return asset


def list_model_assets(context: Optional["MarketingRequestContext"] = None) -> List[Dict[str, Any]]:
    sb = get_supabase()
    if context:
        or_filter = "visibility.eq.public,visibility.is.null,created_by.eq." + context.user_id
        res = (
            sb.table(TABLE)
            .select("*")
            .or_(or_filter)
            .order("created_at", desc=True)
            .execute()
        )
    else:
        res = sb.table(TABLE).select("*").order("created_at", desc=True).execute()
    return res.data or []


def upsert_model_asset(payload: Dict[str, Any], context: Optional["MarketingRequestContext"] = None) -> Dict[str, Any]:
    sb = get_supabase()
    data = payload.copy()
    if not data.get("id"):
        data["id"] = str(uuid4())

    data.setdefault("visibility", "public")
    if context:
        data.setdefault("created_by", context.user_id)
        data.setdefault("created_by_email", context.user_email)
        data.setdefault("created_by_name", context.user_name)

    res = sb.table(TABLE).upsert(data, returning="representation").execute()
    rows = res.data or []
    if not rows:
        return data
    return rows[0]


def delete_model_asset(asset_id: str) -> bool:
    """Delete a model asset by id. Returns True if deleted successfully."""
    if not asset_id:
        return False
    # Prevent deletion of standard preset
    if asset_id == "standard":
        return False
    sb = get_supabase()
    res = sb.table(TABLE).delete().eq("id", asset_id).execute()
    return bool(res.data)


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

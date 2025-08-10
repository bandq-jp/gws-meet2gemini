from __future__ import annotations
from typing import Dict, Any
from app.infrastructure.supabase.client import get_supabase

class StructuredRepositoryImpl:
    TABLE = "structured_outputs"

    def upsert_structured(self, meeting_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        sb = get_supabase()
        payload = {"meeting_id": meeting_id, "data": data}
        res = sb.table(self.TABLE).upsert(payload, on_conflict=["meeting_id"]).execute()
        return res.data[0] if res.data else {}

    def get_by_meeting_id(self, meeting_id: str) -> Dict[str, Any]:
        sb = get_supabase()
        query = sb.table(self.TABLE).select("*").eq("meeting_id", meeting_id)
        try:
            # Prefer maybe_single to avoid raising when 0 rows
            res = query.maybe_single().execute()
            return res.data or {}
        except Exception:
            # Fallback: take first row if exists, otherwise return empty
            try:
                res = query.limit(1).execute()
                return (res.data[0] if res.data else {})
            except Exception:
                return {}

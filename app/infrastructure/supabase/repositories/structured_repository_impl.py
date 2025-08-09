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
        res = sb.table(self.TABLE).select("*").eq("meeting_id", meeting_id).single().execute()
        return res.data or {}

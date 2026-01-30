from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
from datetime import datetime

@dataclass
class ZohoCandidateInfo:
    candidate_id: Optional[str] = None
    record_id: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None

@dataclass
class ZohoSyncInfo:
    """Zoho同期ステータス情報"""
    status: Optional[str] = None  # success | failed | auth_error | field_mapping_error | error | NULL
    error: Optional[str] = None
    synced_at: Optional[datetime] = None
    fields_count: Optional[int] = None

@dataclass
class StructuredData:
    meeting_id: str
    data: Dict[str, Any]
    zoho_candidate: Optional[ZohoCandidateInfo] = None
    zoho_sync: Optional[ZohoSyncInfo] = None

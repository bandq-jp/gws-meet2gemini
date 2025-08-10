from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class ZohoCandidateInfo:
    candidate_id: Optional[str] = None
    record_id: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None

@dataclass
class StructuredData:
    meeting_id: str
    data: Dict[str, Any]
    zoho_candidate: Optional[ZohoCandidateInfo] = None

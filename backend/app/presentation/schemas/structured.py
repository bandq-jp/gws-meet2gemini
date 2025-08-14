from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict, Optional
from uuid import UUID

class ZohoCandidateOut(BaseModel):
    candidate_id: Optional[str] = None
    record_id: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None

class StructuredOut(BaseModel):
    meeting_id: str
    data: Dict[str, Any]
    zoho_candidate: Optional[ZohoCandidateOut] = None
    custom_schema_id: Optional[UUID] = None
    schema_version: Optional[str] = None

class StructuredProcessRequest(BaseModel):
    zoho_candidate_id: Optional[str] = None
    zoho_record_id: str
    zoho_candidate_name: Optional[str] = None
    zoho_candidate_email: Optional[str] = None
    custom_schema_id: Optional[UUID] = None

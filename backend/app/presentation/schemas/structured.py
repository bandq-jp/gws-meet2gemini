from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict, Optional, List
from uuid import UUID

class ZohoCandidateOut(BaseModel):
    candidate_id: Optional[str] = None
    record_id: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None

class ZohoWriteResult(BaseModel):
    """Zoho書き込み結果"""
    status: str  # success, failed, auth_error, error
    message: str
    updated_fields_count: Optional[int] = None
    updated_fields: Optional[List[str]] = None
    zoho_response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    attempted_data_count: Optional[int] = None

class StructuredOut(BaseModel):
    meeting_id: str
    data: Dict[str, Any]
    zoho_candidate: Optional[ZohoCandidateOut] = None
    custom_schema_id: Optional[UUID] = None
    schema_version: Optional[str] = None
    zoho_write_result: Optional[ZohoWriteResult] = None

class StructuredProcessRequest(BaseModel):
    zoho_candidate_id: Optional[str] = None
    zoho_record_id: str
    zoho_candidate_name: Optional[str] = None
    zoho_candidate_email: Optional[str] = None
    custom_schema_id: Optional[UUID] = None

class ExtractOnlyRequest(BaseModel):
    """構造化出力専用リクエスト"""
    custom_schema_id: Optional[UUID] = None

class SyncToZohoRequest(BaseModel):
    """手動Zoho同期リクエスト"""
    zoho_candidate_id: Optional[str] = None
    zoho_record_id: str
    zoho_candidate_name: Optional[str] = None
    zoho_candidate_email: Optional[str] = None

class ExtractOnlyOut(BaseModel):
    """構造化出力専用レスポンス"""
    meeting_id: str
    data: Dict[str, Any]
    custom_schema_id: Optional[UUID] = None
    schema_version: Optional[str] = None

class SyncToZohoOut(BaseModel):
    """手動Zoho同期レスポンス"""
    meeting_id: str
    zoho_candidate: ZohoCandidateOut
    zoho_sync_result: ZohoWriteResult
    synced_data_fields: List[str]

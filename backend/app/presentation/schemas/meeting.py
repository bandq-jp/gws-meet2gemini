from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class TranscriptUpdateIn(BaseModel):
    """議事録本文の上書きリクエスト"""
    text_content: str = Field(..., description="貼り付けた議事録全文")
    transcript_provider: Optional[str] = Field(default=None, description="文字起こし元サービス名（任意）")
    delete_structured: bool = Field(default=True, description="既存の構造化データを削除するか")

class MeetingSummary(BaseModel):
    """軽量な議事録サマリー（一覧表示用）"""
    id: str
    doc_id: str
    title: Optional[str]
    meeting_datetime: Optional[str]
    organizer_email: Optional[str]
    organizer_name: Optional[str]
    document_url: Optional[str]
    invited_emails: List[str] = Field(default_factory=list)
    is_structured: bool = Field(default=False, description="構造化済みかどうか")
    created_at: Optional[str]
    updated_at: Optional[str]

class MeetingOut(BaseModel):
    """完全な議事録データ（詳細表示用）"""
    id: str
    doc_id: str
    title: Optional[str]
    meeting_datetime: Optional[str]
    organizer_email: Optional[str]
    organizer_name: Optional[str]
    document_url: Optional[str]
    invited_emails: List[str] = Field(default_factory=list)
    text_content: Optional[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_structured: bool = Field(default=False, description="構造化済みかどうか")
    created_at: Optional[str]
    updated_at: Optional[str]

class MeetingListResponse(BaseModel):
    """ページネーション対応の議事録一覧レスポンス"""
    items: List[MeetingSummary]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

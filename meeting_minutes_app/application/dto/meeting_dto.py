from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class MeetingDocumentDTO:
    """議事録ドキュメントのDTO"""
    
    id: str
    document_id: str
    account_email: str
    title: str
    date_time: Optional[str]  # ISO format string
    web_view_link: str
    text_content: str
    owner_email: str
    invited_accounts: List[str]
    downloaded_at: str  # ISO format string
    created_at: str  # ISO format string
    updated_at: str  # ISO format string
    
    @classmethod
    def from_entity(cls, entity) -> 'MeetingDocumentDTO':
        """エンティティからDTOを作成"""
        from ...domain.entities.meeting_document import MeetingDocument
        
        entity_dict = entity.to_dict()
        
        return cls(
            id=entity_dict['id'],
            document_id=entity_dict['document_id'],
            account_email=entity_dict['account_email'],
            title=entity_dict['metadata']['title'],
            date_time=entity_dict['metadata']['date_time'],
            web_view_link=entity_dict['metadata']['web_view_link'],
            text_content=entity_dict['text_content'][:500] + "..." if len(entity_dict['text_content']) > 500 else entity_dict['text_content'],
            owner_email=entity_dict['metadata']['owner_email'],
            invited_accounts=entity_dict['metadata']['invited_accounts'],
            downloaded_at=entity_dict['downloaded_at'],
            created_at=entity_dict['created_at'],
            updated_at=entity_dict['updated_at']
        )


@dataclass
class MeetingDocumentDetailDTO:
    """議事録ドキュメントの詳細DTO（全テキスト含む）"""
    
    id: str
    document_id: str
    account_email: str
    metadata: Dict[str, Any]
    text_content: str
    doc_structure: Optional[Dict[str, Any]]
    downloaded_at: str
    created_at: str
    updated_at: str
    
    @classmethod
    def from_entity(cls, entity) -> 'MeetingDocumentDetailDTO':
        """エンティティから詳細DTOを作成"""
        entity_dict = entity.to_dict()
        
        return cls(
            id=entity_dict['id'],
            document_id=entity_dict['document_id'],
            account_email=entity_dict['account_email'],
            metadata=entity_dict['metadata'],
            text_content=entity_dict['text_content'],
            doc_structure=entity_dict['doc_structure'],
            downloaded_at=entity_dict['downloaded_at'],
            created_at=entity_dict['created_at'],
            updated_at=entity_dict['updated_at']
        )


@dataclass
class MeetingListResponseDTO:
    """議事録一覧レスポンスDTO"""
    
    meetings: List[MeetingDocumentDTO]
    total_count: int
    page: int
    page_size: int
    has_next: bool
    
    @classmethod
    def create(
        cls,
        meetings: List[MeetingDocumentDTO],
        total_count: int,
        page: int,
        page_size: int
    ) -> 'MeetingListResponseDTO':
        """一覧レスポンスDTOを作成"""
        has_next = (page * page_size) < total_count
        
        return cls(
            meetings=meetings,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=has_next
        )


@dataclass
class CollectMeetingsRequestDTO:
    """議事録収集リクエストDTO"""
    
    account_emails: Optional[List[str]] = None
    force_update: bool = False
    include_doc_structure: bool = False
    
    def get_account_emails(self) -> List[str]:
        """アカウントメール一覧を取得（デフォルト値含む）"""
        if self.account_emails:
            return self.account_emails
        
        # デフォルトアカウントを返す
        from ...infrastructure.config.settings import settings
        return settings.available_accounts


@dataclass
class CollectMeetingsResponseDTO:
    """議事録収集レスポンスDTO"""
    
    success: bool
    message: str
    collected_count: int
    updated_count: int
    skipped_count: int
    account_results: Dict[str, Dict[str, Any]]
    errors: List[str]
    
    @classmethod
    def create_success(
        cls,
        collected_count: int,
        updated_count: int,
        skipped_count: int,
        account_results: Dict[str, Dict[str, Any]]
    ) -> 'CollectMeetingsResponseDTO':
        """成功レスポンスを作成"""
        return cls(
            success=True,
            message=f"Successfully collected {collected_count} meetings",
            collected_count=collected_count,
            updated_count=updated_count,
            skipped_count=skipped_count,
            account_results=account_results,
            errors=[]
        )
    
    @classmethod
    def create_error(cls, errors: List[str]) -> 'CollectMeetingsResponseDTO':
        """エラーレスポンスを作成"""
        return cls(
            success=False,
            message="Meeting collection failed",
            collected_count=0,
            updated_count=0,
            skipped_count=0,
            account_results={},
            errors=errors
        )
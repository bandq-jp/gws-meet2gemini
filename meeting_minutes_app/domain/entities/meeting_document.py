from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from ..value_objects.account_email import AccountEmail
from ..value_objects.document_id import DocumentId
from ..value_objects.meeting_metadata import MeetingMetadata


@dataclass
class MeetingDocument:
    """議事録ドキュメントエンティティ"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    document_id: DocumentId = None
    account_email: AccountEmail = None
    metadata: MeetingMetadata = None
    text_content: str = ""
    doc_structure: Optional[Dict[str, Any]] = None
    downloaded_at: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.document_id:
            raise ValueError("Document ID is required")
        
        if not self.account_email:
            raise ValueError("Account email is required")
        
        if not self.metadata:
            raise ValueError("Meeting metadata is required")
    
    @classmethod
    def create(
        cls,
        document_id: DocumentId,
        account_email: AccountEmail,
        metadata: MeetingMetadata,
        text_content: str,
        doc_structure: Optional[Dict[str, Any]] = None
    ) -> 'MeetingDocument':
        """新しい議事録ドキュメントを作成"""
        
        return cls(
            document_id=document_id,
            account_email=account_email,
            metadata=metadata,
            text_content=text_content,
            doc_structure=doc_structure
        )
    
    def update_content(self, text_content: str, doc_structure: Optional[Dict[str, Any]] = None):
        """コンテンツを更新"""
        self.text_content = text_content
        if doc_structure is not None:
            self.doc_structure = doc_structure
        self.updated_at = datetime.now()
    
    def is_same_document(self, other_document_id: DocumentId, other_account: AccountEmail) -> bool:
        """同一ドキュメントかどうかを判定"""
        return (
            self.document_id == other_document_id and
            self.account_email == other_account
        )
    
    def has_content_changed(self, new_modified_time: str) -> bool:
        """コンテンツが変更されているかどうかを判定"""
        return self.metadata.modified_time != new_modified_time
    
    def get_safe_filename(self) -> str:
        """安全なファイル名を生成"""
        import re
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', self.metadata.title)
        timestamp = self.downloaded_at.strftime("%Y%m%d_%H%M%S")
        return f"{safe_title}_{self.document_id.value}_{timestamp}"
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "document_id": self.document_id.value,
            "account_email": self.account_email.value,
            "metadata": {
                "title": self.metadata.title,
                "date_time": self.metadata.date_time.isoformat() if self.metadata.date_time else None,
                "web_view_link": self.metadata.web_view_link,
                "created_time": self.metadata.created_time,
                "modified_time": self.metadata.modified_time,
                "owner_email": self.metadata.owner_email,
                "invited_accounts": self.metadata.invited_accounts
            },
            "text_content": self.text_content,
            "doc_structure": self.doc_structure,
            "downloaded_at": self.downloaded_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, MeetingDocument):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
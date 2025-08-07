from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.meeting_document import MeetingDocument
from ..value_objects.account_email import AccountEmail
from ..value_objects.document_id import DocumentId


class MeetingRepository(ABC):
    """議事録リポジトリのインターフェース"""
    
    @abstractmethod
    async def save(self, meeting_document: MeetingDocument) -> MeetingDocument:
        """議事録ドキュメントを保存"""
        pass
    
    @abstractmethod
    async def find_by_id(self, meeting_id: str) -> Optional[MeetingDocument]:
        """IDで議事録ドキュメントを検索"""
        pass
    
    @abstractmethod
    async def find_by_document_id_and_account(
        self, 
        document_id: DocumentId, 
        account_email: AccountEmail
    ) -> Optional[MeetingDocument]:
        """ドキュメントIDとアカウントで議事録ドキュメントを検索（重複チェック用）"""
        pass
    
    @abstractmethod
    async def find_all(
        self,
        account_email: Optional[AccountEmail] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MeetingDocument]:
        """議事録ドキュメント一覧を取得"""
        pass
    
    @abstractmethod
    async def find_by_account(
        self,
        account_email: AccountEmail,
        limit: int = 100,
        offset: int = 0
    ) -> List[MeetingDocument]:
        """指定アカウントの議事録ドキュメント一覧を取得"""
        pass
    
    @abstractmethod
    async def update(self, meeting_document: MeetingDocument) -> MeetingDocument:
        """議事録ドキュメントを更新"""
        pass
    
    @abstractmethod
    async def delete(self, meeting_id: str) -> bool:
        """議事録ドキュメントを削除"""
        pass
    
    @abstractmethod
    async def exists(self, document_id: DocumentId, account_email: AccountEmail) -> bool:
        """指定されたドキュメントIDとアカウントの組み合わせが存在するかチェック"""
        pass
    
    @abstractmethod
    async def count_by_account(self, account_email: Optional[AccountEmail] = None) -> int:
        """議事録ドキュメント数をカウント"""
        pass
    
    @abstractmethod
    async def find_recent(
        self,
        account_email: Optional[AccountEmail] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[MeetingDocument]:
        """最近の議事録ドキュメントを取得"""
        pass
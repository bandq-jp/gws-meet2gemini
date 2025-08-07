from abc import ABC, abstractmethod
from typing import List, Optional
from ..entities.structured_data import StructuredData


class StructuredDataRepository(ABC):
    """構造化データリポジトリのインターフェース"""
    
    @abstractmethod
    async def save(self, structured_data: StructuredData) -> StructuredData:
        """構造化データを保存"""
        pass
    
    @abstractmethod
    async def find_by_id(self, structured_data_id: str) -> Optional[StructuredData]:
        """IDで構造化データを検索"""
        pass
    
    @abstractmethod
    async def find_by_meeting_document_id(self, meeting_document_id: str) -> Optional[StructuredData]:
        """議事録ドキュメントIDで構造化データを検索"""
        pass
    
    @abstractmethod
    async def find_all(
        self,
        extraction_status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[StructuredData]:
        """構造化データ一覧を取得"""
        pass
    
    @abstractmethod
    async def update(self, structured_data: StructuredData) -> StructuredData:
        """構造化データを更新"""
        pass
    
    @abstractmethod
    async def delete(self, structured_data_id: str) -> bool:
        """構造化データを削除"""
        pass
    
    @abstractmethod
    async def exists_for_meeting_document(self, meeting_document_id: str) -> bool:
        """指定された議事録ドキュメントの構造化データが存在するかチェック"""
        pass
    
    @abstractmethod
    async def find_pending_extractions(self, limit: int = 50) -> List[StructuredData]:
        """抽出待ちの構造化データを取得"""
        pass
    
    @abstractmethod
    async def find_failed_extractions(self, limit: int = 50) -> List[StructuredData]:
        """抽出失敗の構造化データを取得"""
        pass
    
    @abstractmethod
    async def count_by_status(self, extraction_status: str) -> int:
        """ステータス別の構造化データ数をカウント"""
        pass
    
    @abstractmethod
    async def find_completed_extractions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[StructuredData]:
        """抽出完了済みの構造化データを取得"""
        pass
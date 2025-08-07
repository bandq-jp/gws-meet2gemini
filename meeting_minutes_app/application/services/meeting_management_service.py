from typing import List, Optional
import logging

from ...domain.entities.meeting_document import MeetingDocument
from ...domain.repositories.meeting_repository import MeetingRepository
from ...domain.value_objects.account_email import AccountEmail
from ..dto.meeting_dto import MeetingDocumentDTO, MeetingDocumentDetailDTO, MeetingListResponseDTO

logger = logging.getLogger(__name__)


class MeetingManagementService:
    """議事録管理サービス"""
    
    def __init__(self, meeting_repository: MeetingRepository):
        self._meeting_repository = meeting_repository
    
    async def get_meeting_list(
        self,
        account_email: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> MeetingListResponseDTO:
        """
        議事録一覧を取得
        
        Args:
            account_email: フィルタするアカウントメール（指定なしで全件）
            page: ページ番号（1から開始）
            page_size: 1ページあたりの件数
            
        Returns:
            議事録一覧のレスポンス
        """
        logger.info(f"Getting meeting list - account: {account_email}, page: {page}, page_size: {page_size}")
        
        # ページングのオフセット計算
        offset = (page - 1) * page_size
        
        # アカウントメールの値オブジェクト変換
        account_email_vo = None
        if account_email:
            try:
                account_email_vo = AccountEmail(account_email)
            except ValueError as e:
                logger.error(f"Invalid account email: {account_email}")
                # 無効なメールアドレスの場合は空の結果を返す
                return MeetingListResponseDTO.create([], 0, page, page_size)
        
        # 議事録一覧取得
        meetings = await self._meeting_repository.find_all(
            account_email=account_email_vo,
            limit=page_size,
            offset=offset
        )
        
        # 総件数取得
        total_count = await self._meeting_repository.count_by_account(account_email_vo)
        
        # DTOに変換
        meeting_dtos = [MeetingDocumentDTO.from_entity(meeting) for meeting in meetings]
        
        return MeetingListResponseDTO.create(
            meeting_dtos, total_count, page, page_size
        )
    
    async def get_meeting_detail(self, meeting_id: str) -> Optional[MeetingDocumentDetailDTO]:
        """
        指定IDの議事録詳細を取得
        
        Args:
            meeting_id: 議事録ドキュメントID
            
        Returns:
            議事録詳細DTO、見つからない場合はNone
        """
        logger.info(f"Getting meeting detail for ID: {meeting_id}")
        
        meeting = await self._meeting_repository.find_by_id(meeting_id)
        
        if not meeting:
            logger.warning(f"Meeting not found: {meeting_id}")
            return None
        
        return MeetingDocumentDetailDTO.from_entity(meeting)
    
    async def get_meetings_by_account(
        self,
        account_email: str,
        page: int = 1,
        page_size: int = 20
    ) -> MeetingListResponseDTO:
        """
        指定アカウントの議事録一覧を取得
        
        Args:
            account_email: アカウントメール
            page: ページ番号（1から開始）
            page_size: 1ページあたりの件数
            
        Returns:
            議事録一覧のレスポンス
        """
        return await self.get_meeting_list(account_email, page, page_size)
    
    async def get_recent_meetings(
        self,
        account_email: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[MeetingDocumentDTO]:
        """
        最近の議事録を取得
        
        Args:
            account_email: フィルタするアカウントメール
            days: 何日前まで取得するか
            limit: 最大取得件数
            
        Returns:
            最近の議事録DTOリスト
        """
        logger.info(f"Getting recent meetings - account: {account_email}, days: {days}, limit: {limit}")
        
        # アカウントメールの値オブジェクト変換
        account_email_vo = None
        if account_email:
            try:
                account_email_vo = AccountEmail(account_email)
            except ValueError as e:
                logger.error(f"Invalid account email: {account_email}")
                return []
        
        # 最近の議事録取得
        recent_meetings = await self._meeting_repository.find_recent(
            account_email=account_email_vo,
            days=days,
            limit=limit
        )
        
        # DTOに変換
        return [MeetingDocumentDTO.from_entity(meeting) for meeting in recent_meetings]
    
    async def search_meetings(
        self,
        query: str,
        account_email: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> MeetingListResponseDTO:
        """
        議事録を検索（将来の拡張用メソッド）
        
        Args:
            query: 検索クエリ
            account_email: フィルタするアカウントメール
            page: ページ番号
            page_size: 1ページあたりの件数
            
        Returns:
            検索結果の議事録一覧
        """
        # 現在は単純な一覧取得を返す
        # 将来的には全文検索などを実装する
        logger.info(f"Search not yet implemented, returning regular list for query: {query}")
        return await self.get_meeting_list(account_email, page, page_size)
    
    async def delete_meeting(self, meeting_id: str) -> bool:
        """
        議事録を削除
        
        Args:
            meeting_id: 議事録ドキュメントID
            
        Returns:
            削除成功の真偽値
        """
        logger.info(f"Deleting meeting: {meeting_id}")
        
        success = await self._meeting_repository.delete(meeting_id)
        
        if success:
            logger.info(f"Successfully deleted meeting: {meeting_id}")
        else:
            logger.warning(f"Failed to delete meeting: {meeting_id}")
        
        return success
    
    async def get_meeting_statistics(
        self,
        account_email: Optional[str] = None
    ) -> dict:
        """
        議事録の統計情報を取得
        
        Args:
            account_email: フィルタするアカウントメール
            
        Returns:
            統計情報の辞書
        """
        logger.info(f"Getting meeting statistics for account: {account_email}")
        
        # アカウントメールの値オブジェクト変換
        account_email_vo = None
        if account_email:
            try:
                account_email_vo = AccountEmail(account_email)
            except ValueError as e:
                logger.error(f"Invalid account email: {account_email}")
                return {
                    "total_count": 0,
                    "recent_count": 0,
                    "accounts": []
                }
        
        # 総件数取得
        total_count = await self._meeting_repository.count_by_account(account_email_vo)
        
        # 最近30日の件数取得
        recent_meetings = await self._meeting_repository.find_recent(
            account_email=account_email_vo,
            days=30,
            limit=1000  # 大きな値で件数をカウント
        )
        recent_count = len(recent_meetings)
        
        # アカウント別の統計（全件対象の場合）
        accounts_stats = []
        if not account_email:
            from ...infrastructure.config.settings import settings
            for account in settings.available_accounts:
                try:
                    account_vo = AccountEmail(account)
                    account_count = await self._meeting_repository.count_by_account(account_vo)
                    accounts_stats.append({
                        "email": account,
                        "count": account_count
                    })
                except Exception as e:
                    logger.error(f"Failed to get stats for account {account}: {e}")
        
        return {
            "total_count": total_count,
            "recent_count": recent_count,
            "accounts": accounts_stats
        }
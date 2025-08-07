from typing import Optional, List
import logging

from ..services.meeting_management_service import MeetingManagementService
from ..dto.meeting_dto import MeetingListResponseDTO, MeetingDocumentDTO

logger = logging.getLogger(__name__)


class GetMeetingListUseCase:
    """議事録一覧取得ユースケース"""
    
    def __init__(self, meeting_management_service: MeetingManagementService):
        self._meeting_management_service = meeting_management_service
    
    async def execute(
        self,
        account_email: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> MeetingListResponseDTO:
        """
        議事録一覧取得を実行
        
        Args:
            account_email: フィルタするアカウントメール（指定なしで全件）
            page: ページ番号（1から開始）
            page_size: 1ページあたりの件数
            
        Returns:
            議事録一覧のレスポンス
        """
        logger.info(
            f"Executing get meeting list use case - "
            f"account: {account_email}, "
            f"page: {page}, "
            f"page_size: {page_size}"
        )
        
        # 入力値検証
        if page < 1:
            logger.warning(f"Invalid page number: {page}, using page 1")
            page = 1
        
        if page_size < 1:
            logger.warning(f"Invalid page size: {page_size}, using page_size 20")
            page_size = 20
        
        if page_size > 100:
            logger.warning(f"Page size too large: {page_size}, using page_size 100")
            page_size = 100
        
        try:
            response = await self._meeting_management_service.get_meeting_list(
                account_email, page, page_size
            )
            
            logger.info(
                f"Meeting list retrieved - "
                f"count: {len(response.meetings)}, "
                f"total: {response.total_count}, "
                f"page: {response.page}"
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Failed to get meeting list: {str(e)}"
            logger.error(error_msg)
            
            # エラーの場合は空のレスポンスを返す
            return MeetingListResponseDTO.create([], 0, page, page_size)
    
    async def execute_for_account(
        self,
        account_email: str,
        page: int = 1,
        page_size: int = 20
    ) -> MeetingListResponseDTO:
        """
        特定アカウントの議事録一覧取得を実行
        
        Args:
            account_email: 対象アカウントメール
            page: ページ番号（1から開始）
            page_size: 1ページあたりの件数
            
        Returns:
            議事録一覧のレスポンス
        """
        return await self.execute(account_email, page, page_size)
    
    async def execute_recent(
        self,
        account_email: Optional[str] = None,
        days: int = 30,
        limit: int = 50
    ) -> List[MeetingDocumentDTO]:
        """
        最近の議事録一覧を取得
        
        Args:
            account_email: フィルタするアカウントメール
            days: 何日前まで取得するか
            limit: 最大取得件数
            
        Returns:
            最近の議事録DTOリスト
        """
        logger.info(
            f"Executing get recent meetings use case - "
            f"account: {account_email}, "
            f"days: {days}, "
            f"limit: {limit}"
        )
        
        # 入力値検証
        if days < 1:
            logger.warning(f"Invalid days: {days}, using days 30")
            days = 30
        
        if limit < 1:
            logger.warning(f"Invalid limit: {limit}, using limit 50")
            limit = 50
        
        if limit > 200:
            logger.warning(f"Limit too large: {limit}, using limit 200")
            limit = 200
        
        try:
            recent_meetings = await self._meeting_management_service.get_recent_meetings(
                account_email, days, limit
            )
            
            logger.info(f"Recent meetings retrieved - count: {len(recent_meetings)}")
            
            return recent_meetings
            
        except Exception as e:
            error_msg = f"Failed to get recent meetings: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def execute_statistics(
        self,
        account_email: Optional[str] = None
    ) -> dict:
        """
        議事録統計情報を取得
        
        Args:
            account_email: フィルタするアカウントメール
            
        Returns:
            統計情報の辞書
        """
        logger.info(f"Executing get meeting statistics use case - account: {account_email}")
        
        try:
            statistics = await self._meeting_management_service.get_meeting_statistics(
                account_email
            )
            
            logger.info(
                f"Meeting statistics retrieved - "
                f"total: {statistics.get('total_count', 0)}, "
                f"recent: {statistics.get('recent_count', 0)}"
            )
            
            return statistics
            
        except Exception as e:
            error_msg = f"Failed to get meeting statistics: {str(e)}"
            logger.error(error_msg)
            
            # エラーの場合はデフォルト値を返す
            return {
                "total_count": 0,
                "recent_count": 0,
                "accounts": []
            }
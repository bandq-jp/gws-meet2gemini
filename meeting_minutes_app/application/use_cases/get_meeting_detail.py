from typing import Optional
import logging

from ..services.meeting_management_service import MeetingManagementService
from ..dto.meeting_dto import MeetingDocumentDetailDTO

logger = logging.getLogger(__name__)


class GetMeetingDetailUseCase:
    """議事録詳細取得ユースケース"""
    
    def __init__(self, meeting_management_service: MeetingManagementService):
        self._meeting_management_service = meeting_management_service
    
    async def execute(self, meeting_id: str) -> Optional[MeetingDocumentDetailDTO]:
        """
        議事録詳細取得を実行
        
        Args:
            meeting_id: 議事録ドキュメントID
            
        Returns:
            議事録詳細DTO、見つからない場合はNone
        """
        logger.info(f"Executing get meeting detail use case - meeting_id: {meeting_id}")
        
        # 入力値検証
        if not meeting_id or not meeting_id.strip():
            logger.error("Meeting ID is required")
            return None
        
        meeting_id = meeting_id.strip()
        
        try:
            detail = await self._meeting_management_service.get_meeting_detail(meeting_id)
            
            if detail:
                logger.info(f"Meeting detail retrieved for ID: {meeting_id}")
            else:
                logger.warning(f"Meeting not found for ID: {meeting_id}")
            
            return detail
            
        except Exception as e:
            error_msg = f"Failed to get meeting detail for {meeting_id}: {str(e)}"
            logger.error(error_msg)
            return None
    
    async def execute_with_validation(
        self, 
        meeting_id: str,
        account_email: Optional[str] = None
    ) -> Optional[MeetingDocumentDetailDTO]:
        """
        議事録詳細取得をアカウント検証付きで実行
        
        Args:
            meeting_id: 議事録ドキュメントID
            account_email: アクセス権限を確認するアカウントメール
            
        Returns:
            議事録詳細DTO、見つからないまたはアクセス権限がない場合はNone
        """
        logger.info(
            f"Executing get meeting detail with validation - "
            f"meeting_id: {meeting_id}, account_email: {account_email}"
        )
        
        # 基本的な詳細取得
        detail = await self.execute(meeting_id)
        
        if not detail:
            return None
        
        # アカウント検証（指定されている場合）
        if account_email:
            if detail.account_email != account_email:
                logger.warning(
                    f"Access denied for account {account_email} "
                    f"to meeting owned by {detail.account_email}"
                )
                return None
        
        return detail
    
    async def check_meeting_exists(self, meeting_id: str) -> bool:
        """
        議事録が存在するかどうかをチェック
        
        Args:
            meeting_id: 議事録ドキュメントID
            
        Returns:
            存在するかどうかの真偽値
        """
        logger.info(f"Checking if meeting exists - meeting_id: {meeting_id}")
        
        try:
            detail = await self.execute(meeting_id)
            exists = detail is not None
            
            logger.info(f"Meeting exists check - meeting_id: {meeting_id}, exists: {exists}")
            return exists
            
        except Exception as e:
            logger.error(f"Failed to check meeting existence for {meeting_id}: {str(e)}")
            return False
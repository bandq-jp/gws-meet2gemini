from typing import List, Optional
import logging

from ..services.meeting_collection_service import MeetingCollectionService
from ..dto.meeting_dto import CollectMeetingsRequestDTO, CollectMeetingsResponseDTO

logger = logging.getLogger(__name__)


class CollectMeetingsUseCase:
    """議事録収集ユースケース"""
    
    def __init__(self, meeting_collection_service: MeetingCollectionService):
        self._meeting_collection_service = meeting_collection_service
    
    async def execute(
        self,
        account_emails: Optional[List[str]] = None,
        force_update: bool = False,
        include_doc_structure: bool = False
    ) -> CollectMeetingsResponseDTO:
        """
        議事録収集を実行
        
        Args:
            account_emails: 対象アカウントメール一覧（Noneで全アカウント）
            force_update: 既存ファイルを強制更新するかどうか
            include_doc_structure: Google Docs API構造を含めるかどうか
            
        Returns:
            収集結果のレスポンス
        """
        logger.info(
            f"Executing collect meetings use case - "
            f"accounts: {account_emails}, "
            f"force_update: {force_update}, "
            f"include_doc_structure: {include_doc_structure}"
        )
        
        # リクエストDTOを作成
        request = CollectMeetingsRequestDTO(
            account_emails=account_emails,
            force_update=force_update,
            include_doc_structure=include_doc_structure
        )
        
        # アプリケーションサービスを呼び出し
        try:
            response = await self._meeting_collection_service.collect_meetings(request)
            
            logger.info(
                f"Meeting collection completed - "
                f"collected: {response.collected_count}, "
                f"updated: {response.updated_count}, "
                f"skipped: {response.skipped_count}, "
                f"success: {response.success}"
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Failed to execute collect meetings use case: {str(e)}"
            logger.error(error_msg)
            return CollectMeetingsResponseDTO.create_error([error_msg])
    
    async def execute_for_single_account(
        self,
        account_email: str,
        force_update: bool = False,
        include_doc_structure: bool = False
    ) -> CollectMeetingsResponseDTO:
        """
        単一アカウントの議事録収集を実行
        
        Args:
            account_email: 対象アカウントメール
            force_update: 既存ファイルを強制更新するかどうか
            include_doc_structure: Google Docs API構造を含めるかどうか
            
        Returns:
            収集結果のレスポンス
        """
        return await self.execute(
            account_emails=[account_email],
            force_update=force_update,
            include_doc_structure=include_doc_structure
        )
    
    async def execute_for_all_accounts(
        self,
        force_update: bool = False,
        include_doc_structure: bool = False
    ) -> CollectMeetingsResponseDTO:
        """
        全アカウントの議事録収集を実行
        
        Args:
            force_update: 既存ファイルを強制更新するかどうか
            include_doc_structure: Google Docs API構造を含めるかどうか
            
        Returns:
            収集結果のレスポンス
        """
        return await self.execute(
            account_emails=None,  # 全アカウント
            force_update=force_update,
            include_doc_structure=include_doc_structure
        )
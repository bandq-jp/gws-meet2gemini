from typing import Optional
from ..entities.meeting_document import MeetingDocument
from ..repositories.meeting_repository import MeetingRepository
from ..value_objects.account_email import AccountEmail
from ..value_objects.document_id import DocumentId


class MeetingDuplicateChecker:
    """議事録の重複チェックを行うドメインサービス"""
    
    def __init__(self, meeting_repository: MeetingRepository):
        self._meeting_repository = meeting_repository
    
    async def check_duplicate(
        self,
        document_id: DocumentId,
        account_email: AccountEmail
    ) -> Optional[MeetingDocument]:
        """
        重複する議事録ドキュメントをチェック
        
        Args:
            document_id: GoogleドキュメントID
            account_email: アカウントメール
            
        Returns:
            重複する議事録ドキュメントがあればそれを返す、なければNone
        """
        return await self._meeting_repository.find_by_document_id_and_account(
            document_id, account_email
        )
    
    async def should_update_existing(
        self,
        existing_document: MeetingDocument,
        new_modified_time: str
    ) -> bool:
        """
        既存ドキュメントを更新すべきかどうかを判定
        
        Args:
            existing_document: 既存の議事録ドキュメント
            new_modified_time: 新しい更新日時
            
        Returns:
            更新すべきならTrue
        """
        return existing_document.has_content_changed(new_modified_time)
    
    async def is_duplicate_allowed(
        self,
        document_id: DocumentId,
        account_email: AccountEmail,
        force_update: bool = False
    ) -> bool:
        """
        重複を許可するかどうかを判定
        
        Args:
            document_id: GoogleドキュメントID
            account_email: アカウントメール
            force_update: 強制更新フラグ
            
        Returns:
            重複を許可（処理継続）するならTrue
        """
        existing_document = await self.check_duplicate(document_id, account_email)
        
        if existing_document is None:
            # 重複なし、新規作成OK
            return True
        
        if force_update:
            # 強制更新モード
            return True
        
        # 既存ドキュメントがある場合は許可しない
        return False
    
    async def get_duplicate_resolution_action(
        self,
        document_id: DocumentId,
        account_email: AccountEmail,
        new_modified_time: str,
        force_update: bool = False
    ) -> tuple[str, Optional[MeetingDocument]]:
        """
        重複解決のアクションを決定
        
        Args:
            document_id: GoogleドキュメントID
            account_email: アカウントメール
            new_modified_time: 新しい更新日時
            force_update: 強制更新フラグ
            
        Returns:
            (action, existing_document) のタプル
            action: "create", "update", "skip"
        """
        existing_document = await self.check_duplicate(document_id, account_email)
        
        if existing_document is None:
            return ("create", None)
        
        if force_update:
            return ("update", existing_document)
        
        if await self.should_update_existing(existing_document, new_modified_time):
            return ("update", existing_document)
        
        return ("skip", existing_document)
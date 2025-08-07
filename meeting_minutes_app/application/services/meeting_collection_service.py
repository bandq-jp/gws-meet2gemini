from typing import List, Dict, Any
import asyncio
import logging

from ...domain.entities.meeting_document import MeetingDocument
from ...domain.repositories.meeting_repository import MeetingRepository
from ...domain.services.meeting_duplicate_checker import MeetingDuplicateChecker
from ...domain.value_objects.account_email import AccountEmail
from ...domain.value_objects.document_id import DocumentId
from ...domain.value_objects.meeting_metadata import MeetingMetadata
from ...infrastructure.external.google_drive_client import GoogleDriveClient
from ...infrastructure.external.google_docs_client import GoogleDocsClient
from ...infrastructure.config.settings import settings
from ..dto.meeting_dto import CollectMeetingsRequestDTO, CollectMeetingsResponseDTO

logger = logging.getLogger(__name__)


class MeetingCollectionService:
    """議事録収集サービス"""
    
    def __init__(
        self,
        meeting_repository: MeetingRepository,
        duplicate_checker: MeetingDuplicateChecker,
        google_drive_client: GoogleDriveClient,
        google_docs_client: GoogleDocsClient
    ):
        self._meeting_repository = meeting_repository
        self._duplicate_checker = duplicate_checker
        self._google_drive_client = google_drive_client
        self._google_docs_client = google_docs_client
    
    async def collect_meetings(
        self, 
        request: CollectMeetingsRequestDTO
    ) -> CollectMeetingsResponseDTO:
        """
        議事録を収集してデータベースに保存
        
        Args:
            request: 収集リクエスト
            
        Returns:
            収集結果のレスポンス
        """
        account_emails = request.get_account_emails()
        
        logger.info(f"Starting meeting collection for accounts: {account_emails}")
        
        collected_count = 0
        updated_count = 0
        skipped_count = 0
        account_results = {}
        errors = []
        
        # 各アカウントごとに議事録を収集
        tasks = []
        for account_email in account_emails:
            task = self._collect_meetings_for_account(
                account_email,
                request.force_update,
                request.include_doc_structure
            )
            tasks.append((account_email, task))
        
        # 並列実行
        for account_email, task in tasks:
            try:
                result = await task
                account_results[account_email] = result
                
                collected_count += result['collected_count']
                updated_count += result['updated_count']
                skipped_count += result['skipped_count']
                
                if result['errors']:
                    errors.extend([f"{account_email}: {error}" for error in result['errors']])
                
            except Exception as e:
                error_msg = f"Failed to collect meetings for {account_email}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
                
                account_results[account_email] = {
                    'collected_count': 0,
                    'updated_count': 0,
                    'skipped_count': 0,
                    'errors': [str(e)]
                }
        
        if errors:
            return CollectMeetingsResponseDTO.create_error(errors)
        
        return CollectMeetingsResponseDTO.create_success(
            collected_count, updated_count, skipped_count, account_results
        )
    
    async def _collect_meetings_for_account(
        self,
        account_email: str,
        force_update: bool,
        include_doc_structure: bool
    ) -> Dict[str, Any]:
        """指定アカウントの議事録を収集"""
        
        logger.info(f"Collecting meetings for account: {account_email}")
        
        collected_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        try:
            # Meet Recordings フォルダを検索
            folders = await self._google_drive_client.find_folders_by_keyword(
                account_email,
                settings.target_folder_keyword,
                settings.case_sensitive_search
            )
            
            if not folders:
                logger.warning(f"No Meet Recordings folder found for {account_email}")
                return {
                    'collected_count': 0,
                    'updated_count': 0,
                    'skipped_count': 0,
                    'errors': ["Meet Recordings folder not found"]
                }
            
            # 各Meet Recordingsフォルダ内のドキュメントを処理
            for folder_id in folders:
                try:
                    files = await self._google_drive_client.list_files_in_folder(
                        account_email, folder_id
                    )
                    
                    # Googleドキュメントのみをフィルタ
                    google_docs = [
                        f for f in files 
                        if f["mimeType"] == "application/vnd.google-apps.document"
                    ]
                    
                    logger.info(f"Found {len(google_docs)} documents in folder {folder_id}")
                    
                    # 各ドキュメントを処理
                    for doc_file in google_docs:
                        try:
                            result = await self._process_document(
                                account_email,
                                doc_file,
                                force_update,
                                include_doc_structure
                            )
                            
                            if result['action'] == 'collected':
                                collected_count += 1
                            elif result['action'] == 'updated':
                                updated_count += 1
                            elif result['action'] == 'skipped':
                                skipped_count += 1
                            
                        except Exception as e:
                            error_msg = f"Failed to process document {doc_file['id']}: {str(e)}"
                            errors.append(error_msg)
                            logger.error(error_msg)
                
                except Exception as e:
                    error_msg = f"Failed to process folder {folder_id}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        except Exception as e:
            error_msg = f"Failed to collect meetings for account {account_email}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
        
        return {
            'collected_count': collected_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'errors': errors
        }
    
    async def _process_document(
        self,
        account_email: str,
        doc_file: Dict[str, Any],
        force_update: bool,
        include_doc_structure: bool
    ) -> Dict[str, str]:
        """個別ドキュメントを処理"""
        
        document_id = DocumentId(doc_file['id'])
        account_email_vo = AccountEmail(account_email)
        
        # 重複チェック
        action, existing_document = await self._duplicate_checker.get_duplicate_resolution_action(
            document_id,
            account_email_vo,
            doc_file['modifiedTime'],
            force_update
        )
        
        if action == "skip":
            logger.info(f"Skipping document {doc_file['id']} (no changes)")
            return {'action': 'skipped'}
        
        # ドキュメントコンテンツを取得
        text_content = await self._google_drive_client.export_document_as_text(
            account_email, doc_file['id']
        )
        
        # ドキュメント構造を取得（オプション）
        doc_structure = None
        if include_doc_structure:
            doc_structure = await self._google_docs_client.get_document_structure(
                account_email, doc_file['id']
            )
        
        # メタデータを作成
        metadata = MeetingMetadata.from_google_doc_metadata(
            doc_file['name'],
            doc_file['webViewLink'],
            doc_file['createdTime'],
            doc_file['modifiedTime'],
            doc_file.get('owners', []),
            []  # invited_accounts は後で拡張
        )
        
        if action == "create":
            # 新規作成
            meeting_document = MeetingDocument.create(
                document_id,
                account_email_vo,
                metadata,
                text_content,
                doc_structure
            )
            
            await self._meeting_repository.save(meeting_document)
            logger.info(f"Created new document {doc_file['id']}")
            return {'action': 'collected'}
        
        elif action == "update":
            # 既存ドキュメント更新
            existing_document.update_content(text_content, doc_structure)
            existing_document.metadata = metadata
            
            await self._meeting_repository.update(existing_document)
            logger.info(f"Updated document {doc_file['id']}")
            return {'action': 'updated'}
        
        return {'action': 'unknown'}
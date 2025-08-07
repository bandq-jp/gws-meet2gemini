from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

# Domain
from ...domain.services.meeting_duplicate_checker import MeetingDuplicateChecker
from ...domain.services.structured_extraction_service import StructuredExtractionService

# Application
from ...application.services.meeting_collection_service import MeetingCollectionService
from ...application.services.meeting_management_service import MeetingManagementService
from ...application.services.structured_analysis_service import StructuredAnalysisService
from ...application.use_cases.collect_meetings import CollectMeetingsUseCase
from ...application.use_cases.get_meeting_list import GetMeetingListUseCase
from ...application.use_cases.get_meeting_detail import GetMeetingDetailUseCase
from ...application.use_cases.process_structured_data import ProcessStructuredDataUseCase

# Infrastructure
from ..database.connection import get_database_session
from ..database.repositories.meeting_repository_impl import MeetingRepositoryImpl
from ..database.repositories.structured_data_repository_impl import StructuredDataRepositoryImpl
from ..auth.google_auth import GoogleAuthService
from ..external.google_drive_client import GoogleDriveClient
from ..external.google_docs_client import GoogleDocsClient
from ..external.gemini_client import GeminiClient


class DependencyContainer:
    """依存性注入コンテナ"""
    
    def __init__(self):
        self._google_auth_service = None
        self._google_drive_client = None
        self._google_docs_client = None
        self._gemini_client = None
    
    def get_google_auth_service(self) -> GoogleAuthService:
        """Google認証サービスを取得（シングルトン）"""
        if self._google_auth_service is None:
            self._google_auth_service = GoogleAuthService()
        return self._google_auth_service
    
    def get_google_drive_client(self) -> GoogleDriveClient:
        """Google Drive クライアントを取得（シングルトン）"""
        if self._google_drive_client is None:
            self._google_drive_client = GoogleDriveClient(self.get_google_auth_service())
        return self._google_drive_client
    
    def get_google_docs_client(self) -> GoogleDocsClient:
        """Google Docs クライアントを取得（シングルトン）"""
        if self._google_docs_client is None:
            self._google_docs_client = GoogleDocsClient(self.get_google_auth_service())
        return self._google_docs_client
    
    def get_gemini_client(self) -> GeminiClient:
        """Gemini クライアントを取得（シングルトン）"""
        if self._gemini_client is None:
            self._gemini_client = GeminiClient()
        return self._gemini_client
    
    # リポジトリ（セッション依存）
    def get_meeting_repository(self, session: AsyncSession) -> MeetingRepositoryImpl:
        """議事録リポジトリを取得"""
        return MeetingRepositoryImpl(session)
    
    def get_structured_data_repository(self, session: AsyncSession) -> StructuredDataRepositoryImpl:
        """構造化データリポジトリを取得"""
        return StructuredDataRepositoryImpl(session)
    
    # ドメインサービス（セッション依存）
    def get_meeting_duplicate_checker(self, session: AsyncSession) -> MeetingDuplicateChecker:
        """重複チェックサービスを取得"""
        meeting_repository = self.get_meeting_repository(session)
        return MeetingDuplicateChecker(meeting_repository)
    
    def get_structured_extraction_service(self) -> StructuredExtractionService:
        """構造化抽出サービスを取得"""
        gemini_client = self.get_gemini_client()
        return StructuredExtractionService(gemini_client)
    
    # アプリケーションサービス（セッション依存）
    def get_meeting_collection_service(self, session: AsyncSession) -> MeetingCollectionService:
        """議事録収集サービスを取得"""
        meeting_repository = self.get_meeting_repository(session)
        duplicate_checker = self.get_meeting_duplicate_checker(session)
        google_drive_client = self.get_google_drive_client()
        google_docs_client = self.get_google_docs_client()
        
        return MeetingCollectionService(
            meeting_repository,
            duplicate_checker,
            google_drive_client,
            google_docs_client
        )
    
    def get_meeting_management_service(self, session: AsyncSession) -> MeetingManagementService:
        """議事録管理サービスを取得"""
        meeting_repository = self.get_meeting_repository(session)
        return MeetingManagementService(meeting_repository)
    
    def get_structured_analysis_service(self, session: AsyncSession) -> StructuredAnalysisService:
        """構造化分析サービスを取得"""
        meeting_repository = self.get_meeting_repository(session)
        structured_data_repository = self.get_structured_data_repository(session)
        extraction_service = self.get_structured_extraction_service()
        
        return StructuredAnalysisService(
            meeting_repository,
            structured_data_repository,
            extraction_service
        )
    
    # ユースケース（セッション依存）
    def get_collect_meetings_use_case(self, session: AsyncSession) -> CollectMeetingsUseCase:
        """議事録収集ユースケースを取得"""
        service = self.get_meeting_collection_service(session)
        return CollectMeetingsUseCase(service)
    
    def get_meeting_list_use_case(self, session: AsyncSession) -> GetMeetingListUseCase:
        """議事録一覧取得ユースケースを取得"""
        service = self.get_meeting_management_service(session)
        return GetMeetingListUseCase(service)
    
    def get_meeting_detail_use_case(self, session: AsyncSession) -> GetMeetingDetailUseCase:
        """議事録詳細取得ユースケースを取得"""
        service = self.get_meeting_management_service(session)
        return GetMeetingDetailUseCase(service)
    
    def get_process_structured_data_use_case(self, session: AsyncSession) -> ProcessStructuredDataUseCase:
        """構造化データ処理ユースケースを取得"""
        service = self.get_structured_analysis_service(session)
        return ProcessStructuredDataUseCase(service)


# グローバルコンテナインスタンス
container = DependencyContainer()


# FastAPI 依存性注入用の関数群
async def get_collect_meetings_use_case(
    session: AsyncSession = Depends(get_database_session)
) -> CollectMeetingsUseCase:
    """議事録収集ユースケースの依存性注入"""
    return container.get_collect_meetings_use_case(session)


async def get_meeting_list_use_case(
    session: AsyncSession = Depends(get_database_session)
) -> GetMeetingListUseCase:
    """議事録一覧取得ユースケースの依存性注入"""
    return container.get_meeting_list_use_case(session)


async def get_meeting_detail_use_case(
    session: AsyncSession = Depends(get_database_session)
) -> GetMeetingDetailUseCase:
    """議事録詳細取得ユースケースの依存性注入"""
    return container.get_meeting_detail_use_case(session)


async def get_process_structured_data_use_case(
    session: AsyncSession = Depends(get_database_session)
) -> ProcessStructuredDataUseCase:
    """構造化データ処理ユースケースの依存性注入"""
    return container.get_process_structured_data_use_case(session)
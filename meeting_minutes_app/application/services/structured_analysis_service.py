from typing import Optional, List
import logging

from ...domain.entities.structured_data import StructuredData
from ...domain.repositories.meeting_repository import MeetingRepository
from ...domain.repositories.structured_data_repository import StructuredDataRepository
from ...domain.services.structured_extraction_service import StructuredExtractionService
from ..dto.structured_data_dto import (
    StructuredDataDTO,
    StructuredDataSummaryDTO,
    AnalyzeStructuredDataRequestDTO,
    AnalyzeStructuredDataResponseDTO
)

logger = logging.getLogger(__name__)


class StructuredAnalysisService:
    """構造化データ分析サービス"""
    
    def __init__(
        self,
        meeting_repository: MeetingRepository,
        structured_data_repository: StructuredDataRepository,
        extraction_service: StructuredExtractionService
    ):
        self._meeting_repository = meeting_repository
        self._structured_data_repository = structured_data_repository
        self._extraction_service = extraction_service
    
    async def analyze_meeting_document(
        self,
        request: AnalyzeStructuredDataRequestDTO
    ) -> AnalyzeStructuredDataResponseDTO:
        """
        議事録ドキュメントを構造化分析
        
        Args:
            request: 分析リクエスト
            
        Returns:
            分析結果のレスポンス
        """
        logger.info(f"Starting structured analysis for meeting document: {request.meeting_document_id}")
        
        try:
            # 議事録ドキュメントを取得
            meeting_document = await self._meeting_repository.find_by_id(request.meeting_document_id)
            if not meeting_document:
                return AnalyzeStructuredDataResponseDTO.create_error(
                    [f"Meeting document not found: {request.meeting_document_id}"]
                )
            
            # 既存の構造化データをチェック
            existing_structured_data = await self._structured_data_repository.find_by_meeting_document_id(
                request.meeting_document_id
            )
            
            if existing_structured_data and not request.force_reanalysis:
                if existing_structured_data.is_extraction_completed():
                    logger.info(f"Structured data already exists and completed: {existing_structured_data.id}")
                    
                    quality_score = self._extraction_service.calculate_extraction_quality_score(
                        existing_structured_data
                    )
                    
                    return AnalyzeStructuredDataResponseDTO.create_success(
                        existing_structured_data.id,
                        existing_structured_data.extraction_status,
                        quality_score
                    )
            
            # 構造化データの抽出実行
            if existing_structured_data and request.force_reanalysis:
                # 既存データの再抽出
                structured_data = await self._extraction_service.re_extract(
                    meeting_document, existing_structured_data
                )
                await self._structured_data_repository.update(structured_data)
                logger.info(f"Re-extracted structured data: {structured_data.id}")
            else:
                # 新規抽出
                structured_data = await self._extraction_service.extract_from_meeting_document(
                    meeting_document
                )
                await self._structured_data_repository.save(structured_data)
                logger.info(f"Created new structured data: {structured_data.id}")
            
            # 品質スコア計算
            quality_score = None
            if structured_data.is_extraction_completed():
                quality_score = self._extraction_service.calculate_extraction_quality_score(
                    structured_data
                )
            
            return AnalyzeStructuredDataResponseDTO.create_success(
                structured_data.id,
                structured_data.extraction_status,
                quality_score
            )
            
        except Exception as e:
            error_msg = f"Failed to analyze meeting document {request.meeting_document_id}: {str(e)}"
            logger.error(error_msg)
            return AnalyzeStructuredDataResponseDTO.create_error([error_msg])
    
    async def get_structured_data(
        self,
        meeting_document_id: str
    ) -> Optional[StructuredDataDTO]:
        """
        指定議事録ドキュメントの構造化データを取得
        
        Args:
            meeting_document_id: 議事録ドキュメントID
            
        Returns:
            構造化データDTO、存在しない場合はNone
        """
        logger.info(f"Getting structured data for meeting document: {meeting_document_id}")
        
        structured_data = await self._structured_data_repository.find_by_meeting_document_id(
            meeting_document_id
        )
        
        if not structured_data:
            logger.warning(f"Structured data not found for meeting document: {meeting_document_id}")
            return None
        
        return StructuredDataDTO.from_entity(structured_data)
    
    async def get_structured_data_by_id(
        self,
        structured_data_id: str
    ) -> Optional[StructuredDataDTO]:
        """
        IDで構造化データを取得
        
        Args:
            structured_data_id: 構造化データID
            
        Returns:
            構造化データDTO、存在しない場合はNone
        """
        logger.info(f"Getting structured data by ID: {structured_data_id}")
        
        structured_data = await self._structured_data_repository.find_by_id(structured_data_id)
        
        if not structured_data:
            logger.warning(f"Structured data not found: {structured_data_id}")
            return None
        
        return StructuredDataDTO.from_entity(structured_data)
    
    async def get_completed_structured_data_list(
        self,
        page: int = 1,
        page_size: int = 20
    ) -> List[StructuredDataSummaryDTO]:
        """
        完了済み構造化データの一覧を取得
        
        Args:
            page: ページ番号（1から開始）
            page_size: 1ページあたりの件数
            
        Returns:
            構造化データ要約DTOのリスト
        """
        logger.info(f"Getting completed structured data list - page: {page}, page_size: {page_size}")
        
        # ページングのオフセット計算
        offset = (page - 1) * page_size
        
        completed_data_list = await self._structured_data_repository.find_completed_extractions(
            limit=page_size,
            offset=offset
        )
        
        return [StructuredDataSummaryDTO.from_entity(data) for data in completed_data_list]
    
    async def get_pending_extractions(self, limit: int = 50) -> List[StructuredDataSummaryDTO]:
        """
        抽出待ちの構造化データ一覧を取得
        
        Args:
            limit: 最大取得件数
            
        Returns:
            構造化データ要約DTOのリスト
        """
        logger.info(f"Getting pending extractions - limit: {limit}")
        
        pending_data_list = await self._structured_data_repository.find_pending_extractions(limit)
        
        return [StructuredDataSummaryDTO.from_entity(data) for data in pending_data_list]
    
    async def get_failed_extractions(self, limit: int = 50) -> List[StructuredDataSummaryDTO]:
        """
        抽出失敗の構造化データ一覧を取得
        
        Args:
            limit: 最大取得件数
            
        Returns:
            構造化データ要約DTOのリスト
        """
        logger.info(f"Getting failed extractions - limit: {limit}")
        
        failed_data_list = await self._structured_data_repository.find_failed_extractions(limit)
        
        return [StructuredDataSummaryDTO.from_entity(data) for data in failed_data_list]
    
    async def get_extraction_statistics(self) -> dict:
        """
        抽出処理の統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        logger.info("Getting extraction statistics")
        
        try:
            pending_count = await self._structured_data_repository.count_by_status("pending")
            completed_count = await self._structured_data_repository.count_by_status("completed")
            failed_count = await self._structured_data_repository.count_by_status("failed")
            
            total_count = pending_count + completed_count + failed_count
            
            # 成功率計算
            success_rate = 0.0
            if total_count > 0:
                success_rate = (completed_count / total_count) * 100
            
            return {
                "total_count": total_count,
                "pending_count": pending_count,
                "completed_count": completed_count,
                "failed_count": failed_count,
                "success_rate": round(success_rate, 2)
            }
        
        except Exception as e:
            logger.error(f"Failed to get extraction statistics: {e}")
            return {
                "total_count": 0,
                "pending_count": 0,
                "completed_count": 0,
                "failed_count": 0,
                "success_rate": 0.0
            }
    
    async def retry_failed_extraction(self, structured_data_id: str) -> AnalyzeStructuredDataResponseDTO:
        """
        失敗した構造化データの抽出をリトライ
        
        Args:
            structured_data_id: 構造化データID
            
        Returns:
            リトライ結果のレスポンス
        """
        logger.info(f"Retrying failed extraction for structured data: {structured_data_id}")
        
        try:
            # 構造化データを取得
            structured_data = await self._structured_data_repository.find_by_id(structured_data_id)
            if not structured_data:
                return AnalyzeStructuredDataResponseDTO.create_error(
                    [f"Structured data not found: {structured_data_id}"]
                )
            
            # 議事録ドキュメントを取得
            meeting_document = await self._meeting_repository.find_by_id(
                structured_data.meeting_document_id
            )
            if not meeting_document:
                return AnalyzeStructuredDataResponseDTO.create_error(
                    [f"Meeting document not found: {structured_data.meeting_document_id}"]
                )
            
            # 再抽出実行
            structured_data = await self._extraction_service.re_extract(
                meeting_document, structured_data
            )
            await self._structured_data_repository.update(structured_data)
            
            # 品質スコア計算
            quality_score = None
            if structured_data.is_extraction_completed():
                quality_score = self._extraction_service.calculate_extraction_quality_score(
                    structured_data
                )
            
            logger.info(f"Successfully retried extraction: {structured_data_id}")
            
            return AnalyzeStructuredDataResponseDTO.create_success(
                structured_data.id,
                structured_data.extraction_status,
                quality_score
            )
            
        except Exception as e:
            error_msg = f"Failed to retry extraction for {structured_data_id}: {str(e)}"
            logger.error(error_msg)
            return AnalyzeStructuredDataResponseDTO.create_error([error_msg])
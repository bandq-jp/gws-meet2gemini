from typing import Optional, List
import logging

from ..services.structured_analysis_service import StructuredAnalysisService
from ..dto.structured_data_dto import (
    StructuredDataDTO,
    StructuredDataSummaryDTO,
    AnalyzeStructuredDataRequestDTO,
    AnalyzeStructuredDataResponseDTO
)

logger = logging.getLogger(__name__)


class ProcessStructuredDataUseCase:
    """構造化データ処理ユースケース"""
    
    def __init__(self, structured_analysis_service: StructuredAnalysisService):
        self._structured_analysis_service = structured_analysis_service
    
    async def execute_analysis(
        self,
        meeting_document_id: str,
        force_reanalysis: bool = False
    ) -> AnalyzeStructuredDataResponseDTO:
        """
        構造化データ分析を実行
        
        Args:
            meeting_document_id: 議事録ドキュメントID
            force_reanalysis: 強制再分析フラグ
            
        Returns:
            分析結果のレスポンス
        """
        logger.info(
            f"Executing structured data analysis - "
            f"meeting_document_id: {meeting_document_id}, "
            f"force_reanalysis: {force_reanalysis}"
        )
        
        # 入力値検証
        if not meeting_document_id or not meeting_document_id.strip():
            logger.error("Meeting document ID is required")
            return AnalyzeStructuredDataResponseDTO.create_error(
                ["Meeting document ID is required"]
            )
        
        meeting_document_id = meeting_document_id.strip()
        
        # リクエストDTOを作成
        request = AnalyzeStructuredDataRequestDTO(
            meeting_document_id=meeting_document_id,
            force_reanalysis=force_reanalysis
        )
        
        try:
            response = await self._structured_analysis_service.analyze_meeting_document(request)
            
            logger.info(
                f"Structured data analysis completed - "
                f"success: {response.success}, "
                f"extraction_status: {response.extraction_status}, "
                f"quality_score: {response.quality_score}"
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Failed to execute structured data analysis: {str(e)}"
            logger.error(error_msg)
            return AnalyzeStructuredDataResponseDTO.create_error([error_msg])
    
    async def get_structured_data(
        self,
        meeting_document_id: str
    ) -> Optional[StructuredDataDTO]:
        """
        構造化データを取得
        
        Args:
            meeting_document_id: 議事録ドキュメントID
            
        Returns:
            構造化データDTO、存在しない場合はNone
        """
        logger.info(f"Getting structured data - meeting_document_id: {meeting_document_id}")
        
        if not meeting_document_id or not meeting_document_id.strip():
            logger.error("Meeting document ID is required")
            return None
        
        try:
            structured_data = await self._structured_analysis_service.get_structured_data(
                meeting_document_id.strip()
            )
            
            if structured_data:
                logger.info(f"Structured data retrieved for meeting: {meeting_document_id}")
            else:
                logger.warning(f"Structured data not found for meeting: {meeting_document_id}")
            
            return structured_data
            
        except Exception as e:
            error_msg = f"Failed to get structured data for {meeting_document_id}: {str(e)}"
            logger.error(error_msg)
            return None
    
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
        logger.info(f"Getting structured data by ID - structured_data_id: {structured_data_id}")
        
        if not structured_data_id or not structured_data_id.strip():
            logger.error("Structured data ID is required")
            return None
        
        try:
            structured_data = await self._structured_analysis_service.get_structured_data_by_id(
                structured_data_id.strip()
            )
            
            if structured_data:
                logger.info(f"Structured data retrieved by ID: {structured_data_id}")
            else:
                logger.warning(f"Structured data not found by ID: {structured_data_id}")
            
            return structured_data
            
        except Exception as e:
            error_msg = f"Failed to get structured data by ID {structured_data_id}: {str(e)}"
            logger.error(error_msg)
            return None
    
    async def get_completed_list(
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
        logger.info(
            f"Getting completed structured data list - "
            f"page: {page}, page_size: {page_size}"
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
            completed_list = await self._structured_analysis_service.get_completed_structured_data_list(
                page, page_size
            )
            
            logger.info(f"Completed structured data list retrieved - count: {len(completed_list)}")
            
            return completed_list
            
        except Exception as e:
            error_msg = f"Failed to get completed structured data list: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def get_pending_list(self, limit: int = 50) -> List[StructuredDataSummaryDTO]:
        """
        抽出待ちの構造化データ一覧を取得
        
        Args:
            limit: 最大取得件数
            
        Returns:
            構造化データ要約DTOのリスト
        """
        logger.info(f"Getting pending structured data list - limit: {limit}")
        
        if limit < 1:
            logger.warning(f"Invalid limit: {limit}, using limit 50")
            limit = 50
        
        if limit > 200:
            logger.warning(f"Limit too large: {limit}, using limit 200")
            limit = 200
        
        try:
            pending_list = await self._structured_analysis_service.get_pending_extractions(limit)
            
            logger.info(f"Pending structured data list retrieved - count: {len(pending_list)}")
            
            return pending_list
            
        except Exception as e:
            error_msg = f"Failed to get pending structured data list: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def get_failed_list(self, limit: int = 50) -> List[StructuredDataSummaryDTO]:
        """
        抽出失敗の構造化データ一覧を取得
        
        Args:
            limit: 最大取得件数
            
        Returns:
            構造化データ要約DTOのリスト
        """
        logger.info(f"Getting failed structured data list - limit: {limit}")
        
        if limit < 1:
            logger.warning(f"Invalid limit: {limit}, using limit 50")
            limit = 50
        
        if limit > 200:
            logger.warning(f"Limit too large: {limit}, using limit 200")
            limit = 200
        
        try:
            failed_list = await self._structured_analysis_service.get_failed_extractions(limit)
            
            logger.info(f"Failed structured data list retrieved - count: {len(failed_list)}")
            
            return failed_list
            
        except Exception as e:
            error_msg = f"Failed to get failed structured data list: {str(e)}"
            logger.error(error_msg)
            return []
    
    async def get_statistics(self) -> dict:
        """
        抽出処理の統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        logger.info("Getting structured data extraction statistics")
        
        try:
            statistics = await self._structured_analysis_service.get_extraction_statistics()
            
            logger.info(
                f"Extraction statistics retrieved - "
                f"total: {statistics.get('total_count', 0)}, "
                f"success_rate: {statistics.get('success_rate', 0)}%"
            )
            
            return statistics
            
        except Exception as e:
            error_msg = f"Failed to get extraction statistics: {str(e)}"
            logger.error(error_msg)
            
            return {
                "total_count": 0,
                "pending_count": 0,
                "completed_count": 0,
                "failed_count": 0,
                "success_rate": 0.0
            }
    
    async def retry_failed_extraction(
        self,
        structured_data_id: str
    ) -> AnalyzeStructuredDataResponseDTO:
        """
        失敗した構造化データの抽出をリトライ
        
        Args:
            structured_data_id: 構造化データID
            
        Returns:
            リトライ結果のレスポンス
        """
        logger.info(f"Retrying failed extraction - structured_data_id: {structured_data_id}")
        
        if not structured_data_id or not structured_data_id.strip():
            logger.error("Structured data ID is required")
            return AnalyzeStructuredDataResponseDTO.create_error(
                ["Structured data ID is required"]
            )
        
        try:
            response = await self._structured_analysis_service.retry_failed_extraction(
                structured_data_id.strip()
            )
            
            logger.info(
                f"Retry extraction completed - "
                f"success: {response.success}, "
                f"extraction_status: {response.extraction_status}"
            )
            
            return response
            
        except Exception as e:
            error_msg = f"Failed to retry extraction: {str(e)}"
            logger.error(error_msg)
            return AnalyzeStructuredDataResponseDTO.create_error([error_msg])
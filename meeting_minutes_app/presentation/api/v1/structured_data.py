from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import Optional, List
import logging

from ....application.use_cases.process_structured_data import ProcessStructuredDataUseCase
from ...schemas.structured_data_schemas import (
    AnalyzeStructuredDataRequest,
    AnalyzeStructuredDataResponse,
    StructuredDataListRequest,
    StructuredDataListResponse,
    StructuredDataDetailResponse,
    StructuredDataStatisticsResponse,
    BatchAnalysisResponse,
    RetryExtractionResponse,
    ExtractionQualityReportRequest,
    ExtractionQualityReportResponse,
    StructuredDataExportRequest,
    StructuredDataExportResponse,
    StructuredDataSchema,
    StructuredDataSummarySchema,
    StructuredDataBatchAnalysisRequest
)
from ...schemas.common_schemas import BaseResponse, BackgroundTaskResponse

logger = logging.getLogger(__name__)

# ルーター作成
router = APIRouter(prefix="/structured-data", tags=["structured-data"])


# 依存性注入プレースホルダー（後で実装）
async def get_process_structured_data_use_case() -> ProcessStructuredDataUseCase:
    """構造化データ処理ユースケースを取得"""
    raise NotImplementedError("Dependency injection not implemented yet")


@router.post("/analyze/{meeting_document_id}", response_model=AnalyzeStructuredDataResponse)
async def analyze_meeting_document(
    meeting_document_id: str,
    request: AnalyzeStructuredDataRequest,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    指定された議事録ドキュメントを構造化分析
    
    - **meeting_document_id**: 分析対象の議事録ドキュメントID
    - **force_reanalysis**: 既存の分析結果があっても強制的に再分析するかどうか
    """
    logger.info(f"Analyzing meeting document: {meeting_document_id}")
    
    try:
        response = await use_case.execute_analysis(
            meeting_document_id=meeting_document_id,
            force_reanalysis=request.force_reanalysis
        )
        
        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": response.message,
                    "errors": response.errors
                }
            )
        
        logger.info(f"Analysis completed: {response.structured_data_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to analyze meeting document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze meeting document: {str(e)}"
        )


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def batch_analyze_meetings(
    request: StructuredDataBatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    複数の議事録ドキュメントを一括で構造化分析
    
    - **meeting_document_ids**: 分析対象の議事録ドキュメントID一覧
    - **force_reanalysis**: 強制再分析フラグ
    """
    logger.info(f"Batch analyzing {len(request.meeting_document_ids)} meeting documents")
    
    try:
        success_count = 0
        failed_count = 0
        results = []
        
        # 各ドキュメントを順次処理
        for doc_id in request.meeting_document_ids:
            try:
                response = await use_case.execute_analysis(
                    meeting_document_id=doc_id,
                    force_reanalysis=request.force_reanalysis
                )
                
                if response.success:
                    success_count += 1
                    results.append({
                        "meeting_document_id": doc_id,
                        "status": "success",
                        "structured_data_id": response.structured_data_id,
                        "quality_score": response.quality_score
                    })
                else:
                    failed_count += 1
                    results.append({
                        "meeting_document_id": doc_id,
                        "status": "failed",
                        "errors": response.errors
                    })
                    
            except Exception as e:
                failed_count += 1
                results.append({
                    "meeting_document_id": doc_id,
                    "status": "failed",
                    "errors": [str(e)]
                })
        
        return BatchAnalysisResponse(
            success=success_count > 0,
            message=f"Batch analysis completed: {success_count} succeeded, {failed_count} failed",
            total_count=len(request.meeting_document_ids),
            success_count=success_count,
            failed_count=failed_count,
            results=results
        )
        
    except Exception as e:
        logger.error(f"Failed to execute batch analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute batch analysis: {str(e)}"
        )


@router.get("/meeting/{meeting_document_id}", response_model=StructuredDataDetailResponse)
async def get_structured_data_by_meeting(
    meeting_document_id: str,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    指定された議事録ドキュメントの構造化データを取得
    
    - **meeting_document_id**: 議事録ドキュメントID
    """
    logger.info(f"Getting structured data for meeting: {meeting_document_id}")
    
    try:
        structured_data = await use_case.get_structured_data(meeting_document_id)
        
        if not structured_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Structured data not found for meeting document: {meeting_document_id}"
            )
        
        return StructuredDataDetailResponse(
            structured_data=StructuredDataSchema(**structured_data.__dict__)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get structured data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get structured data: {str(e)}"
        )


@router.get("/{structured_data_id}", response_model=StructuredDataDetailResponse)
async def get_structured_data_by_id(
    structured_data_id: str,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    IDで構造化データを取得
    
    - **structured_data_id**: 構造化データID
    """
    logger.info(f"Getting structured data by ID: {structured_data_id}")
    
    try:
        structured_data = await use_case.get_structured_data_by_id(structured_data_id)
        
        if not structured_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Structured data not found: {structured_data_id}"
            )
        
        return StructuredDataDetailResponse(
            structured_data=StructuredDataSchema(**structured_data.__dict__)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get structured data by ID: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get structured data by ID: {str(e)}"
        )


@router.get("", response_model=StructuredDataListResponse)
async def get_structured_data_list(
    extraction_status: Optional[str] = Query(
        None, 
        description="抽出ステータスでフィルタ（pending/completed/failed）"
    ),
    page: int = Query(1, ge=1, description="ページ番号（1から開始）"),
    page_size: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    構造化データ一覧を取得
    
    - **extraction_status**: 抽出ステータスでフィルタ
    - **page**: ページ番号（1から開始）
    - **page_size**: 1ページあたりの件数
    """
    logger.info(f"Getting structured data list - status: {extraction_status}, page: {page}")
    
    try:
        if extraction_status == "completed":
            structured_data_list = await use_case.get_completed_list(page, page_size)
        elif extraction_status == "pending":
            structured_data_list = await use_case.get_pending_list(page_size * page)
        elif extraction_status == "failed":
            structured_data_list = await use_case.get_failed_list(page_size * page)
        else:
            # 全件取得（ページング対応）
            structured_data_list = await use_case.get_completed_list(page, page_size)
        
        # TODO: 適切なページネーション情報を計算
        total_count = len(structured_data_list)
        has_next = len(structured_data_list) == page_size
        
        return StructuredDataListResponse(
            structured_data=[
                StructuredDataSummarySchema(**data.__dict__)
                for data in structured_data_list
            ],
            pagination={
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "has_next": has_next
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get structured data list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get structured data list: {str(e)}"
        )


@router.get("/statistics", response_model=StructuredDataStatisticsResponse)
async def get_structured_data_statistics(
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    構造化データの統計情報を取得
    """
    logger.info("Getting structured data statistics")
    
    try:
        statistics = await use_case.get_statistics()
        
        return StructuredDataStatisticsResponse(**statistics)
        
    except Exception as e:
        logger.error(f"Failed to get structured data statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get structured data statistics: {str(e)}"
        )


@router.post("/retry/{structured_data_id}", response_model=RetryExtractionResponse)
async def retry_failed_extraction(
    structured_data_id: str,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    失敗した構造化データの抽出をリトライ
    
    - **structured_data_id**: 構造化データID
    """
    logger.info(f"Retrying extraction for structured data: {structured_data_id}")
    
    try:
        response = await use_case.retry_failed_extraction(structured_data_id)
        
        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": response.message,
                    "errors": response.errors
                }
            )
        
        return RetryExtractionResponse(
            success=response.success,
            message=response.message,
            structured_data_id=response.structured_data_id,
            extraction_status=response.extraction_status,
            quality_score=response.quality_score
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retry extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retry extraction: {str(e)}"
        )


@router.post("/quality-report", response_model=ExtractionQualityReportResponse)
async def get_extraction_quality_report(
    request: ExtractionQualityReportRequest,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    抽出品質レポートを生成
    """
    logger.info(f"Generating extraction quality report")
    
    try:
        # TODO: 品質レポート生成を実装
        
        return ExtractionQualityReportResponse(
            report_period={
                "from": request.date_from.isoformat() if request.date_from else None,
                "to": request.date_to.isoformat() if request.date_to else None
            },
            overall_statistics={
                "total_extractions": 0,
                "average_quality_score": 0.0,
                "completion_rate": 0.0
            },
            quality_distribution={
                "excellent": 0,  # 0.8-1.0
                "good": 0,       # 0.6-0.8
                "fair": 0,       # 0.4-0.6
                "poor": 0        # 0.0-0.4
            },
            field_completion_rates={},
            recommendations=[],
            details=[] if request.include_details else None
        )
        
    except Exception as e:
        logger.error(f"Failed to generate quality report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate quality report: {str(e)}"
        )


@router.post("/export", response_model=StructuredDataExportResponse)
async def export_structured_data(
    request: StructuredDataExportRequest,
    background_tasks: BackgroundTasks,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    構造化データをエクスポート
    """
    logger.info(f"Exporting structured data - format: {request.format}")
    
    try:
        # TODO: エクスポート機能を実装
        
        from datetime import datetime, timedelta
        
        return StructuredDataExportResponse(
            success=True,
            message="Export completed",
            export_url="/downloads/structured_data_export.json",  # プレースホルダー
            file_size=2048,  # プレースホルダー
            record_count=25,  # プレースホルダー
            expires_at=datetime.now() + timedelta(days=7)
        )
        
    except Exception as e:
        logger.error(f"Failed to export structured data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export structured data: {str(e)}"
        )


@router.delete("/{structured_data_id}", response_model=BaseResponse)
async def delete_structured_data(
    structured_data_id: str,
    use_case: ProcessStructuredDataUseCase = Depends(get_process_structured_data_use_case)
):
    """
    構造化データを削除
    
    - **structured_data_id**: 構造化データID
    """
    logger.info(f"Deleting structured data: {structured_data_id}")
    
    try:
        # TODO: 削除機能を実装
        
        return BaseResponse(
            success=True,
            message=f"Structured data deleted: {structured_data_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to delete structured data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete structured data: {str(e)}"
        )
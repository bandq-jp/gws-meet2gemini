from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from typing import Optional, List
import logging

from ....application.use_cases.collect_meetings import CollectMeetingsUseCase
from ....application.use_cases.get_meeting_list import GetMeetingListUseCase
from ....application.use_cases.get_meeting_detail import GetMeetingDetailUseCase
from ...schemas.meeting_schemas import (
    CollectMeetingsRequest,
    CollectMeetingsResponse,
    MeetingListRequest,
    MeetingListResponse,
    MeetingDetailResponse,
    RecentMeetingsRequest,
    MeetingStatisticsResponse,
    DeleteMeetingResponse,
    MeetingBatchOperationRequest,
    MeetingBatchOperationResponse,
    MeetingExportRequest,
    MeetingExportResponse,
    MeetingDocumentSchema,
    MeetingDocumentDetailSchema,
    MeetingSearchRequest
)
from ...schemas.common_schemas import BaseResponse, ErrorResponse, BackgroundTaskResponse

logger = logging.getLogger(__name__)

# ルーター作成
router = APIRouter(prefix="/meetings", tags=["meetings"])


# 依存性注入プレースホルダー（後で実装）
async def get_collect_meetings_use_case() -> CollectMeetingsUseCase:
    """議事録収集ユースケースを取得"""
    raise NotImplementedError("Dependency injection not implemented yet")


async def get_meeting_list_use_case() -> GetMeetingListUseCase:
    """議事録一覧取得ユースケースを取得"""
    raise NotImplementedError("Dependency injection not implemented yet")


async def get_meeting_detail_use_case() -> GetMeetingDetailUseCase:
    """議事録詳細取得ユースケースを取得"""
    raise NotImplementedError("Dependency injection not implemented yet")


@router.post("/collect", response_model=CollectMeetingsResponse)
async def collect_meetings(
    request: CollectMeetingsRequest,
    background_tasks: BackgroundTasks,
    use_case: CollectMeetingsUseCase = Depends(get_collect_meetings_use_case)
):
    """
    議事録を収集してデータベースに保存
    
    - **account_emails**: 対象アカウントメール一覧（指定なしで全アカウント）
    - **force_update**: 既存ファイルを強制更新するかどうか
    - **include_doc_structure**: Google Docs API構造を含めるかどうか
    """
    logger.info(f"Collecting meetings request: {request}")
    
    try:
        # 同期実行（小規模な場合）
        response = await use_case.execute(
            account_emails=request.account_emails,
            force_update=request.force_update,
            include_doc_structure=request.include_doc_structure
        )
        
        if not response.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": response.message,
                    "errors": response.errors
                }
            )
        
        logger.info(f"Meeting collection completed: {response.collected_count} collected")
        return response
        
    except Exception as e:
        logger.error(f"Failed to collect meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to collect meetings: {str(e)}"
        )


@router.post("/collect/background", response_model=BackgroundTaskResponse)
async def collect_meetings_background(
    request: CollectMeetingsRequest,
    background_tasks: BackgroundTasks,
    use_case: CollectMeetingsUseCase = Depends(get_collect_meetings_use_case)
):
    """
    議事録収集をバックグラウンドタスクとして実行
    """
    logger.info(f"Starting background meeting collection: {request}")
    
    def run_collection():
        """バックグラウンドで実行される収集処理"""
        # 非同期処理をバックグラウンドで実行
        # 実際の実装では、Celery や RQ などのタスクキューを使用することを推奨
        pass
    
    background_tasks.add_task(run_collection)
    
    return BackgroundTaskResponse(
        success=True,
        message="Meeting collection started in background",
        task_id=None,  # 実際のタスクIDを返す
        status="started"
    )


@router.get("", response_model=MeetingListResponse)
async def get_meeting_list(
    account_email: Optional[str] = Query(None, description="フィルタするアカウントメール"),
    page: int = Query(1, ge=1, description="ページ番号（1から開始）"),
    page_size: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    use_case: GetMeetingListUseCase = Depends(get_meeting_list_use_case)
):
    """
    議事録一覧を取得
    
    - **account_email**: フィルタするアカウントメール（指定なしで全件）
    - **page**: ページ番号（1から開始）
    - **page_size**: 1ページあたりの件数
    """
    logger.info(f"Getting meeting list - account: {account_email}, page: {page}")
    
    try:
        response = await use_case.execute(account_email, page, page_size)
        
        return MeetingListResponse(
            meetings=[
                MeetingDocumentSchema(**meeting.__dict__) 
                for meeting in response.meetings
            ],
            pagination=response.__dict__
        )
        
    except Exception as e:
        logger.error(f"Failed to get meeting list: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get meeting list: {str(e)}"
        )


@router.get("/recent", response_model=List[MeetingDocumentSchema])
async def get_recent_meetings(
    account_email: Optional[str] = Query(None, description="フィルタするアカウントメール"),
    days: int = Query(30, ge=1, le=365, description="何日前まで取得するか"),
    limit: int = Query(50, ge=1, le=200, description="最大取得件数"),
    use_case: GetMeetingListUseCase = Depends(get_meeting_list_use_case)
):
    """
    最近の議事録一覧を取得
    
    - **account_email**: フィルタするアカウントメール
    - **days**: 何日前まで取得するか
    - **limit**: 最大取得件数
    """
    logger.info(f"Getting recent meetings - account: {account_email}, days: {days}")
    
    try:
        meetings = await use_case.execute_recent(account_email, days, limit)
        
        return [MeetingDocumentSchema(**meeting.__dict__) for meeting in meetings]
        
    except Exception as e:
        logger.error(f"Failed to get recent meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get recent meetings: {str(e)}"
        )


@router.get("/statistics", response_model=MeetingStatisticsResponse)
async def get_meeting_statistics(
    account_email: Optional[str] = Query(None, description="フィルタするアカウントメール"),
    use_case: GetMeetingListUseCase = Depends(get_meeting_list_use_case)
):
    """
    議事録の統計情報を取得
    
    - **account_email**: フィルタするアカウントメール
    """
    logger.info(f"Getting meeting statistics - account: {account_email}")
    
    try:
        statistics = await use_case.execute_statistics(account_email)
        
        return MeetingStatisticsResponse(**statistics)
        
    except Exception as e:
        logger.error(f"Failed to get meeting statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get meeting statistics: {str(e)}"
        )


@router.get("/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(
    meeting_id: str,
    use_case: GetMeetingDetailUseCase = Depends(get_meeting_detail_use_case)
):
    """
    指定IDの議事録詳細を取得
    
    - **meeting_id**: 議事録ドキュメントID
    """
    logger.info(f"Getting meeting detail - meeting_id: {meeting_id}")
    
    try:
        detail = await use_case.execute(meeting_id)
        
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting not found: {meeting_id}"
            )
        
        return MeetingDetailResponse(
            meeting=MeetingDocumentDetailSchema(**detail.__dict__)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get meeting detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get meeting detail: {str(e)}"
        )


@router.delete("/{meeting_id}", response_model=DeleteMeetingResponse)
async def delete_meeting(
    meeting_id: str,
    use_case: GetMeetingListUseCase = Depends(get_meeting_list_use_case)
):
    """
    指定IDの議事録を削除
    
    - **meeting_id**: 議事録ドキュメントID
    """
    logger.info(f"Deleting meeting - meeting_id: {meeting_id}")
    
    try:
        # TODO: 削除機能を実装
        # success = await use_case.delete_meeting(meeting_id)
        success = False  # プレースホルダー
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Meeting not found or could not be deleted: {meeting_id}"
            )
        
        return DeleteMeetingResponse(
            success=True,
            message="Meeting deleted successfully",
            meeting_id=meeting_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete meeting: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete meeting: {str(e)}"
        )


@router.post("/search", response_model=MeetingListResponse)
async def search_meetings(
    request: MeetingSearchRequest,
    use_case: GetMeetingListUseCase = Depends(get_meeting_list_use_case)
):
    """
    議事録を検索（将来拡張用）
    
    現在は通常の一覧取得と同じ動作をします。
    """
    logger.info(f"Searching meetings - query: {request.query}")
    
    try:
        # 現在は通常の一覧取得を実行
        response = await use_case.execute(
            request.account_email, 
            request.page, 
            request.page_size
        )
        
        return MeetingListResponse(
            meetings=[
                MeetingDocumentSchema(**meeting.__dict__) 
                for meeting in response.meetings
            ],
            pagination=response.__dict__
        )
        
    except Exception as e:
        logger.error(f"Failed to search meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search meetings: {str(e)}"
        )


@router.post("/batch", response_model=MeetingBatchOperationResponse)
async def batch_operation(
    request: MeetingBatchOperationRequest,
    use_case: GetMeetingListUseCase = Depends(get_meeting_list_use_case)
):
    """
    議事録の一括操作（削除・分析・エクスポート等）
    """
    logger.info(f"Batch operation - operation: {request.operation}, count: {len(request.meeting_ids)}")
    
    try:
        # TODO: 一括操作を実装
        
        return MeetingBatchOperationResponse(
            success=True,
            message="Batch operation completed",
            total_count=len(request.meeting_ids),
            success_count=0,  # プレースホルダー
            failed_count=0,   # プレースホルダー
            results=[]
        )
        
    except Exception as e:
        logger.error(f"Failed to execute batch operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute batch operation: {str(e)}"
        )


@router.post("/export", response_model=MeetingExportResponse)
async def export_meetings(
    request: MeetingExportRequest,
    background_tasks: BackgroundTasks,
    use_case: GetMeetingListUseCase = Depends(get_meeting_list_use_case)
):
    """
    議事録をエクスポート
    """
    logger.info(f"Exporting meetings - format: {request.format}")
    
    try:
        # TODO: エクスポート機能を実装
        
        from datetime import datetime, timedelta
        
        return MeetingExportResponse(
            success=True,
            message="Export completed",
            export_url="/downloads/meetings_export.json",  # プレースホルダー
            file_size=1024,  # プレースホルダー
            record_count=10,  # プレースホルダー
            expires_at=datetime.now() + timedelta(days=7)
        )
        
    except Exception as e:
        logger.error(f"Failed to export meetings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export meetings: {str(e)}"
        )
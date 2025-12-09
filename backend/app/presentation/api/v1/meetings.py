from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException, Body, Request, Response, status
from pydantic import BaseModel
import logging

from app.presentation.schemas.meeting import MeetingOut, MeetingListResponse, TranscriptUpdateIn
from app.application.use_cases.collect_meetings import CollectMeetingsUseCase
from app.infrastructure.background.job_tracker import JobTracker

from app.application.use_cases.get_meeting_list import GetMeetingListUseCase
from app.application.use_cases.get_meeting_list_paginated import GetMeetingListPaginatedUseCase
from app.application.use_cases.get_meeting_detail import GetMeetingDetailUseCase
from app.infrastructure.config.settings import get_settings
from app.infrastructure.gcp.tasks import enqueue_collect_meetings_task
from app.application.use_cases.update_meeting_transcript import UpdateMeetingTranscriptUseCase

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/collect", response_model=dict, status_code=202)
async def collect_meetings(
    accounts: Optional[List[str]] = Query(default=None),
    include_structure: bool = Query(default=False),
    force_update: bool = Query(default=False),
):
    """Kick off meeting collection in the background and return immediately."""
    use_case = CollectMeetingsUseCase()
    try:
        logger.info(
            "POST /api/v1/meetings/collect queued: accounts=%s include_structure=%s force_update=%s",
            accounts,
            include_structure,
            force_update,
        )
        job_id = JobTracker.create_job(
            name="collect_meetings",
            params={
                "accounts": accounts or [],
                "include_structure": include_structure,
                "force_update": force_update,
            },
        )
        JobTracker.mark_running(job_id, message="Collecting from Google Drive")

        import asyncio

        async def _run():
            try:
                await use_case.execute(
                    accounts,
                    include_structure=include_structure,
                    force_update=force_update,
                    job_id=job_id,
                )
            except Exception as e:  # pragma: no cover
                logger.exception("Background collect failed: %s", e)
                JobTracker.mark_failed(job_id, error=str(e))

        asyncio.create_task(_run())
        return {
            "message": "Meeting collection started (background).",
            "job_id": job_id,
            "status_url": f"/api/v1/meetings/collect/status/{job_id}",
        }
    except RuntimeError as e:
        logger.exception("Collect meetings queueing failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/collect/status/{job_id}", response_model=dict)
async def collect_status(job_id: str):
    data = JobTracker.get(job_id)
    if not data:
        raise HTTPException(status_code=404, detail="job not found")
    return data

@router.get("/", response_model=MeetingListResponse)
async def list_meetings_paginated(
    page: int = Query(default=1, ge=1, description="ページ番号（1から開始）"),
    page_size: int = Query(default=40, ge=1, le=40, description="1ページあたりのアイテム数（最大40）"),
    accounts: Optional[List[str]] = Query(default=None, description="フィルタ対象のアカウント一覧"),
    structured: Optional[bool] = Query(default=None, description="構造化済み(true)/未構造化(false)でフィルタ"),
    search: Optional[str] = Query(default=None, description="検索クエリ（タイトル、主催者で検索）")
):
    """軽量な議事録一覧をページネーション付きで取得（推奨）"""
    use_case = GetMeetingListPaginatedUseCase()
    try:
        return await use_case.execute(page, page_size, accounts, structured, search)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/legacy", response_model=List[MeetingOut])
async def list_meetings_legacy(
    accounts: Optional[List[str]] = Query(default=None),
    structured: Optional[bool] = Query(default=None, description="構造化済み(true)/未構造化(false)でフィルタ")
):
    """レガシー: 全データを含む議事録一覧取得（非推奨、互換性のため残存）"""
    use_case = GetMeetingListUseCase()
    try:
        return await use_case.execute(accounts, structured)
    except RuntimeError as e:
        # Supabase未設定時でもHTTP 400を返して原因を明示
        raise HTTPException(status_code=400, detail=str(e))
@router.get("/accounts", response_model=dict)
async def get_available_accounts():
    """Get available accounts for filtering"""
    settings = get_settings()
    return {"accounts": settings.impersonate_subjects}

@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting_detail(meeting_id: str):
    use_case = GetMeetingDetailUseCase()
    return await use_case.execute(meeting_id)

@router.put("/{meeting_id}/transcript", response_model=MeetingOut)
async def update_meeting_transcript(meeting_id: str, body: TranscriptUpdateIn = Body(...)):
    """議事録テキストを上書きし、必要なら既存の構造化データをクリア"""
    use_case = UpdateMeetingTranscriptUseCase()
    try:
        updated = use_case.execute(
            meeting_id=meeting_id,
            text_content=body.text_content,
            transcript_provider=body.transcript_provider,
            delete_structured=body.delete_structured,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="meeting not found")
        return updated
    except ValueError:
        raise HTTPException(status_code=404, detail="meeting not found")
    except Exception as e:
        logger.exception("Failed to update transcript: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/collect-task", response_model=dict, status_code=202)
async def enqueue_collect_meetings(
    accounts: Optional[List[str]] = Query(default=None),
    include_structure: bool = Query(default=False),
    force_update: bool = Query(default=False),
):
    """
    収集処理をCloud Tasksへエンキューする新エンドポイント。
    即時にjob_idを返し、statusURLで監視できる点は既存と同じ。
    """
    # 既存collectと同じくJobを作る（statusは既存の /collect/status/{job_id} を使う）
    job_id = JobTracker.create_job(
        name="collect_meetings(tasks)",
        params={
            "accounts": accounts or [],
            "include_structure": include_structure,
            "force_update": force_update,
        },
    )
    JobTracker.mark_running(job_id, message="Queued to Cloud Tasks")

    # ワーカーに渡すpayload
    payload = {
        "job_id": job_id,
        "accounts": accounts or [],
        "include_structure": include_structure,
        "force_update": force_update,
    }

    task_name = None  # 連続実行の重複を抑止したい場合は日付ベースのnameを付ける
    try:
        task_fullname = enqueue_collect_meetings_task(payload, task_name=task_name)
    except Exception as e:
        JobTracker.mark_failed(job_id, error=f"enqueue failed: {e}")
        raise HTTPException(status_code=500, detail=f"Cloud Tasks enqueue failed: {e}")

    return {
        "message": "Enqueued to Cloud Tasks.",
        "job_id": job_id,
        "task_name": task_fullname,
        "status_url": f"/api/v1/meetings/collect/status/{job_id}",
    }


class CollectWorkerIn(BaseModel):
    job_id: str
    accounts: Optional[List[str]] = None
    include_structure: bool = False
    force_update: bool = False

@router.post("/collect/worker", status_code=204)
async def collect_worker(request: Request, body: CollectWorkerIn = Body(...)):
    """
    Cloud Tasks からのみ叩かれるワーカー受け口。
    - Cloud Run 側は認証必須（Run Invoker）にし、Cloud Tasks のSAのみ叩けるようにIAM制御
    - 追加でX-Cloud-Tasks-QueueNameヘッダ等を軽く検証（保険）
    """
    settings = get_settings()

    # Cloud Tasks 経由の共通ヘッダ（存在チェック）
    qhdr = request.headers.get("X-Cloud-Tasks-QueueName")
    if not qhdr and request.headers.get("X-Requested-By") != "cloud-tasks-enqueue":
        # ローカル検証などを許したい場合は APP_AUTH_TOKEN 等にフォールバックしても良い
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if settings.expected_queue_name and qhdr and qhdr != settings.expected_queue_name:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid queue")

    # 本体実行（既存UseCaseをそのまま呼ぶ）
    use_case = CollectMeetingsUseCase()
    try:
        await use_case.execute(
            body.accounts if body.accounts else None,
            include_structure=body.include_structure,
            force_update=body.force_update,
            job_id=body.job_id,
        )
        # UseCase 側で JobTracker.mark_success/failed まで面倒をみてくれる
        # （途中メトリクス更新もUseCase内で済む）
        return Response(status_code=204)
    except Exception as e:
        JobTracker.mark_failed(body.job_id, error=str(e))
        raise

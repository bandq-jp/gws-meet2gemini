from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
import logging

from app.presentation.schemas.meeting import MeetingOut, MeetingListResponse
from app.application.use_cases.collect_meetings import CollectMeetingsUseCase

from app.application.use_cases.get_meeting_list import GetMeetingListUseCase
from app.application.use_cases.get_meeting_list_paginated import GetMeetingListPaginatedUseCase
from app.application.use_cases.get_meeting_detail import GetMeetingDetailUseCase
from app.infrastructure.config.settings import get_settings

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

        import asyncio

        async def _run():
            try:
                await use_case.execute(
                    accounts,
                    include_structure=include_structure,
                    force_update=force_update,
                )
            except Exception as e:  # pragma: no cover
                logger.exception("Background collect failed: %s", e)

        asyncio.create_task(_run())
        return {"message": "Meeting collection started (background)."}
    except RuntimeError as e:
        logger.exception("Collect meetings queueing failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=MeetingListResponse)
async def list_meetings_paginated(
    page: int = Query(default=1, ge=1, description="ページ番号（1から開始）"),
    page_size: int = Query(default=40, ge=1, le=40, description="1ページあたりのアイテム数（最大40）"),
    accounts: Optional[List[str]] = Query(default=None, description="フィルタ対象のアカウント一覧"),
    structured: Optional[bool] = Query(default=None, description="構造化済み(true)/未構造化(false)でフィルタ")
):
    """軽量な議事録一覧をページネーション付きで取得（推奨）"""
    use_case = GetMeetingListPaginatedUseCase()
    try:
        return await use_case.execute(page, page_size, accounts, structured)
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

from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException
import logging

from app.presentation.schemas.meeting import MeetingOut
from app.application.use_cases.collect_meetings import CollectMeetingsUseCase

from app.application.use_cases.get_meeting_list import GetMeetingListUseCase
from app.application.use_cases.get_meeting_detail import GetMeetingDetailUseCase
from app.infrastructure.config.settings import get_settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/collect", response_model=dict)
async def collect_meetings(
    accounts: Optional[List[str]] = Query(default=None),
    include_structure: bool = Query(default=False),
    force_update: bool = Query(default=False),
):
    use_case = CollectMeetingsUseCase()
    try:
        logger.debug(
            "POST /api/v1/meetings/collect called: accounts=%s include_structure=%s force_update=%s",
            accounts,
            include_structure,
            force_update,
        )
        count = await use_case.execute(
            accounts, include_structure=include_structure, force_update=force_update
        )
        logger.debug("Meetings collected and stored: %d", count)
        return {"stored": count}
    except RuntimeError as e:
        logger.exception("Collect meetings failed: %s", e)
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[MeetingOut])
async def list_meetings(
    accounts: Optional[List[str]] = Query(default=None),
    structured: Optional[bool] = Query(default=None, description="構造化済み(true)/未構造化(false)でフィルタ")
):
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

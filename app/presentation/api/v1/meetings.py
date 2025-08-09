from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Query, HTTPException

from app.presentation.schemas.meeting import MeetingOut
from app.application.use_cases.collect_meetings import CollectMeetingsUseCase

from app.application.use_cases.get_meeting_list import GetMeetingListUseCase
from app.application.use_cases.get_meeting_detail import GetMeetingDetailUseCase

router = APIRouter()

@router.post("/collect", response_model=dict)
async def collect_meetings(
    accounts: Optional[List[str]] = Query(default=None),
    include_structure: bool = Query(default=False),
    force_update: bool = Query(default=False),
):
    use_case = CollectMeetingsUseCase()
    try:
        count = await use_case.execute(accounts, include_structure=include_structure, force_update=force_update)
        return {"stored": count}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[MeetingOut])
async def list_meetings(accounts: Optional[List[str]] = Query(default=None)):
    use_case = GetMeetingListUseCase()
    try:
        return await use_case.execute(accounts)
    except RuntimeError as e:
        # Supabase未設定時でもHTTP 400を返して原因を明示
        raise HTTPException(status_code=400, detail=str(e))
@router.get("/{meeting_id}", response_model=MeetingOut)
async def get_meeting_detail(meeting_id: str):
    use_case = GetMeetingDetailUseCase()
    return await use_case.execute(meeting_id)

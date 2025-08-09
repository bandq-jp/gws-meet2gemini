from __future__ import annotations
from fastapi import APIRouter

from app.application.use_cases.process_structured_data import ProcessStructuredDataUseCase
from app.application.use_cases.get_structured_data import GetStructuredDataUseCase
from app.presentation.schemas.structured import StructuredOut

router = APIRouter()

@router.post("/process/{meeting_id}", response_model=StructuredOut)
async def process_structured(meeting_id: str):
    use_case = ProcessStructuredDataUseCase()
    return await use_case.execute(meeting_id)

@router.get("/{meeting_id}", response_model=StructuredOut)
async def get_structured(meeting_id: str):
    use_case = GetStructuredDataUseCase()
    return await use_case.execute(meeting_id)

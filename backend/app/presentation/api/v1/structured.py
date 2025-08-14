from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.application.use_cases.process_structured_data import ProcessStructuredDataUseCase
from app.application.use_cases.get_structured_data import GetStructuredDataUseCase
from app.presentation.schemas.structured import StructuredOut, StructuredProcessRequest

router = APIRouter()

@router.post("/process/{meeting_id}", response_model=StructuredOut)
def process_structured(meeting_id: str, request: StructuredProcessRequest):
    try:
        use_case = ProcessStructuredDataUseCase()
        return use_case.execute(
            meeting_id=meeting_id,
            zoho_candidate_id=request.zoho_candidate_id,
            zoho_record_id=request.zoho_record_id,
            zoho_candidate_name=request.zoho_candidate_name,
            zoho_candidate_email=request.zoho_candidate_email,
            custom_schema_id=request.custom_schema_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{meeting_id}", response_model=StructuredOut)
async def get_structured(meeting_id: str):
    use_case = GetStructuredDataUseCase()
    return await use_case.execute(meeting_id)

from __future__ import annotations
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.presentation.schemas.candidate import (
    CandidateDetailOut,
    CandidateListResponse,
    CandidateMeetingsResponse,
    CandidateSummaryOut,
    JDDetailOut,
    JobMatchOut,
    JobMatchRequest,
    JobMatchResponse,
    LineMessageRequest,
    LineMessageResponse,
    LinkedMeetingOut,
    StructuredOutputBrief,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=CandidateListResponse)
def list_candidates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    sort_by: str = Query("registration_date"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """候補者一覧（Zoho CRM APP-hc）をページネーション付きで取得"""
    from app.application.use_cases.list_candidates import ListCandidatesUseCase

    try:
        use_case = ListCandidatesUseCase()
        result = use_case.execute(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            channel=channel,
            sort_by=sort_by,
            date_from=date_from,
            date_to=date_to,
        )
        return CandidateListResponse(
            items=[CandidateSummaryOut(**item) for item in result["items"]],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
            total_pages=result["total_pages"],
            has_next=result["has_next"],
            has_previous=result["has_previous"],
            filters=result.get("filters", {}),
        )
    except Exception as e:
        logger.error("[candidates] list failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jd/{jd_id}", response_model=JDDetailOut)
def get_jd_detail(
    jd_id: str,
    version: Optional[str] = Query(None, description="old (JOB) or new (JobDescription)"),
):
    """求人票(JD)の詳細を取得"""
    from app.application.use_cases.get_jd_detail import GetJDDetailUseCase

    try:
        use_case = GetJDDetailUseCase()
        result = use_case.execute(jd_id, version=version)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return JDDetailOut(id=jd_id, **{k: v for k, v in result.items() if k != "id"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[candidates] jd detail failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/line-message/generate", response_model=LineMessageResponse)
def generate_line_message(body: LineMessageRequest):
    """候補者向けLINEメッセージをAI生成"""
    from app.application.use_cases.generate_line_message import GenerateLineMessageUseCase

    try:
        use_case = GenerateLineMessageUseCase()
        result = use_case.execute(body.model_dump())
        return LineMessageResponse(**result)
    except Exception as e:
        logger.error("[candidates] line-message generate failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{record_id}", response_model=CandidateDetailOut)
def get_candidate_detail(record_id: str):
    """候補者詳細（Zohoレコード + 構造化データ + 関連議事録）"""
    from app.application.use_cases.get_candidate_detail import GetCandidateDetailUseCase

    try:
        use_case = GetCandidateDetailUseCase()
        result = use_case.execute(record_id)

        if "error" in result:
            raise HTTPException(status_code=404, detail=result["error"])

        return CandidateDetailOut(
            record_id=result["record_id"],
            zoho_record=result["zoho_record"],
            structured_outputs=[
                StructuredOutputBrief(**so) for so in result["structured_outputs"]
            ],
            linked_meetings=[
                LinkedMeetingOut(**m) for m in result["linked_meetings"]
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[candidates] detail failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{record_id}/meetings", response_model=CandidateMeetingsResponse)
def get_candidate_meetings(record_id: str):
    """候補者に紐づく議事録一覧"""
    from app.application.use_cases.get_candidate_meetings import GetCandidateMeetingsUseCase

    try:
        use_case = GetCandidateMeetingsUseCase()
        result = use_case.execute(record_id)

        return CandidateMeetingsResponse(
            items=[LinkedMeetingOut(**m) for m in result["items"]],
            total=result["total"],
        )
    except Exception as e:
        logger.error("[candidates] meetings failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{record_id}/job-match", response_model=JobMatchResponse)
def match_candidate_jobs(record_id: str, body: Optional[JobMatchRequest] = None):
    """候補者の求人マッチング（ADKエージェント活用 — Zoho JD + セマンティック + Mail/Slack）"""
    from app.application.use_cases.match_candidate_jobs import MatchCandidateJobsUseCase

    try:
        use_case = MatchCandidateJobsUseCase()
        overrides = {}
        jd_module_version = None
        if body:
            if body.transfer_reasons:
                overrides["transfer_reasons"] = body.transfer_reasons
            if body.desired_salary is not None:
                overrides["desired_salary"] = body.desired_salary
            if body.desired_locations:
                overrides["desired_locations"] = body.desired_locations
            overrides["limit"] = body.limit
            jd_module_version = body.jd_module_version

        result = use_case.execute(
            record_id,
            overrides=overrides,
            jd_module_version=jd_module_version,
        )

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        # Normalize recommended_jobs to JobMatchOut
        raw_jobs = result.get("recommended_jobs", [])
        jobs = [JobMatchOut(**j) for j in raw_jobs]

        return JobMatchResponse(
            candidate_profile=result.get("candidate_profile", {}),
            recommended_jobs=jobs,
            total_found=result.get("total_found", len(jobs)),
            analysis_text=result.get("analysis_text"),
            data_sources_used=result.get("data_sources_used", []),
            jd_module_version=result.get("jd_module_version"),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[candidates] job-match failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

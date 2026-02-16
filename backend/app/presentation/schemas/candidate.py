from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CandidateSummaryOut(BaseModel):
    record_id: str
    name: str
    status: Optional[str] = None
    channel: Optional[str] = None
    registration_date: Optional[str] = None
    modified_time: Optional[str] = None
    pic: Optional[str] = None
    linked_meetings_count: int = 0


class CandidateListResponse(BaseModel):
    items: List[CandidateSummaryOut]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool
    filters: Dict[str, List[str]] = Field(default_factory=dict)


class LinkedMeetingOut(BaseModel):
    meeting_id: str
    title: Optional[str] = None
    meeting_datetime: Optional[str] = None
    organizer_email: Optional[str] = None
    is_structured: bool = False


class StructuredOutputBrief(BaseModel):
    meeting_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None


class CandidateDetailOut(BaseModel):
    record_id: str
    zoho_record: Dict[str, Any] = Field(default_factory=dict)
    structured_outputs: List[StructuredOutputBrief] = Field(default_factory=list)
    linked_meetings: List[LinkedMeetingOut] = Field(default_factory=list)


class CandidateMeetingsResponse(BaseModel):
    items: List[LinkedMeetingOut]
    total: int


# --- Job Matching ---

class JobMatchRequest(BaseModel):
    transfer_reasons: Optional[str] = None
    desired_salary: Optional[int] = None
    desired_locations: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=20)
    jd_module_version: Optional[str] = Field(default=None, description="old (JOB) or new (JobDescription)")


class JobMatchOut(BaseModel):
    job_name: str = ""
    company_name: str = ""
    match_score: float = 0.0
    recommendation_reason: Optional[str] = None
    appeal_points: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    salary_range: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[str] = None
    position: Optional[str] = None
    hiring_appetite: Optional[str] = None
    source: str = "unknown"


class JobMatchResponse(BaseModel):
    candidate_profile: Dict[str, Any] = Field(default_factory=dict)
    recommended_jobs: List[JobMatchOut] = Field(default_factory=list)
    total_found: int = 0
    analysis_text: Optional[str] = None
    data_sources_used: List[str] = Field(default_factory=list)
    jd_module_version: Optional[str] = None

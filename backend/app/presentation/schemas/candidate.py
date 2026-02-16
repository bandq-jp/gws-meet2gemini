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
    jd_id: Optional[str] = None
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


# --- JD Detail ---

class JDDetailOut(BaseModel):
    id: str
    name: Optional[str] = None
    company: Optional[str] = None
    company_id: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    expected_salary: Optional[str] = None
    incentive: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[str] = None
    is_remote: Optional[bool] = None
    flex: Optional[str] = None
    is_flex: Optional[bool] = None
    overtime: Optional[str] = None
    age_max: Optional[int] = None
    education: Optional[str] = None
    exp_count_max: Optional[int] = None
    hr_experience: Optional[str] = None
    job_details: Optional[str] = None
    ideal_candidate: Optional[str] = None
    hiring_background: Optional[str] = None
    org_structure: Optional[str] = None
    after_career: Optional[str] = None
    category: Optional[str] = None
    position: Optional[str] = None
    hiring_appetite: Optional[str] = None
    benefits: Optional[str] = None
    holiday: Optional[str] = None
    annual_days_off: Optional[str] = None
    is_open: Optional[bool] = None
    fee: Optional[str] = None
    jd_manager: Optional[str] = None
    company_features: Optional[str] = None
    modified_time: Optional[str] = None
    module_version: Optional[str] = None


# --- LINE Message ---

class LineMessageRequest(BaseModel):
    job_name: str
    company_name: str
    appeal_points: List[str] = Field(default_factory=list)
    recommendation_reason: Optional[str] = None
    salary_range: Optional[str] = None
    location: Optional[str] = None
    remote: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_desires: Optional[str] = None


class LineMessageResponse(BaseModel):
    message: str
    char_count: int

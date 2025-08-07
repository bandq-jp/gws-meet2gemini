from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid


@dataclass
class StructuredData:
    """構造化データエンティティ"""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    meeting_document_id: str = None
    
    # 転職活動状況・エージェント関連
    transfer_activity_status: Optional[str] = None
    agent_count: Optional[str] = None
    current_agents: Optional[str] = None
    introduced_jobs: Optional[str] = None
    job_appeal_points: Optional[str] = None
    job_concerns: Optional[str] = None
    companies_in_selection: Optional[List[str]] = None
    other_offer_salary: Optional[str] = None
    other_company_intention: Optional[List[str]] = None
    
    # 転職理由・希望条件
    transfer_reasons: Optional[List[str]] = None
    transfer_trigger: Optional[List[str]] = None
    desired_timing: Optional[str] = None
    timing_details: Optional[str] = None
    current_job_status: Optional[str] = None
    transfer_status_memo: Optional[List[str]] = None
    transfer_priorities: Optional[List[str]] = None
    
    # 職歴・経験
    career_history: Optional[List[str]] = None
    current_duties: Optional[str] = None
    company_good_points: Optional[str] = None
    company_bad_points: Optional[str] = None
    enjoyed_work: Optional[str] = None
    difficult_work: Optional[str] = None
    
    # 希望業界・職種
    experience_industry: Optional[str] = None
    experience_field_hr: Optional[str] = None
    desired_industry: Optional[List[str]] = None
    industry_reason: Optional[List[str]] = None
    desired_position: Optional[List[str]] = None
    position_industry_reason: Optional[List[str]] = None
    
    # 年収・待遇条件
    current_salary: Optional[int] = None
    salary_breakdown: Optional[str] = None
    desired_first_year_salary: Optional[float] = None
    base_incentive_ratio: Optional[str] = None
    max_future_salary: Optional[str] = None
    salary_memo: Optional[List[str]] = None
    remote_time_memo: Optional[List[str]] = None
    ca_ra_focus: Optional[str] = None
    customer_acquisition: Optional[str] = None
    new_existing_ratio: Optional[str] = None
    
    # 企業文化・キャリアビジョン
    business_vision: Optional[List[str]] = None
    desired_employee_count: Optional[List[str]] = None
    culture_scale_memo: Optional[List[str]] = None
    career_vision: Optional[List[str]] = None
    
    # メタデータ
    extraction_metadata: Optional[Dict[str, Any]] = None
    extraction_status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.meeting_document_id:
            raise ValueError("Meeting document ID is required")
        
        # リストフィールドの初期化
        if self.companies_in_selection is None:
            self.companies_in_selection = []
        if self.other_company_intention is None:
            self.other_company_intention = []
        if self.transfer_reasons is None:
            self.transfer_reasons = []
        if self.transfer_trigger is None:
            self.transfer_trigger = []
        if self.transfer_status_memo is None:
            self.transfer_status_memo = []
        if self.transfer_priorities is None:
            self.transfer_priorities = []
        if self.career_history is None:
            self.career_history = []
        if self.desired_industry is None:
            self.desired_industry = []
        if self.industry_reason is None:
            self.industry_reason = []
        if self.desired_position is None:
            self.desired_position = []
        if self.position_industry_reason is None:
            self.position_industry_reason = []
        if self.salary_memo is None:
            self.salary_memo = []
        if self.remote_time_memo is None:
            self.remote_time_memo = []
        if self.business_vision is None:
            self.business_vision = []
        if self.desired_employee_count is None:
            self.desired_employee_count = []
        if self.culture_scale_memo is None:
            self.culture_scale_memo = []
        if self.career_vision is None:
            self.career_vision = []
    
    @classmethod
    def create(cls, meeting_document_id: str) -> 'StructuredData':
        """新しい構造化データを作成"""
        return cls(meeting_document_id=meeting_document_id)
    
    @classmethod
    def from_extracted_data(cls, meeting_document_id: str, extracted_data: Dict[str, Any]) -> 'StructuredData':
        """抽出されたデータから構造化データを作成"""
        structured_data = cls.create(meeting_document_id)
        structured_data.update_from_extracted_data(extracted_data)
        return structured_data
    
    def update_from_extracted_data(self, extracted_data: Dict[str, Any]):
        """抽出されたデータで構造化データを更新"""
        # 転職活動状況・エージェント関連
        self.transfer_activity_status = extracted_data.get('transfer_activity_status')
        self.agent_count = extracted_data.get('agent_count')
        self.current_agents = extracted_data.get('current_agents')
        self.introduced_jobs = extracted_data.get('introduced_jobs')
        self.job_appeal_points = extracted_data.get('job_appeal_points')
        self.job_concerns = extracted_data.get('job_concerns')
        self.companies_in_selection = extracted_data.get('companies_in_selection', [])
        self.other_offer_salary = extracted_data.get('other_offer_salary')
        self.other_company_intention = extracted_data.get('other_company_intention', [])
        
        # 転職理由・希望条件
        self.transfer_reasons = extracted_data.get('transfer_reasons', [])
        self.transfer_trigger = extracted_data.get('transfer_trigger', [])
        self.desired_timing = extracted_data.get('desired_timing')
        self.timing_details = extracted_data.get('timing_details')
        self.current_job_status = extracted_data.get('current_job_status')
        self.transfer_status_memo = extracted_data.get('transfer_status_memo', [])
        self.transfer_priorities = extracted_data.get('transfer_priorities', [])
        
        # 職歴・経験
        self.career_history = extracted_data.get('career_history', [])
        self.current_duties = extracted_data.get('current_duties')
        self.company_good_points = extracted_data.get('company_good_points')
        self.company_bad_points = extracted_data.get('company_bad_points')
        self.enjoyed_work = extracted_data.get('enjoyed_work')
        self.difficult_work = extracted_data.get('difficult_work')
        
        # 希望業界・職種
        self.experience_industry = extracted_data.get('experience_industry')
        self.experience_field_hr = extracted_data.get('experience_field_hr')
        self.desired_industry = extracted_data.get('desired_industry', [])
        self.industry_reason = extracted_data.get('industry_reason', [])
        self.desired_position = extracted_data.get('desired_position', [])
        self.position_industry_reason = extracted_data.get('position_industry_reason', [])
        
        # 年収・待遇条件
        self.current_salary = extracted_data.get('current_salary')
        self.salary_breakdown = extracted_data.get('salary_breakdown')
        self.desired_first_year_salary = extracted_data.get('desired_first_year_salary')
        self.base_incentive_ratio = extracted_data.get('base_incentive_ratio')
        self.max_future_salary = extracted_data.get('max_future_salary')
        self.salary_memo = extracted_data.get('salary_memo', [])
        self.remote_time_memo = extracted_data.get('remote_time_memo', [])
        self.ca_ra_focus = extracted_data.get('ca_ra_focus')
        self.customer_acquisition = extracted_data.get('customer_acquisition')
        self.new_existing_ratio = extracted_data.get('new_existing_ratio')
        
        # 企業文化・キャリアビジョン
        self.business_vision = extracted_data.get('business_vision', [])
        self.desired_employee_count = extracted_data.get('desired_employee_count', [])
        self.culture_scale_memo = extracted_data.get('culture_scale_memo', [])
        self.career_vision = extracted_data.get('career_vision', [])
        
        self.extraction_status = "completed"
        self.updated_at = datetime.now()
    
    def mark_extraction_failed(self, error_message: str):
        """抽出失敗をマーク"""
        self.extraction_status = "failed"
        self.extraction_metadata = {
            "error": error_message,
            "failed_at": datetime.now().isoformat()
        }
        self.updated_at = datetime.now()
    
    def is_extraction_completed(self) -> bool:
        """抽出が完了しているかどうか"""
        return self.extraction_status == "completed"
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "meeting_document_id": self.meeting_document_id,
            "transfer_activity_status": self.transfer_activity_status,
            "agent_count": self.agent_count,
            "current_agents": self.current_agents,
            "introduced_jobs": self.introduced_jobs,
            "job_appeal_points": self.job_appeal_points,
            "job_concerns": self.job_concerns,
            "companies_in_selection": self.companies_in_selection,
            "other_offer_salary": self.other_offer_salary,
            "other_company_intention": self.other_company_intention,
            "transfer_reasons": self.transfer_reasons,
            "transfer_trigger": self.transfer_trigger,
            "desired_timing": self.desired_timing,
            "timing_details": self.timing_details,
            "current_job_status": self.current_job_status,
            "transfer_status_memo": self.transfer_status_memo,
            "transfer_priorities": self.transfer_priorities,
            "career_history": self.career_history,
            "current_duties": self.current_duties,
            "company_good_points": self.company_good_points,
            "company_bad_points": self.company_bad_points,
            "enjoyed_work": self.enjoyed_work,
            "difficult_work": self.difficult_work,
            "experience_industry": self.experience_industry,
            "experience_field_hr": self.experience_field_hr,
            "desired_industry": self.desired_industry,
            "industry_reason": self.industry_reason,
            "desired_position": self.desired_position,
            "position_industry_reason": self.position_industry_reason,
            "current_salary": self.current_salary,
            "salary_breakdown": self.salary_breakdown,
            "desired_first_year_salary": self.desired_first_year_salary,
            "base_incentive_ratio": self.base_incentive_ratio,
            "max_future_salary": self.max_future_salary,
            "salary_memo": self.salary_memo,
            "remote_time_memo": self.remote_time_memo,
            "ca_ra_focus": self.ca_ra_focus,
            "customer_acquisition": self.customer_acquisition,
            "new_existing_ratio": self.new_existing_ratio,
            "business_vision": self.business_vision,
            "desired_employee_count": self.desired_employee_count,
            "culture_scale_memo": self.culture_scale_memo,
            "career_vision": self.career_vision,
            "extraction_metadata": self.extraction_metadata,
            "extraction_status": self.extraction_status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    def __eq__(self, other) -> bool:
        if not isinstance(other, StructuredData):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        return hash(self.id)
from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class StructuredDataDTO:
    """構造化データのDTO"""
    
    id: str
    meeting_document_id: str
    extraction_status: str
    
    # 転職活動状況・エージェント関連
    transfer_activity_status: Optional[str]
    agent_count: Optional[str]
    current_agents: Optional[str]
    introduced_jobs: Optional[str]
    job_appeal_points: Optional[str]
    job_concerns: Optional[str]
    companies_in_selection: Optional[List[str]]
    other_offer_salary: Optional[str]
    other_company_intention: Optional[List[str]]
    
    # 転職理由・希望条件
    transfer_reasons: Optional[List[str]]
    transfer_trigger: Optional[List[str]]
    desired_timing: Optional[str]
    timing_details: Optional[str]
    current_job_status: Optional[str]
    transfer_status_memo: Optional[List[str]]
    transfer_priorities: Optional[List[str]]
    
    # 職歴・経験
    career_history: Optional[List[str]]
    current_duties: Optional[str]
    company_good_points: Optional[str]
    company_bad_points: Optional[str]
    enjoyed_work: Optional[str]
    difficult_work: Optional[str]
    
    # 希望業界・職種
    experience_industry: Optional[str]
    experience_field_hr: Optional[str]
    desired_industry: Optional[List[str]]
    industry_reason: Optional[List[str]]
    desired_position: Optional[List[str]]
    position_industry_reason: Optional[List[str]]
    
    # 年収・待遇条件
    current_salary: Optional[int]
    salary_breakdown: Optional[str]
    desired_first_year_salary: Optional[float]
    base_incentive_ratio: Optional[str]
    max_future_salary: Optional[str]
    salary_memo: Optional[List[str]]
    remote_time_memo: Optional[List[str]]
    ca_ra_focus: Optional[str]
    customer_acquisition: Optional[str]
    new_existing_ratio: Optional[str]
    
    # 企業文化・キャリアビジョン
    business_vision: Optional[List[str]]
    desired_employee_count: Optional[List[str]]
    culture_scale_memo: Optional[List[str]]
    career_vision: Optional[List[str]]
    
    # メタデータ
    extraction_metadata: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str
    
    @classmethod
    def from_entity(cls, entity) -> 'StructuredDataDTO':
        """エンティティからDTOを作成"""
        entity_dict = entity.to_dict()
        
        return cls(
            id=entity_dict['id'],
            meeting_document_id=entity_dict['meeting_document_id'],
            extraction_status=entity_dict['extraction_status'],
            
            # 転職活動状況・エージェント関連
            transfer_activity_status=entity_dict['transfer_activity_status'],
            agent_count=entity_dict['agent_count'],
            current_agents=entity_dict['current_agents'],
            introduced_jobs=entity_dict['introduced_jobs'],
            job_appeal_points=entity_dict['job_appeal_points'],
            job_concerns=entity_dict['job_concerns'],
            companies_in_selection=entity_dict['companies_in_selection'],
            other_offer_salary=entity_dict['other_offer_salary'],
            other_company_intention=entity_dict['other_company_intention'],
            
            # 転職理由・希望条件
            transfer_reasons=entity_dict['transfer_reasons'],
            transfer_trigger=entity_dict['transfer_trigger'],
            desired_timing=entity_dict['desired_timing'],
            timing_details=entity_dict['timing_details'],
            current_job_status=entity_dict['current_job_status'],
            transfer_status_memo=entity_dict['transfer_status_memo'],
            transfer_priorities=entity_dict['transfer_priorities'],
            
            # 職歴・経験
            career_history=entity_dict['career_history'],
            current_duties=entity_dict['current_duties'],
            company_good_points=entity_dict['company_good_points'],
            company_bad_points=entity_dict['company_bad_points'],
            enjoyed_work=entity_dict['enjoyed_work'],
            difficult_work=entity_dict['difficult_work'],
            
            # 希望業界・職種
            experience_industry=entity_dict['experience_industry'],
            experience_field_hr=entity_dict['experience_field_hr'],
            desired_industry=entity_dict['desired_industry'],
            industry_reason=entity_dict['industry_reason'],
            desired_position=entity_dict['desired_position'],
            position_industry_reason=entity_dict['position_industry_reason'],
            
            # 年収・待遇条件
            current_salary=entity_dict['current_salary'],
            salary_breakdown=entity_dict['salary_breakdown'],
            desired_first_year_salary=entity_dict['desired_first_year_salary'],
            base_incentive_ratio=entity_dict['base_incentive_ratio'],
            max_future_salary=entity_dict['max_future_salary'],
            salary_memo=entity_dict['salary_memo'],
            remote_time_memo=entity_dict['remote_time_memo'],
            ca_ra_focus=entity_dict['ca_ra_focus'],
            customer_acquisition=entity_dict['customer_acquisition'],
            new_existing_ratio=entity_dict['new_existing_ratio'],
            
            # 企業文化・キャリアビジョン
            business_vision=entity_dict['business_vision'],
            desired_employee_count=entity_dict['desired_employee_count'],
            culture_scale_memo=entity_dict['culture_scale_memo'],
            career_vision=entity_dict['career_vision'],
            
            # メタデータ
            extraction_metadata=entity_dict['extraction_metadata'],
            created_at=entity_dict['created_at'],
            updated_at=entity_dict['updated_at']
        )


@dataclass
class StructuredDataSummaryDTO:
    """構造化データの要約DTO"""
    
    id: str
    meeting_document_id: str
    extraction_status: str
    
    # 主要情報のみ
    transfer_activity_status: Optional[str]
    desired_timing: Optional[str]
    current_salary: Optional[int]
    desired_first_year_salary: Optional[float]
    experience_industry: Optional[str]
    desired_position: Optional[List[str]]
    career_vision: Optional[List[str]]
    
    created_at: str
    updated_at: str
    
    @classmethod
    def from_entity(cls, entity) -> 'StructuredDataSummaryDTO':
        """エンティティから要約DTOを作成"""
        entity_dict = entity.to_dict()
        
        return cls(
            id=entity_dict['id'],
            meeting_document_id=entity_dict['meeting_document_id'],
            extraction_status=entity_dict['extraction_status'],
            transfer_activity_status=entity_dict['transfer_activity_status'],
            desired_timing=entity_dict['desired_timing'],
            current_salary=entity_dict['current_salary'],
            desired_first_year_salary=entity_dict['desired_first_year_salary'],
            experience_industry=entity_dict['experience_industry'],
            desired_position=entity_dict['desired_position'],
            career_vision=entity_dict['career_vision'],
            created_at=entity_dict['created_at'],
            updated_at=entity_dict['updated_at']
        )


@dataclass
class AnalyzeStructuredDataRequestDTO:
    """構造化データ分析リクエストDTO"""
    
    meeting_document_id: str
    force_reanalysis: bool = False


@dataclass
class AnalyzeStructuredDataResponseDTO:
    """構造化データ分析レスポンスDTO"""
    
    success: bool
    message: str
    structured_data_id: Optional[str]
    extraction_status: str
    quality_score: Optional[float]
    errors: List[str]
    
    @classmethod
    def create_success(
        cls,
        structured_data_id: str,
        extraction_status: str,
        quality_score: Optional[float] = None
    ) -> 'AnalyzeStructuredDataResponseDTO':
        """成功レスポンスを作成"""
        return cls(
            success=True,
            message="Analysis completed successfully",
            structured_data_id=structured_data_id,
            extraction_status=extraction_status,
            quality_score=quality_score,
            errors=[]
        )
    
    @classmethod
    def create_error(cls, errors: List[str]) -> 'AnalyzeStructuredDataResponseDTO':
        """エラーレスポンスを作成"""
        return cls(
            success=False,
            message="Analysis failed",
            structured_data_id=None,
            extraction_status="failed",
            quality_score=None,
            errors=errors
        )
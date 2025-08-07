from sqlalchemy import Column, String, Text, DateTime, JSON, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from ..connection import Base


class StructuredDataModel(Base):
    """構造化データのORMモデル"""
    
    __tablename__ = "structured_data"
    
    # 基本フィールド
    id = Column(
        String, 
        primary_key=True, 
        default=lambda: str(uuid.uuid4()),
        comment="構造化データの一意ID"
    )
    
    meeting_document_id = Column(
        String, 
        ForeignKey("meeting_documents.id", ondelete="CASCADE"),
        nullable=False,
        comment="関連する議事録ドキュメントID"
    )
    
    # 転職活動状況・エージェント関連
    transfer_activity_status = Column(
        String(100),
        nullable=True,
        comment="転職活動状況"
    )
    
    agent_count = Column(
        String(50),
        nullable=True,
        comment="エージェント数"
    )
    
    current_agents = Column(
        Text,
        nullable=True,
        comment="現在利用中のエージェント"
    )
    
    introduced_jobs = Column(
        Text,
        nullable=True,
        comment="紹介された求人"
    )
    
    job_appeal_points = Column(
        Text,
        nullable=True,
        comment="求人の魅力点"
    )
    
    job_concerns = Column(
        Text,
        nullable=True,
        comment="求人の懸念点"
    )
    
    companies_in_selection = Column(
        JSON,
        nullable=True,
        default=[],
        comment="選考中の企業（配列）"
    )
    
    other_offer_salary = Column(
        String(100),
        nullable=True,
        comment="他社オファー年収"
    )
    
    other_company_intention = Column(
        JSON,
        nullable=True,
        default=[],
        comment="他社意向度（配列）"
    )
    
    # 転職理由・希望条件
    transfer_reasons = Column(
        JSON,
        nullable=True,
        default=[],
        comment="転職理由（配列）"
    )
    
    transfer_trigger = Column(
        JSON,
        nullable=True,
        default=[],
        comment="転職きっかけ（配列）"
    )
    
    desired_timing = Column(
        String(50),
        nullable=True,
        comment="希望転職時期"
    )
    
    timing_details = Column(
        Text,
        nullable=True,
        comment="転職時期詳細"
    )
    
    current_job_status = Column(
        String(50),
        nullable=True,
        comment="現職状況"
    )
    
    transfer_status_memo = Column(
        JSON,
        nullable=True,
        default=[],
        comment="転職状況メモ（配列）"
    )
    
    transfer_priorities = Column(
        JSON,
        nullable=True,
        default=[],
        comment="転職軸（配列）"
    )
    
    # 職歴・経験
    career_history = Column(
        JSON,
        nullable=True,
        default=[],
        comment="職歴（配列）"
    )
    
    current_duties = Column(
        Text,
        nullable=True,
        comment="現在の担当業務"
    )
    
    company_good_points = Column(
        Text,
        nullable=True,
        comment="現職企業の良い点"
    )
    
    company_bad_points = Column(
        Text,
        nullable=True,
        comment="現職企業の悪い点"
    )
    
    enjoyed_work = Column(
        Text,
        nullable=True,
        comment="楽しかった仕事"
    )
    
    difficult_work = Column(
        Text,
        nullable=True,
        comment="辛かった仕事"
    )
    
    # 希望業界・職種
    experience_industry = Column(
        String(100),
        nullable=True,
        comment="経験業界"
    )
    
    experience_field_hr = Column(
        String(100),
        nullable=True,
        comment="人材領域での経験"
    )
    
    desired_industry = Column(
        JSON,
        nullable=True,
        default=[],
        comment="希望業界（配列）"
    )
    
    industry_reason = Column(
        JSON,
        nullable=True,
        default=[],
        comment="業界希望理由（配列）"
    )
    
    desired_position = Column(
        JSON,
        nullable=True,
        default=[],
        comment="希望職種（配列）"
    )
    
    position_industry_reason = Column(
        JSON,
        nullable=True,
        default=[],
        comment="職種・業界希望理由（配列）"
    )
    
    # 年収・待遇条件
    current_salary = Column(
        Integer,
        nullable=True,
        comment="現在の年収"
    )
    
    salary_breakdown = Column(
        Text,
        nullable=True,
        comment="年収内訳"
    )
    
    desired_first_year_salary = Column(
        Float,
        nullable=True,
        comment="初年度希望年収"
    )
    
    base_incentive_ratio = Column(
        String(100),
        nullable=True,
        comment="基本給・インセンティブ比率"
    )
    
    max_future_salary = Column(
        String(100),
        nullable=True,
        comment="将来最大年収"
    )
    
    salary_memo = Column(
        JSON,
        nullable=True,
        default=[],
        comment="給与メモ（配列）"
    )
    
    remote_time_memo = Column(
        JSON,
        nullable=True,
        default=[],
        comment="リモート・時間メモ（配列）"
    )
    
    ca_ra_focus = Column(
        String(100),
        nullable=True,
        comment="CA起点/RA起点"
    )
    
    customer_acquisition = Column(
        String(200),
        nullable=True,
        comment="集客方法"
    )
    
    new_existing_ratio = Column(
        String(100),
        nullable=True,
        comment="新規・既存比率"
    )
    
    # 企業文化・キャリアビジョン
    business_vision = Column(
        JSON,
        nullable=True,
        default=[],
        comment="事業構想（配列）"
    )
    
    desired_employee_count = Column(
        JSON,
        nullable=True,
        default=[],
        comment="希望従業員数（配列）"
    )
    
    culture_scale_memo = Column(
        JSON,
        nullable=True,
        default=[],
        comment="企業文化・規模メモ（配列）"
    )
    
    career_vision = Column(
        JSON,
        nullable=True,
        default=[],
        comment="キャリアビジョン（配列）"
    )
    
    # 抽出メタデータ
    extraction_metadata = Column(
        JSON,
        nullable=True,
        comment="抽出処理のメタデータ"
    )
    
    extraction_status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="抽出ステータス（pending/completed/failed）"
    )
    
    # タイムスタンプ
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        comment="レコード作成日時"
    )
    
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
        comment="レコード更新日時"
    )
    
    # リレーションシップ
    meeting_document = relationship(
        "MeetingDocumentModel",
        backref="structured_data"
    )
    
    # インデックス
    __table_args__ = (
        # 議事録ドキュメントID検索用インデックス
        Index('idx_structured_meeting_doc_id', 'meeting_document_id'),
        # 抽出ステータス検索用インデックス
        Index('idx_structured_extraction_status', 'extraction_status'),
        # 作成日時検索用インデックス
        Index('idx_structured_created_at', 'created_at'),
        # 更新日時検索用インデックス
        Index('idx_structured_updated_at', 'updated_at'),
        # 転職活動状況検索用インデックス
        Index('idx_structured_activity_status', 'transfer_activity_status'),
        # 現在年収検索用インデックス（範囲検索用）
        Index('idx_structured_current_salary', 'current_salary'),
    )
    
    def __repr__(self):
        return (
            f"<StructuredDataModel("
            f"id={self.id}, "
            f"meeting_document_id={self.meeting_document_id}, "
            f"extraction_status={self.extraction_status}, "
            f"created_at={self.created_at}"
            f")>"
        )
    
    def to_dict(self) -> dict:
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
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
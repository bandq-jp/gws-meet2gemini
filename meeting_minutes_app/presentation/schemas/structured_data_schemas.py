from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

from .common_schemas import BaseResponse, PaginationResponse


# リクエストスキーマ
class AnalyzeStructuredDataRequest(BaseModel):
    """構造化データ分析リクエスト"""
    force_reanalysis: bool = Field(
        default=False, 
        description="既存の分析結果があっても強制的に再分析するかどうか"
    )


class StructuredDataListRequest(BaseModel):
    """構造化データ一覧取得リクエスト"""
    extraction_status: Optional[str] = Field(
        default=None, 
        description="抽出ステータスでフィルタ（pending/completed/failed）"
    )
    page: int = Field(default=1, ge=1, description="ページ番号（1から開始）")
    page_size: int = Field(default=20, ge=1, le=100, description="1ページあたりの件数")
    
    @validator('extraction_status')
    def validate_extraction_status(cls, v):
        if v is not None:
            allowed_statuses = ['pending', 'completed', 'failed']
            if v not in allowed_statuses:
                raise ValueError(f"Status must be one of: {allowed_statuses}")
        return v


class StructuredDataBatchAnalysisRequest(BaseModel):
    """構造化データ一括分析リクエスト"""
    meeting_document_ids: List[str] = Field(..., description="分析対象議事録ドキュメントID一覧")
    force_reanalysis: bool = Field(default=False, description="強制再分析フラグ")
    
    @validator('meeting_document_ids')
    def validate_meeting_document_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one meeting document ID is required")
        if len(v) > 50:
            raise ValueError("Too many meeting document IDs (max: 50)")
        return v


# レスポンススキーマ
class StructuredDataSchema(BaseModel):
    """構造化データのスキーマ"""
    id: str = Field(..., description="構造化データID")
    meeting_document_id: str = Field(..., description="関連議事録ドキュメントID")
    extraction_status: str = Field(..., description="抽出ステータス")
    
    # 転職活動状況・エージェント関連
    transfer_activity_status: Optional[str] = Field(default=None, description="転職活動状況")
    agent_count: Optional[str] = Field(default=None, description="エージェント数")
    current_agents: Optional[str] = Field(default=None, description="現在利用中のエージェント")
    introduced_jobs: Optional[str] = Field(default=None, description="紹介された求人")
    job_appeal_points: Optional[str] = Field(default=None, description="求人の魅力点")
    job_concerns: Optional[str] = Field(default=None, description="求人の懸念点")
    companies_in_selection: Optional[List[str]] = Field(default=None, description="選考中の企業")
    other_offer_salary: Optional[str] = Field(default=None, description="他社オファー年収")
    other_company_intention: Optional[List[str]] = Field(default=None, description="他社意向度")
    
    # 転職理由・希望条件
    transfer_reasons: Optional[List[str]] = Field(default=None, description="転職理由")
    transfer_trigger: Optional[List[str]] = Field(default=None, description="転職きっかけ")
    desired_timing: Optional[str] = Field(default=None, description="希望転職時期")
    timing_details: Optional[str] = Field(default=None, description="転職時期詳細")
    current_job_status: Optional[str] = Field(default=None, description="現職状況")
    transfer_status_memo: Optional[List[str]] = Field(default=None, description="転職状況メモ")
    transfer_priorities: Optional[List[str]] = Field(default=None, description="転職軸")
    
    # 職歴・経験
    career_history: Optional[List[str]] = Field(default=None, description="職歴")
    current_duties: Optional[str] = Field(default=None, description="現在の担当業務")
    company_good_points: Optional[str] = Field(default=None, description="現職企業の良い点")
    company_bad_points: Optional[str] = Field(default=None, description="現職企業の悪い点")
    enjoyed_work: Optional[str] = Field(default=None, description="楽しかった仕事")
    difficult_work: Optional[str] = Field(default=None, description="辛かった仕事")
    
    # 希望業界・職種
    experience_industry: Optional[str] = Field(default=None, description="経験業界")
    experience_field_hr: Optional[str] = Field(default=None, description="人材領域での経験")
    desired_industry: Optional[List[str]] = Field(default=None, description="希望業界")
    industry_reason: Optional[List[str]] = Field(default=None, description="業界希望理由")
    desired_position: Optional[List[str]] = Field(default=None, description="希望職種")
    position_industry_reason: Optional[List[str]] = Field(default=None, description="職種・業界希望理由")
    
    # 年収・待遇条件
    current_salary: Optional[int] = Field(default=None, description="現在の年収")
    salary_breakdown: Optional[str] = Field(default=None, description="年収内訳")
    desired_first_year_salary: Optional[float] = Field(default=None, description="初年度希望年収")
    base_incentive_ratio: Optional[str] = Field(default=None, description="基本給・インセンティブ比率")
    max_future_salary: Optional[str] = Field(default=None, description="将来最大年収")
    salary_memo: Optional[List[str]] = Field(default=None, description="給与メモ")
    remote_time_memo: Optional[List[str]] = Field(default=None, description="リモート・時間メモ")
    ca_ra_focus: Optional[str] = Field(default=None, description="CA起点/RA起点")
    customer_acquisition: Optional[str] = Field(default=None, description="集客方法")
    new_existing_ratio: Optional[str] = Field(default=None, description="新規・既存比率")
    
    # 企業文化・キャリアビジョン
    business_vision: Optional[List[str]] = Field(default=None, description="事業構想")
    desired_employee_count: Optional[List[str]] = Field(default=None, description="希望従業員数")
    culture_scale_memo: Optional[List[str]] = Field(default=None, description="企業文化・規模メモ")
    career_vision: Optional[List[str]] = Field(default=None, description="キャリアビジョン")
    
    # メタデータ
    extraction_metadata: Optional[Dict[str, Any]] = Field(default=None, description="抽出メタデータ")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")


class StructuredDataSummarySchema(BaseModel):
    """構造化データの要約スキーマ"""
    id: str = Field(..., description="構造化データID")
    meeting_document_id: str = Field(..., description="関連議事録ドキュメントID")
    extraction_status: str = Field(..., description="抽出ステータス")
    
    # 主要情報のみ
    transfer_activity_status: Optional[str] = Field(default=None, description="転職活動状況")
    desired_timing: Optional[str] = Field(default=None, description="希望転職時期")
    current_salary: Optional[int] = Field(default=None, description="現在の年収")
    desired_first_year_salary: Optional[float] = Field(default=None, description="初年度希望年収")
    experience_industry: Optional[str] = Field(default=None, description="経験業界")
    desired_position: Optional[List[str]] = Field(default=None, description="希望職種")
    career_vision: Optional[List[str]] = Field(default=None, description="キャリアビジョン")
    
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")


class AnalyzeStructuredDataResponse(BaseResponse):
    """構造化データ分析レスポンス"""
    structured_data_id: Optional[str] = Field(default=None, description="構造化データID")
    extraction_status: str = Field(..., description="抽出ステータス")
    quality_score: Optional[float] = Field(default=None, description="抽出品質スコア（0.0-1.0）")
    errors: List[str] = Field(default_factory=list, description="エラー一覧")


class StructuredDataDetailResponse(BaseModel):
    """構造化データ詳細レスポンス"""
    structured_data: StructuredDataSchema = Field(..., description="構造化データ詳細")


class StructuredDataListResponse(BaseModel):
    """構造化データ一覧レスポンス"""
    structured_data: List[StructuredDataSummarySchema] = Field(..., description="構造化データ一覧")
    pagination: PaginationResponse = Field(..., description="ページネーション情報")


class StructuredDataStatisticsResponse(BaseModel):
    """構造化データ統計レスポンス"""
    total_count: int = Field(..., description="総構造化データ数")
    pending_count: int = Field(..., description="抽出待ち数")
    completed_count: int = Field(..., description="抽出完了数")
    failed_count: int = Field(..., description="抽出失敗数")
    success_rate: float = Field(..., description="成功率（%）")


class BatchAnalysisResponse(BaseResponse):
    """一括分析レスポンス"""
    total_count: int = Field(..., description="対象総数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失敗数")
    results: List[Dict[str, Any]] = Field(..., description="各分析の結果詳細")


class RetryExtractionResponse(BaseResponse):
    """抽出リトライレスポンス"""
    structured_data_id: str = Field(..., description="構造化データID")
    extraction_status: str = Field(..., description="抽出ステータス")
    quality_score: Optional[float] = Field(default=None, description="抽出品質スコア")


class ExtractionQualityReportRequest(BaseModel):
    """抽出品質レポートリクエスト"""
    date_from: Optional[datetime] = Field(default=None, description="レポート開始日時")
    date_to: Optional[datetime] = Field(default=None, description="レポート終了日時")
    include_details: bool = Field(default=False, description="詳細情報を含めるかどうか")


class ExtractionQualityReportResponse(BaseModel):
    """抽出品質レポートレスポンス"""
    report_period: Dict[str, str] = Field(..., description="レポート期間")
    overall_statistics: Dict[str, Any] = Field(..., description="全体統計")
    quality_distribution: Dict[str, int] = Field(..., description="品質スコア分布")
    field_completion_rates: Dict[str, float] = Field(..., description="フィールド完成度")
    recommendations: List[str] = Field(..., description="改善提案")
    details: Optional[List[Dict[str, Any]]] = Field(default=None, description="詳細データ")


class StructuredDataExportRequest(BaseModel):
    """構造化データエクスポートリクエスト"""
    extraction_status: Optional[str] = Field(default=None, description="ステータスフィルタ")
    format: str = Field(default="json", description="エクスポート形式（json/csv/excel）")
    include_metadata: bool = Field(default=True, description="メタデータを含めるかどうか")
    date_from: Optional[datetime] = Field(default=None, description="抽出開始日時")
    date_to: Optional[datetime] = Field(default=None, description="抽出終了日時")
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['json', 'csv', 'excel']
        if v not in allowed_formats:
            raise ValueError(f"Format must be one of: {allowed_formats}")
        return v


class StructuredDataExportResponse(BaseResponse):
    """構造化データエクスポートレスポンス"""
    export_url: str = Field(..., description="エクスポートファイルURL")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    record_count: int = Field(..., description="エクスポートされたレコード数")
    expires_at: datetime = Field(..., description="ダウンロード期限")
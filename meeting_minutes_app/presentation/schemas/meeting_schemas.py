from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

from .common_schemas import BaseResponse, PaginationResponse


# リクエストスキーマ
class CollectMeetingsRequest(BaseModel):
    """議事録収集リクエスト"""
    account_emails: Optional[List[str]] = Field(
        default=None, 
        description="対象アカウントメール一覧（指定なしで全アカウント）"
    )
    force_update: bool = Field(
        default=False, 
        description="既存ファイルを強制更新するかどうか"
    )
    include_doc_structure: bool = Field(
        default=False, 
        description="Google Docs API構造を含めるかどうか"
    )
    
    @validator('account_emails')
    def validate_account_emails(cls, v):
        if v is not None and len(v) == 0:
            return None  # 空リストはNoneとして扱う
        return v


class MeetingListRequest(BaseModel):
    """議事録一覧取得リクエスト"""
    account_email: Optional[str] = Field(default=None, description="フィルタするアカウントメール")
    page: int = Field(default=1, ge=1, description="ページ番号（1から開始）")
    page_size: int = Field(default=20, ge=1, le=100, description="1ページあたりの件数")


class RecentMeetingsRequest(BaseModel):
    """最近の議事録取得リクエスト"""
    account_email: Optional[str] = Field(default=None, description="フィルタするアカウントメール")
    days: int = Field(default=30, ge=1, le=365, description="何日前まで取得するか")
    limit: int = Field(default=50, ge=1, le=200, description="最大取得件数")


# レスポンススキーマ
class MeetingDocumentSchema(BaseModel):
    """議事録ドキュメントのスキーマ"""
    id: str = Field(..., description="議事録ドキュメントID")
    document_id: str = Field(..., description="GoogleドキュメントID")
    account_email: str = Field(..., description="アカウントメールアドレス")
    title: str = Field(..., description="議事録タイトル")
    date_time: Optional[str] = Field(default=None, description="会議日時（ISO形式）")
    web_view_link: str = Field(..., description="GoogleドキュメントのURL")
    text_content: str = Field(..., description="議事録テキスト（プレビュー）")
    owner_email: str = Field(..., description="ドキュメント所有者メール")
    invited_accounts: List[str] = Field(..., description="招待されたアカウント一覧")
    downloaded_at: str = Field(..., description="取得日時（ISO形式）")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")


class MeetingDocumentDetailSchema(BaseModel):
    """議事録ドキュメント詳細のスキーマ"""
    id: str = Field(..., description="議事録ドキュメントID")
    document_id: str = Field(..., description="GoogleドキュメントID")
    account_email: str = Field(..., description="アカウントメールアドレス")
    metadata: Dict[str, Any] = Field(..., description="会議メタデータ")
    text_content: str = Field(..., description="議事録テキスト（全文）")
    doc_structure: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Google Docs API構造"
    )
    downloaded_at: str = Field(..., description="取得日時（ISO形式）")
    created_at: str = Field(..., description="作成日時（ISO形式）")
    updated_at: str = Field(..., description="更新日時（ISO形式）")


class MeetingListResponse(BaseModel):
    """議事録一覧レスポンス"""
    meetings: List[MeetingDocumentSchema] = Field(..., description="議事録一覧")
    pagination: PaginationResponse = Field(..., description="ページネーション情報")


class MeetingDetailResponse(BaseModel):
    """議事録詳細レスポンス"""
    meeting: MeetingDocumentDetailSchema = Field(..., description="議事録詳細")


class CollectMeetingsResponse(BaseResponse):
    """議事録収集レスポンス"""
    collected_count: int = Field(..., description="収集された議事録数")
    updated_count: int = Field(..., description="更新された議事録数")
    skipped_count: int = Field(..., description="スキップされた議事録数")
    account_results: Dict[str, Dict[str, Any]] = Field(
        ..., 
        description="アカウント別の結果詳細"
    )
    errors: List[str] = Field(default_factory=list, description="エラー一覧")


class MeetingStatisticsResponse(BaseModel):
    """議事録統計レスポンス"""
    total_count: int = Field(..., description="総議事録数")
    recent_count: int = Field(..., description="最近30日の議事録数")
    accounts: List[Dict[str, Any]] = Field(..., description="アカウント別統計")


class DeleteMeetingResponse(BaseResponse):
    """議事録削除レスポンス"""
    meeting_id: str = Field(..., description="削除された議事録ID")


class MeetingSearchRequest(BaseModel):
    """議事録検索リクエスト（将来拡張用）"""
    query: str = Field(..., description="検索クエリ")
    account_email: Optional[str] = Field(default=None, description="フィルタするアカウントメール")
    page: int = Field(default=1, ge=1, description="ページ番号")
    page_size: int = Field(default=20, ge=1, le=100, description="1ページあたりの件数")
    date_from: Optional[datetime] = Field(default=None, description="検索開始日時")
    date_to: Optional[datetime] = Field(default=None, description="検索終了日時")


class MeetingBatchOperationRequest(BaseModel):
    """議事録一括操作リクエスト"""
    meeting_ids: List[str] = Field(..., description="対象議事録ID一覧")
    operation: str = Field(..., description="操作種別（delete/analyze/export）")
    force: bool = Field(default=False, description="強制実行フラグ")
    
    @validator('meeting_ids')
    def validate_meeting_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one meeting ID is required")
        if len(v) > 100:
            raise ValueError("Too many meeting IDs (max: 100)")
        return v


class MeetingBatchOperationResponse(BaseResponse):
    """議事録一括操作レスポンス"""
    total_count: int = Field(..., description="対象総数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失敗数")
    results: List[Dict[str, Any]] = Field(..., description="各操作の結果詳細")


class MeetingExportRequest(BaseModel):
    """議事録エクスポートリクエスト"""
    meeting_ids: Optional[List[str]] = Field(default=None, description="エクスポート対象議事録ID")
    account_email: Optional[str] = Field(default=None, description="フィルタするアカウントメール")
    format: str = Field(default="json", description="エクスポート形式（json/csv/excel）")
    include_structured_data: bool = Field(
        default=False, 
        description="構造化データを含めるかどうか"
    )
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['json', 'csv', 'excel']
        if v not in allowed_formats:
            raise ValueError(f"Format must be one of: {allowed_formats}")
        return v


class MeetingExportResponse(BaseResponse):
    """議事録エクスポートレスポンス"""
    export_url: str = Field(..., description="エクスポートファイルURL")
    file_size: int = Field(..., description="ファイルサイズ（バイト）")
    record_count: int = Field(..., description="エクスポートされたレコード数")
    expires_at: datetime = Field(..., description="ダウンロード期限")
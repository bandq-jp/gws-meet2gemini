from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class BaseResponse(BaseModel):
    """レスポンスの基底クラス"""
    success: bool = Field(..., description="処理成功フラグ")
    message: str = Field(..., description="メッセージ")


class ErrorResponse(BaseResponse):
    """エラーレスポンス"""
    success: bool = Field(default=False, description="処理成功フラグ")
    errors: List[str] = Field(default_factory=list, description="エラー詳細リスト")


class PaginationRequest(BaseModel):
    """ページネーションリクエスト"""
    page: int = Field(default=1, ge=1, description="ページ番号（1から開始）")
    page_size: int = Field(default=20, ge=1, le=100, description="1ページあたりの件数")


class PaginationResponse(BaseModel):
    """ページネーションレスポンス"""
    total_count: int = Field(..., description="総件数")
    page: int = Field(..., description="現在のページ番号")
    page_size: int = Field(..., description="1ページあたりの件数")
    has_next: bool = Field(..., description="次ページがあるかどうか")


class HealthCheckResponse(BaseModel):
    """ヘルスチェックレスポンス"""
    status: str = Field(..., description="サービス状態")
    timestamp: datetime = Field(..., description="チェック時刻")
    version: str = Field(..., description="アプリケーションバージョン")
    database: bool = Field(..., description="データベース接続状態")
    google_auth: bool = Field(..., description="Google認証状態")
    details: Optional[Dict[str, Any]] = Field(default=None, description="詳細情報")


class StatisticsResponse(BaseModel):
    """統計情報レスポンス"""
    total_count: int = Field(..., description="総件数")
    recent_count: int = Field(..., description="最近の件数")
    success_rate: Optional[float] = Field(default=None, description="成功率（%）")
    accounts: List[Dict[str, Any]] = Field(default_factory=list, description="アカウント別統計")
    last_updated: Optional[datetime] = Field(default=None, description="最終更新日時")


class AccountValidationRequest(BaseModel):
    """アカウント検証リクエスト"""
    account_email: str = Field(..., description="検証するアカウントメール")


class AccountValidationResponse(BaseModel):
    """アカウント検証レスポンス"""
    account_email: str = Field(..., description="アカウントメール")
    accessible: bool = Field(..., description="アクセス可能かどうか")
    error: Optional[str] = Field(default=None, description="エラーメッセージ")


class BulkOperationRequest(BaseModel):
    """一括操作リクエスト"""
    ids: List[str] = Field(..., description="対象ID一覧")
    operation: str = Field(..., description="操作種別")
    params: Optional[Dict[str, Any]] = Field(default=None, description="追加パラメータ")


class BulkOperationResponse(BaseResponse):
    """一括操作レスポンス"""
    total_count: int = Field(..., description="対象総数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失敗数")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="各操作の結果詳細")


class BackgroundTaskResponse(BaseResponse):
    """バックグラウンドタスクレスポンス"""
    task_id: Optional[str] = Field(default=None, description="タスクID")
    status: str = Field(..., description="タスク状態")
    estimated_time: Optional[int] = Field(default=None, description="推定完了時間（秒）")


class ConfigurationResponse(BaseModel):
    """設定情報レスポンス"""
    available_accounts: List[str] = Field(..., description="利用可能アカウント一覧")
    target_folder_keyword: str = Field(..., description="対象フォルダキーワード")
    max_workers: int = Field(..., description="最大並列数")
    gemini_model: str = Field(..., description="使用中のGeminiモデル")
    environment: str = Field(..., description="実行環境")
    features: Dict[str, bool] = Field(..., description="機能有効フラグ")


class ValidationError(BaseModel):
    """バリデーションエラー詳細"""
    field: str = Field(..., description="エラーフィールド")
    message: str = Field(..., description="エラーメッセージ")
    value: Optional[str] = Field(default=None, description="入力値")


class DetailedErrorResponse(ErrorResponse):
    """詳細エラーレスポンス"""
    error_code: Optional[str] = Field(default=None, description="エラーコード")
    validation_errors: List[ValidationError] = Field(default_factory=list, description="バリデーションエラー詳細")
    timestamp: datetime = Field(default_factory=datetime.now, description="エラー発生時刻")
    request_id: Optional[str] = Field(default=None, description="リクエストID")
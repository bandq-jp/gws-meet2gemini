from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """アプリケーション設定"""
    
    # アプリケーション基本設定
    app_name: str = "Meeting Minutes Management System"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Debug mode")
    
    # サーバー設定
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    
    # 環境設定
    environment: str = Field(default="development", description="Environment (development/production)")
    
    # Google Cloud 設定
    google_cloud_project_id: Optional[str] = Field(default=None, description="Google Cloud Project ID")
    service_account_file: Optional[str] = Field(default=None, description="Service account JSON file path")
    
    # Google APIs 設定
    google_drive_scopes: List[str] = Field(
        default=[
            "https://www.googleapis.com/auth/drive.readonly",
            "https://www.googleapis.com/auth/documents.readonly"
        ],
        description="Google Drive API scopes"
    )
    
    # 対象アカウント設定
    available_accounts: List[str] = Field(
        default=[
            "masuda.g@bandq.jp",
            "narita.k@bandq.jp", 
            "ito.t@bandq.jp"
        ],
        description="Available Google accounts for document access"
    )
    
    # Gemini API 設定
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    gemini_model: str = Field(default="gemini-2.5-pro", description="Gemini model name")
    gemini_temperature: float = Field(default=0.1, description="Gemini temperature")
    gemini_max_output_tokens: int = Field(default=8192, description="Gemini max output tokens")
    
    # データベース設定
    database_url: Optional[str] = Field(default=None, description="Database connection URL")
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Database max overflow connections")
    
    # 議事録取得設定
    target_folder_keyword: str = Field(default="Meet Recordings", description="Target folder keyword")
    case_sensitive_search: bool = Field(default=False, description="Case sensitive folder search")
    export_mime_type: str = Field(default="text/plain", description="Export MIME type")
    max_text_preview: int = Field(default=600, description="Max text preview length")
    
    # 並列処理設定
    max_workers: int = Field(default=3, description="Max parallel workers")
    max_retries: int = Field(default=3, description="Max retries for API calls")
    retry_delay_seconds: float = Field(default=1.0, description="Retry delay in seconds")
    
    # ログ設定
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # CORS設定
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )
    cors_credentials: bool = Field(default=True, description="CORS allow credentials")
    cors_methods: List[str] = Field(default=["*"], description="CORS allowed methods")
    cors_headers: List[str] = Field(default=["*"], description="CORS allowed headers")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
    
    @property
    def is_production(self) -> bool:
        """本番環境かどうか"""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """開発環境かどうか"""
        return self.environment.lower() == "development"
    
    def get_gemini_api_key(self) -> str:
        """Gemini API キーを取得（環境変数からも取得）"""
        if self.gemini_api_key:
            return self.gemini_api_key
        
        # 環境変数から取得を試行
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")
        
        return api_key
    
    def get_service_account_file(self) -> str:
        """サービスアカウントファイルのパスを取得"""
        if self.service_account_file:
            return self.service_account_file
        
        # デフォルトパスを試行
        default_path = "service_account.json"
        if os.path.exists(default_path):
            return default_path
        
        # 環境変数から取得を試行
        env_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
        if env_path and os.path.exists(env_path):
            return env_path
        
        if self.is_production:
            # 本番環境ではサービスアカウントファイルは不要（メタデータサーバーから取得）
            return ""
        
        raise ValueError("Service account file is required for local development.")


# グローバル設定インスタンス
settings = Settings()
from typing import Optional, List
from google.auth.credentials import Credentials
from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

from .service_account_manager import ServiceAccountManager
from ..config.settings import settings


class GoogleAuthService:
    """Google認証サービス"""
    
    def __init__(self):
        self._service_account_manager = ServiceAccountManager()
        self._service_cache = {}
    
    def get_drive_service(self, account_email: Optional[str] = None) -> Resource:
        """
        Google Drive APIサービスを取得
        
        Args:
            account_email: 対象アカウントのメールアドレス
            
        Returns:
            Google Drive APIサービス
        """
        cache_key = f"drive_{account_email or 'default'}"
        
        if cache_key in self._service_cache:
            return self._service_cache[cache_key]
        
        credentials = self._get_credentials_for_account(account_email)
        service = build("drive", "v3", credentials=credentials, cache_discovery=False)
        
        self._service_cache[cache_key] = service
        return service
    
    def get_docs_service(self, account_email: Optional[str] = None) -> Resource:
        """
        Google Docs APIサービスを取得
        
        Args:
            account_email: 対象アカウントのメールアドレス
            
        Returns:
            Google Docs APIサービス
        """
        cache_key = f"docs_{account_email or 'default'}"
        
        if cache_key in self._service_cache:
            return self._service_cache[cache_key]
        
        credentials = self._get_credentials_for_account(account_email)
        service = build("docs", "v1", credentials=credentials, cache_discovery=False)
        
        self._service_cache[cache_key] = service
        return service
    
    def _get_credentials_for_account(self, account_email: Optional[str]) -> Credentials:
        """アカウント用の認証情報を取得"""
        if account_email:
            return self._service_account_manager.get_credentials_for_account(account_email)
        else:
            return self._service_account_manager.get_credentials()
    
    def validate_account_access(self, account_email: str) -> bool:
        """
        アカウントへのアクセス権限を検証
        
        Args:
            account_email: 検証対象のアカウント
            
        Returns:
            アクセス可能性の真偽値
        """
        try:
            drive_service = self.get_drive_service(account_email)
            # 簡単なAPI呼び出しでアクセス権限を確認
            drive_service.about().get(fields="user").execute()
            return True
        except HttpError as e:
            if e.resp.status == 403:
                # 権限不足
                return False
            raise
    
    def get_available_accounts(self) -> List[str]:
        """
        利用可能なアカウント一覧を取得
        
        Returns:
            利用可能なアカウントのリスト
        """
        available = []
        for account in settings.available_accounts:
            try:
                if self.validate_account_access(account):
                    available.append(account)
            except Exception:
                # アクセスできないアカウントはスキップ
                continue
        
        return available
    
    def test_authentication(self) -> dict:
        """
        認証のテストを実行
        
        Returns:
            テスト結果の辞書
        """
        result = {
            "service_account_available": self._service_account_manager.is_service_account_available(),
            "accounts": {}
        }
        
        for account in settings.available_accounts:
            try:
                is_accessible = self.validate_account_access(account)
                result["accounts"][account] = {
                    "accessible": is_accessible,
                    "error": None
                }
            except Exception as e:
                result["accounts"][account] = {
                    "accessible": False,
                    "error": str(e)
                }
        
        return result
    
    def clear_cache(self):
        """サービスキャッシュをクリア"""
        self._service_cache.clear()
        self._service_account_manager.clear_cache()
    
    def refresh_credentials(self):
        """認証情報を更新"""
        self.clear_cache()
        # 新しい認証情報でサービスを再作成
        for account in settings.available_accounts:
            try:
                self.get_drive_service(account)
                self.get_docs_service(account)
            except Exception:
                # エラーは無視（後でアクセス時にエラーになる）
                pass
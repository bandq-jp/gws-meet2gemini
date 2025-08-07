from typing import Optional
import os
from google.oauth2.service_account import Credentials
from google.auth import default
from google.auth.credentials import Credentials as BaseCredentials
from ..config.settings import settings


class ServiceAccountManager:
    """サービスアカウント管理クラス"""
    
    def __init__(self):
        self._credentials_cache = {}
    
    def get_credentials(self, subject: Optional[str] = None) -> BaseCredentials:
        """
        サービスアカウントの認証情報を取得
        
        Args:
            subject: 偽装するユーザーのメールアドレス（Domain-wide delegation用）
            
        Returns:
            Google Cloud認証情報
        """
        cache_key = subject or "default"
        
        if cache_key in self._credentials_cache:
            return self._credentials_cache[cache_key]
        
        if settings.is_production:
            # 本番環境：メタデータサーバーから認証情報を取得
            credentials = self._get_production_credentials(subject)
        else:
            # 開発環境：サービスアカウントJSONファイルから認証情報を取得
            credentials = self._get_development_credentials(subject)
        
        self._credentials_cache[cache_key] = credentials
        return credentials
    
    def _get_production_credentials(self, subject: Optional[str] = None) -> BaseCredentials:
        """本番環境用の認証情報を取得"""
        if subject:
            # Domain-wide delegationが必要な場合
            # 本番環境でもサービスアカウントキーが必要
            service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
            if service_account_file:
                return Credentials.from_service_account_file(
                    service_account_file,
                    scopes=settings.google_drive_scopes,
                    subject=subject
                )
            else:
                raise ValueError(
                    "Service account file is required for domain-wide delegation in production"
                )
        else:
            # Application Default Credentials (ADC)を使用
            credentials, _ = default(scopes=settings.google_drive_scopes)
            return credentials
    
    def _get_development_credentials(self, subject: Optional[str] = None) -> BaseCredentials:
        """開発環境用の認証情報を取得"""
        service_account_file = settings.get_service_account_file()
        
        return Credentials.from_service_account_file(
            service_account_file,
            scopes=settings.google_drive_scopes,
            subject=subject
        )
    
    def validate_credentials(self, credentials: BaseCredentials) -> bool:
        """
        認証情報の有効性を検証
        
        Args:
            credentials: 検証する認証情報
            
        Returns:
            有効性の真偽値
        """
        try:
            # 認証情報の更新を試行
            if hasattr(credentials, 'refresh'):
                import google.auth.transport.requests
                request = google.auth.transport.requests.Request()
                credentials.refresh(request)
            return True
        except Exception:
            return False
    
    def clear_cache(self):
        """認証情報キャッシュをクリア"""
        self._credentials_cache.clear()
    
    def get_credentials_for_account(self, account_email: str) -> BaseCredentials:
        """
        特定のアカウント用の認証情報を取得
        
        Args:
            account_email: 対象アカウントのメールアドレス
            
        Returns:
            認証情報
        """
        if account_email not in settings.available_accounts:
            raise ValueError(f"Account {account_email} is not in available accounts list")
        
        return self.get_credentials(subject=account_email)
    
    def is_service_account_available(self) -> bool:
        """
        サービスアカウントが利用可能かどうかをチェック
        
        Returns:
            利用可能性の真偽値
        """
        try:
            if settings.is_production:
                # 本番環境では ADC の確認
                credentials, _ = default()
                return credentials is not None
            else:
                # 開発環境ではサービスアカウントファイルの存在確認
                service_account_file = settings.get_service_account_file()
                return os.path.exists(service_account_file)
        except Exception:
            return False
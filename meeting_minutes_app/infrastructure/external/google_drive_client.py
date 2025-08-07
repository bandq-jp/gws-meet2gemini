from typing import List, Dict, Any, Optional
from googleapiclient.errors import HttpError
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..auth.google_auth import GoogleAuthService
from ..config.settings import settings


class GoogleDriveClient:
    """Google Drive APIクライアント"""
    
    def __init__(self, google_auth_service: GoogleAuthService):
        self._google_auth_service = google_auth_service
        self._executor = ThreadPoolExecutor(max_workers=settings.max_workers)
    
    async def list_folders(self, account_email: str) -> Dict[str, Dict]:
        """
        指定アカウントの全フォルダを取得
        
        Args:
            account_email: 対象アカウントのメールアドレス
            
        Returns:
            フォルダID をキーとした フォルダ情報の辞書
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor, 
            self._list_folders_sync, 
            account_email
        )
    
    def _list_folders_sync(self, account_email: str) -> Dict[str, Dict]:
        """フォルダ一覧を同期的に取得"""
        drive_service = self._google_auth_service.get_drive_service(account_email)
        
        folders = {}
        page_token = None
        
        while True:
            try:
                response = (
                    drive_service.files()
                    .list(
                        q="mimeType='application/vnd.google-apps.folder' and trashed=false",
                        fields="nextPageToken, files(id,name,parents)",
                        pageSize=1000,
                        corpora="allDrives",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        pageToken=page_token,
                    )
                    .execute()
                )
                
                for folder in response.get("files", []):
                    folders[folder["id"]] = {
                        "name": folder["name"], 
                        "parents": folder.get("parents", [])
                    }
                
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                    
            except HttpError as e:
                raise Exception(f"Failed to list folders for {account_email}: {e}")
        
        return folders
    
    async def find_folders_by_keyword(
        self, 
        account_email: str, 
        keyword: str,
        case_sensitive: bool = False
    ) -> List[str]:
        """
        キーワードでフォルダを検索
        
        Args:
            account_email: 対象アカウントのメールアドレス
            keyword: 検索キーワード
            case_sensitive: 大文字小文字の区別
            
        Returns:
            マッチしたフォルダIDのリスト
        """
        folders = await self.list_folders(account_email)
        
        match_func = (
            (lambda name: name == keyword)
            if case_sensitive
            else (lambda name: name.lower() == keyword.lower())
        )
        
        return [
            folder_id 
            for folder_id, meta in folders.items() 
            if match_func(meta["name"])
        ]
    
    async def build_folder_path(
        self, 
        folder_id: str, 
        folders_dict: Dict[str, Dict]
    ) -> List[str]:
        """
        フォルダパスを構築
        
        Args:
            folder_id: 対象フォルダID
            folders_dict: フォルダ情報の辞書
            
        Returns:
            フォルダパスの配列（ルートから順）
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._build_folder_path_sync,
            folder_id,
            folders_dict
        )
    
    def _build_folder_path_sync(
        self, 
        folder_id: str, 
        folders_dict: Dict[str, Dict]
    ) -> List[str]:
        """フォルダパスを同期的に構築"""
        parts = []
        current_id = folder_id
        
        while current_id:
            folder_info = folders_dict.get(current_id)
            if not folder_info:
                break
            
            parts.append(folder_info["name"])
            parents = folder_info.get("parents", [])
            current_id = parents[0] if parents else None
        
        return list(reversed(parts))
    
    async def list_files_in_folder(
        self, 
        account_email: str, 
        folder_id: str
    ) -> List[Dict[str, Any]]:
        """
        フォルダ内のファイル一覧を取得
        
        Args:
            account_email: 対象アカウントのメールアドレス
            folder_id: 対象フォルダID
            
        Returns:
            ファイル情報のリスト
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._list_files_in_folder_sync,
            account_email,
            folder_id
        )
    
    def _list_files_in_folder_sync(
        self, 
        account_email: str, 
        folder_id: str
    ) -> List[Dict[str, Any]]:
        """フォルダ内ファイル一覧を同期的に取得"""
        drive_service = self._google_auth_service.get_drive_service(account_email)
        
        files = []
        page_token = None
        
        while True:
            try:
                response = (
                    drive_service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        fields=(
                            "nextPageToken, "
                            "files(id,name,mimeType,createdTime,modifiedTime,owners,webViewLink)"
                        ),
                        pageSize=1000,
                        corpora="allDrives",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        pageToken=page_token,
                    )
                    .execute()
                )
                
                files.extend(response.get("files", []))
                
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
                    
            except HttpError as e:
                raise Exception(f"Failed to list files in folder {folder_id} for {account_email}: {e}")
        
        return files
    
    async def export_document_as_text(
        self, 
        account_email: str, 
        document_id: str,
        mime_type: str = "text/plain"
    ) -> str:
        """
        Googleドキュメントをテキストとしてエクスポート
        
        Args:
            account_email: 対象アカウントのメールアドレス
            document_id: ドキュメントID
            mime_type: エクスポート形式
            
        Returns:
            ドキュメントのテキストコンテンツ
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._export_document_as_text_sync,
            account_email,
            document_id,
            mime_type
        )
    
    def _export_document_as_text_sync(
        self, 
        account_email: str, 
        document_id: str,
        mime_type: str = "text/plain"
    ) -> str:
        """ドキュメントを同期的にエクスポート"""
        drive_service = self._google_auth_service.get_drive_service(account_email)
        
        try:
            data = drive_service.files().export(
                fileId=document_id, 
                mimeType=mime_type
            ).execute()
            
            return data.decode("utf-8")
            
        except HttpError as e:
            raise Exception(f"Failed to export document {document_id} for {account_email}: {e}")
    
    def __del__(self):
        """デストラクタ：ExecutorPoolを適切にシャットダウン"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
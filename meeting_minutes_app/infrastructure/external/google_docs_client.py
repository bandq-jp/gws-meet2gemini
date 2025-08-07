from typing import Dict, Any, Optional
from googleapiclient.errors import HttpError
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..auth.google_auth import GoogleAuthService
from ..config.settings import settings


class GoogleDocsClient:
    """Google Docs APIクライアント"""
    
    def __init__(self, google_auth_service: GoogleAuthService):
        self._google_auth_service = google_auth_service
        self._executor = ThreadPoolExecutor(max_workers=settings.max_workers)
    
    async def get_document_structure(
        self, 
        account_email: str, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Googleドキュメントの構造情報を取得
        
        Args:
            account_email: 対象アカウントのメールアドレス
            document_id: ドキュメントID
            
        Returns:
            ドキュメント構造情報、取得失敗時はNone
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_document_structure_sync,
            account_email,
            document_id
        )
    
    def _get_document_structure_sync(
        self, 
        account_email: str, 
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """ドキュメント構造を同期的に取得"""
        try:
            docs_service = self._google_auth_service.get_docs_service(account_email)
            
            document = docs_service.documents().get(documentId=document_id).execute()
            return document
            
        except HttpError as e:
            # Docs APIが無効な場合やアクセス権限がない場合はNoneを返す
            if e.resp.status in [403, 404]:
                return None
            raise Exception(f"Failed to get document structure {document_id} for {account_email}: {e}")
    
    async def extract_document_text(
        self, 
        document_structure: Dict[str, Any]
    ) -> str:
        """
        ドキュメント構造からテキストを抽出
        
        Args:
            document_structure: Docs APIから取得したドキュメント構造
            
        Returns:
            抽出されたテキスト
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._extract_document_text_sync,
            document_structure
        )
    
    def _extract_document_text_sync(self, document_structure: Dict[str, Any]) -> str:
        """ドキュメント構造からテキストを同期的に抽出"""
        text_parts = []
        
        try:
            body = document_structure.get('body', {})
            content = body.get('content', [])
            
            for element in content:
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    paragraph_text = self._extract_paragraph_text(paragraph)
                    if paragraph_text:
                        text_parts.append(paragraph_text)
                
                elif 'table' in element:
                    table = element['table']
                    table_text = self._extract_table_text(table)
                    if table_text:
                        text_parts.append(table_text)
        
        except Exception as e:
            # 構造解析に失敗した場合は空文字を返す
            return ""
        
        return '\n'.join(text_parts)
    
    def _extract_paragraph_text(self, paragraph: Dict[str, Any]) -> str:
        """段落からテキストを抽出"""
        text_parts = []
        
        elements = paragraph.get('elements', [])
        for element in elements:
            text_run = element.get('textRun', {})
            content = text_run.get('content', '')
            if content:
                text_parts.append(content)
        
        return ''.join(text_parts).strip()
    
    def _extract_table_text(self, table: Dict[str, Any]) -> str:
        """テーブルからテキストを抽出"""
        text_parts = []
        
        rows = table.get('tableRows', [])
        for row in rows:
            row_text = []
            cells = row.get('tableCells', [])
            
            for cell in cells:
                cell_text_parts = []
                content = cell.get('content', [])
                
                for element in content:
                    if 'paragraph' in element:
                        paragraph_text = self._extract_paragraph_text(element['paragraph'])
                        if paragraph_text:
                            cell_text_parts.append(paragraph_text)
                
                cell_text = ' '.join(cell_text_parts)
                row_text.append(cell_text)
            
            if any(row_text):  # 空でない行のみ追加
                text_parts.append(' | '.join(row_text))
        
        return '\n'.join(text_parts)
    
    async def get_document_metadata(
        self, 
        document_structure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        ドキュメント構造からメタデータを抽出
        
        Args:
            document_structure: Docs APIから取得したドキュメント構造
            
        Returns:
            抽出されたメタデータ
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            self._get_document_metadata_sync,
            document_structure
        )
    
    def _get_document_metadata_sync(self, document_structure: Dict[str, Any]) -> Dict[str, Any]:
        """ドキュメント構造からメタデータを同期的に抽出"""
        return {
            "document_id": document_structure.get("documentId"),
            "title": document_structure.get("title"),
            "revision_id": document_structure.get("revisionId"),
            "document_style": document_structure.get("documentStyle", {}),
            "headers": document_structure.get("headers", {}),
            "footers": document_structure.get("footers", {}),
            "footnotes": document_structure.get("footnotes", {}),
            "suggestions_view_mode": document_structure.get("suggestionsViewMode")
        }
    
    def __del__(self):
        """デストラクタ：ExecutorPoolを適切にシャットダウン"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentId:
    """GoogleドキュメントIDの値オブジェクト"""
    
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Document ID cannot be empty")
        
        if not self._is_valid_google_doc_id(self.value):
            raise ValueError(f"Invalid Google document ID format: {self.value}")
    
    def _is_valid_google_doc_id(self, doc_id: str) -> bool:
        """GoogleドキュメントIDの形式チェック"""
        # GoogleドキュメントIDは通常44文字の英数字・ハイフン・アンダースコア
        if len(doc_id) < 25 or len(doc_id) > 50:
            return False
        
        # 英数字、ハイフン、アンダースコアのみを許可
        allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
        return all(c in allowed_chars for c in doc_id)
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, DocumentId):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
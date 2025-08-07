from dataclasses import dataclass
import re
from typing import Any


@dataclass(frozen=True)
class AccountEmail:
    """アカウントメールアドレスの値オブジェクト"""
    
    value: str
    
    def __post_init__(self):
        if not self.value:
            raise ValueError("Email address cannot be empty")
        
        if not self._is_valid_email(self.value):
            raise ValueError(f"Invalid email format: {self.value}")
    
    def _is_valid_email(self, email: str) -> bool:
        """簡易的なメールアドレス形式チェック"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def safe_filename_part(self) -> str:
        """ファイル名に使える形式に変換（@を_at_、.を_に）"""
        return self.value.replace('@', '_at_').replace('.', '_')
    
    def __str__(self) -> str:
        return self.value
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, AccountEmail):
            return False
        return self.value == other.value
    
    def __hash__(self) -> int:
        return hash(self.value)
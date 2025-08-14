"""
カスタムスキーマリポジトリのインターフェース

DDD/オニオンアーキテクチャに従い、ドメイン層でリポジトリの
インターフェースを定義し、インフラ層で実装する。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.entities.custom_schema import CustomSchema


class CustomSchemaRepository(ABC):
    """カスタムスキーマリポジトリのインターフェース"""
    
    @abstractmethod
    def create(self, schema: CustomSchema) -> CustomSchema:
        """カスタムスキーマを作成"""
        pass
    
    @abstractmethod
    def get_by_id(self, schema_id: UUID) -> Optional[CustomSchema]:
        """IDによるカスタムスキーマの取得"""
        pass
    
    @abstractmethod
    def get_all(self, include_inactive: bool = False) -> List[CustomSchema]:
        """全カスタムスキーマの取得"""
        pass
    
    @abstractmethod
    def get_default_schema(self) -> Optional[CustomSchema]:
        """デフォルトスキーマの取得"""
        pass
    
    @abstractmethod
    def update(self, schema: CustomSchema) -> CustomSchema:
        """カスタムスキーマの更新"""
        pass
    
    @abstractmethod
    def delete(self, schema_id: UUID) -> bool:
        """カスタムスキーマの削除"""
        pass
    
    @abstractmethod
    def set_as_default(self, schema_id: UUID) -> bool:
        """指定したスキーマをデフォルトに設定（他のスキーマのデフォルトフラグは解除）"""
        pass
    
    @abstractmethod
    def duplicate(self, source_schema_id: UUID, new_name: str) -> CustomSchema:
        """スキーマの複製"""
        pass
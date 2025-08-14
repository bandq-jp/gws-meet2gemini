"""
カスタムスキーマのドメインエンティティ

DDD/オニオンアーキテクチャに従い、ビジネスロジックに関わる
カスタムスキーマのエンティティをドメイン層に配置。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID


@dataclass
class SchemaGroup:
    """スキーマグループ"""
    name: str
    description: str


@dataclass
class EnumOption:
    """列挙型の選択肢"""
    id: Optional[UUID]
    value: str
    label: Optional[str] = None
    display_order: int = 0


@dataclass
class ValidationRules:
    """バリデーションルール"""
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None


@dataclass
class SchemaField:
    """スキーマフィールド"""
    id: Optional[UUID]
    field_key: str
    field_label: str
    field_description: Optional[str]
    field_type: str  # string, number, integer, array, boolean, object
    is_required: bool = False
    array_item_type: Optional[str] = None
    group_name: str = ""
    display_order: int = 0
    validation_rules: Optional[ValidationRules] = None
    enum_options: List[EnumOption] = field(default_factory=list)
    
    def to_json_schema_property(self) -> Dict[str, Any]:
        """JSON Schema形式のプロパティ定義に変換"""
        prop = {
            "type": self.field_type,
            "description": self.field_description or self.field_label
        }
        
        # 配列の場合
        if self.field_type == "array":
            if self.array_item_type:
                if self.enum_options:
                    # 配列内の要素が列挙型の場合
                    prop["items"] = {
                        "type": self.array_item_type,
                        "enum": [option.value for option in self.enum_options]
                    }
                else:
                    prop["items"] = {"type": self.array_item_type}
        
        # 列挙型の場合（配列でない）
        elif self.enum_options:
            prop["enum"] = [option.value for option in self.enum_options]
        
        # バリデーションルール
        if self.validation_rules:
            if self.validation_rules.minimum is not None:
                prop["minimum"] = self.validation_rules.minimum
            if self.validation_rules.maximum is not None:
                prop["maximum"] = self.validation_rules.maximum
            if self.validation_rules.min_length is not None:
                prop["minLength"] = self.validation_rules.min_length
            if self.validation_rules.max_length is not None:
                prop["maxLength"] = self.validation_rules.max_length
            if self.validation_rules.pattern:
                prop["pattern"] = self.validation_rules.pattern
        
        return prop


@dataclass
class CustomSchema:
    """カスタムスキーマ"""
    id: Optional[UUID]
    name: str
    description: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    created_by: Optional[str] = None
    base_schema_version: Optional[str] = None
    schema_groups: List[SchemaGroup] = field(default_factory=list)
    fields: List[SchemaField] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def get_fields_by_group(self, group_name: str) -> List[SchemaField]:
        """特定のグループのフィールドを取得"""
        return [field for field in self.fields if field.group_name == group_name]
    
    def to_json_schema_groups(self) -> List[tuple[Dict[str, Any], str]]:
        """JSON Schema形式のグループリストに変換（既存のget_all_schema_groups()と互換性を保つ）"""
        groups = []
        
        for schema_group in self.schema_groups:
            group_fields = self.get_fields_by_group(schema_group.name)
            
            properties = {}
            required = []
            
            for field in group_fields:
                properties[field.field_key] = field.to_json_schema_property()
                if field.is_required:
                    required.append(field.field_key)
            
            schema = {
                "type": "object",
                "properties": properties,
                "required": required
            }
            
            groups.append((schema, schema_group.name))
        
        return groups
    
    def to_full_json_schema(self) -> Dict[str, Any]:
        """完全なJSON Schemaに変換"""
        properties = {}
        required = []
        
        for field in self.fields:
            properties[field.field_key] = field.to_json_schema_property()
            if field.is_required:
                required.append(field.field_key)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required
        }
    
    def validate_schema(self) -> List[str]:
        """スキーマの妥当性を検証し、エラーメッセージのリストを返す"""
        errors = []
        
        if not self.name.strip():
            errors.append("スキーマ名は必須です")
        
        if not self.fields:
            errors.append("少なくとも1つのフィールドが必要です")
        
        # フィールドキーの重複チェック
        field_keys = [field.field_key for field in self.fields]
        if len(field_keys) != len(set(field_keys)):
            errors.append("フィールドキーが重複しています")
        
        # グループ名の存在チェック
        group_names = [group.name for group in self.schema_groups]
        for field in self.fields:
            if field.group_name and field.group_name not in group_names:
                errors.append(f"フィールド '{field.field_key}' のグループ名 '{field.group_name}' が存在しません")
        
        # 各フィールドの妥当性チェック
        for field in self.fields:
            field_errors = self._validate_field(field)
            errors.extend(field_errors)
        
        return errors
    
    def _validate_field(self, field: SchemaField) -> List[str]:
        """個別フィールドの妥当性チェック"""
        errors = []
        
        if not field.field_key.strip():
            errors.append(f"フィールドキーは必須です")
        
        if not field.field_label.strip():
            errors.append(f"フィールドラベル '{field.field_key}' は必須です")
        
        if field.field_type not in ["string", "number", "integer", "array", "boolean", "object"]:
            errors.append(f"フィールド '{field.field_key}' の型が不正です")
        
        if field.field_type == "array" and not field.array_item_type:
            errors.append(f"配列フィールド '{field.field_key}' には要素の型が必要です")
        
        return errors
"""
カスタムスキーマリポジトリのSupabase実装

DDD/オニオンアーキテクチャに従い、インフラ層で
ドメイン層のリポジトリインターフェースを実装。
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json
import logging

from app.domain.entities.custom_schema import CustomSchema, SchemaField, SchemaGroup, EnumOption, ValidationRules
from app.domain.repositories.custom_schema_repository import CustomSchemaRepository
from app.infrastructure.supabase.client import get_supabase

logger = logging.getLogger(__name__)


class CustomSchemaRepositoryImpl(CustomSchemaRepository):
    """カスタムスキーマリポジトリのSupabase実装"""
    
    SCHEMAS_TABLE = "custom_schemas"
    FIELDS_TABLE = "schema_fields"
    ENUM_OPTIONS_TABLE = "field_enum_options"
    
    def __init__(self):
        pass  # Supabaseクライアントは必要な時に取得
    
    def _get_client(self):
        """Supabaseクライアントを取得"""
        return get_supabase()
    
    def create(self, schema: CustomSchema) -> CustomSchema:
        """カスタムスキーマを作成"""
        sb = self._get_client()

        try:
            # 1. スキーマ基本情報を挿入
            schema_data = {
                "name": schema.name,
                "description": schema.description,
                "is_default": schema.is_default,
                "is_active": schema.is_active,
                "created_by": schema.created_by,
                "base_schema_version": schema.base_schema_version,
                "schema_groups": [{"name": g.name, "description": g.description} for g in schema.schema_groups]
            }

            schema_result = sb.table(self.SCHEMAS_TABLE).insert(schema_data).execute()
            if not schema_result.data:
                raise ValueError("カスタムスキーマの作成に失敗しました")

            schema_record = schema_result.data[0]
            schema_id = schema_record["id"]

            # 2. フィールドをバッチ挿入
            self._batch_insert_fields(sb, schema_id, schema.fields)

            # デフォルトスキーマに設定する場合、他のスキーマのデフォルトフラグを解除
            if schema.is_default:
                self._unset_other_defaults(schema_id)

            # 作成されたスキーマを取得して返す
            return self.get_by_id(UUID(schema_id))

        except Exception as e:
            logger.error(f"スキーマ作成エラー: {e}")
            raise ValueError(f"カスタムスキーマの作成に失敗しました: {str(e)}")
    
    def get_by_id(self, schema_id: UUID) -> Optional[CustomSchema]:
        """IDによるカスタムスキーマの取得"""
        sb = self._get_client()

        try:
            # スキーマ基本情報を取得
            schema_result = sb.table(self.SCHEMAS_TABLE).select("*").eq("id", str(schema_id)).maybe_single().execute()

            if not schema_result.data:
                return None

            schema_data = schema_result.data

            # フィールド情報を取得
            fields_result = sb.table(self.FIELDS_TABLE).select("*").eq("custom_schema_id", str(schema_id)).execute()

            fields = []
            if fields_result.data:
                # 全フィールドIDを収集し、enum_optionsを一括取得（N+1解消）
                field_ids = [fd["id"] for fd in fields_result.data if fd.get("id")]
                enum_by_field: Dict[str, list] = {}
                if field_ids:
                    enum_result = sb.table(self.ENUM_OPTIONS_TABLE).select("*").in_("schema_field_id", field_ids).order("display_order").execute()
                    if enum_result.data:
                        for enum_data in enum_result.data:
                            fid = enum_data["schema_field_id"]
                            enum_by_field.setdefault(fid, []).append(enum_data)

                for field_data in fields_result.data:
                    enum_options = [
                        EnumOption(
                            id=UUID(ed["id"]) if ed["id"] else None,
                            value=ed["option_value"],
                            label=ed["option_label"],
                            display_order=ed["display_order"] or 0
                        )
                        for ed in enum_by_field.get(field_data["id"], [])
                    ]

                    field = SchemaField(
                        id=UUID(field_data["id"]) if field_data["id"] else None,
                        field_key=field_data["field_key"],
                        field_label=field_data["field_label"],
                        field_description=field_data["field_description"],
                        field_type=field_data["field_type"],
                        is_required=field_data["is_required"] or False,
                        array_item_type=field_data["array_item_type"],
                        group_name=field_data["group_name"] or "",
                        display_order=field_data["display_order"] or 0,
                        validation_rules=self._dict_to_validation_rules(field_data.get("validation_rules", {})),
                        enum_options=enum_options
                    )
                    fields.append(field)

            return self._build_schema_entity(schema_data, fields)

        except Exception as e:
            logger.error(f"スキーマ取得エラー: {e}")
            return None

    def _build_schema_entity(self, schema_data: Dict[str, Any], fields: List[SchemaField]) -> CustomSchema:
        """スキーマデータとフィールドリストからCustomSchemaエンティティを構築"""
        schema_groups = []
        groups_data = schema_data.get("schema_groups", [])
        if groups_data:
            for group_data in groups_data:
                schema_groups.append(SchemaGroup(
                    name=group_data["name"],
                    description=group_data.get("description", "")
                ))

        return CustomSchema(
            id=UUID(schema_data["id"]),
            name=schema_data["name"],
            description=schema_data["description"],
            is_default=schema_data.get("is_default", False),
            is_active=schema_data.get("is_active", True),
            created_by=schema_data.get("created_by"),
            base_schema_version=schema_data.get("base_schema_version"),
            schema_groups=schema_groups,
            fields=sorted(fields, key=lambda x: (x.group_name, x.display_order)),
            created_at=datetime.fromisoformat(schema_data["created_at"].replace("Z", "+00:00")) if schema_data.get("created_at") else None,
            updated_at=datetime.fromisoformat(schema_data["updated_at"].replace("Z", "+00:00")) if schema_data.get("updated_at") else None
        )
    
    def get_all(self, include_inactive: bool = False) -> List[CustomSchema]:
        """全カスタムスキーマの取得（一括取得で最適化）"""
        sb = self._get_client()

        try:
            query = sb.table(self.SCHEMAS_TABLE).select("*")
            if not include_inactive:
                query = query.eq("is_active", True)

            result = query.order("created_at", desc=True).execute()

            if not result.data:
                return []

            schema_ids = [sd["id"] for sd in result.data]

            # 全スキーマのフィールドを一括取得
            all_fields_result = sb.table(self.FIELDS_TABLE).select("*").in_("custom_schema_id", schema_ids).execute()
            fields_by_schema: Dict[str, list] = {}
            all_field_ids: list = []
            if all_fields_result.data:
                for fd in all_fields_result.data:
                    sid = fd["custom_schema_id"]
                    fields_by_schema.setdefault(sid, []).append(fd)
                    if fd.get("id"):
                        all_field_ids.append(fd["id"])

            # 全フィールドのenum_optionsを一括取得
            enum_by_field: Dict[str, list] = {}
            if all_field_ids:
                all_enum_result = sb.table(self.ENUM_OPTIONS_TABLE).select("*").in_("schema_field_id", all_field_ids).order("display_order").execute()
                if all_enum_result.data:
                    for ed in all_enum_result.data:
                        fid = ed["schema_field_id"]
                        enum_by_field.setdefault(fid, []).append(ed)

            # 各スキーマのエンティティを構築
            schemas = []
            for schema_data in result.data:
                sid = schema_data["id"]
                fields = []
                for field_data in fields_by_schema.get(sid, []):
                    enum_options = [
                        EnumOption(
                            id=UUID(ed["id"]) if ed["id"] else None,
                            value=ed["option_value"],
                            label=ed["option_label"],
                            display_order=ed["display_order"] or 0
                        )
                        for ed in enum_by_field.get(field_data["id"], [])
                    ]
                    fields.append(SchemaField(
                        id=UUID(field_data["id"]) if field_data["id"] else None,
                        field_key=field_data["field_key"],
                        field_label=field_data["field_label"],
                        field_description=field_data["field_description"],
                        field_type=field_data["field_type"],
                        is_required=field_data["is_required"] or False,
                        array_item_type=field_data["array_item_type"],
                        group_name=field_data["group_name"] or "",
                        display_order=field_data["display_order"] or 0,
                        validation_rules=self._dict_to_validation_rules(field_data.get("validation_rules", {})),
                        enum_options=enum_options
                    ))
                schemas.append(self._build_schema_entity(schema_data, fields))

            return schemas

        except Exception as e:
            logger.error(f"スキーマ一覧取得エラー: {e}")
            return []
    
    def get_default_schema(self) -> Optional[CustomSchema]:
        """デフォルトスキーマの取得"""
        sb = self._get_client()
        
        try:
            result = sb.table(self.SCHEMAS_TABLE).select("*").eq("is_default", True).eq("is_active", True).maybe_single().execute()
            
            if not result.data:
                return None
            
            return self.get_by_id(UUID(result.data["id"]))
            
        except Exception as e:
            logger.error(f"デフォルトスキーマ取得エラー: {e}")
            return None
    
    def update(self, schema: CustomSchema) -> CustomSchema:
        """カスタムスキーマの更新"""
        if not schema.id:
            raise ValueError("更新にはスキーマIDが必要です")

        sb = self._get_client()

        try:
            # 1. スキーマ基本情報を更新
            schema_data = {
                "name": schema.name,
                "description": schema.description,
                "is_default": schema.is_default,
                "is_active": schema.is_active,
                "created_by": schema.created_by,
                "base_schema_version": schema.base_schema_version,
                "schema_groups": [{"name": g.name, "description": g.description} for g in schema.schema_groups]
            }

            sb.table(self.SCHEMAS_TABLE).update(schema_data).eq("id", str(schema.id)).execute()

            # 2. 既存フィールドと列挙オプションを削除（CASCADE削除でenumも消える）
            sb.table(self.FIELDS_TABLE).delete().eq("custom_schema_id", str(schema.id)).execute()

            # 3. 新しいフィールドをバッチ挿入
            self._batch_insert_fields(sb, str(schema.id), schema.fields)

            # デフォルトスキーマに設定する場合、他のスキーマのデフォルトフラグを解除
            if schema.is_default:
                self._unset_other_defaults(schema.id)

            return self.get_by_id(schema.id)

        except Exception as e:
            logger.error(f"スキーマ更新エラー: {e}")
            raise ValueError(f"カスタムスキーマの更新に失敗しました: {str(e)}")
    
    def delete(self, schema_id: UUID) -> bool:
        """カスタムスキーマの削除"""
        sb = self._get_client()
        
        try:
            result = sb.table(self.SCHEMAS_TABLE).delete().eq("id", str(schema_id)).execute()
            return result is not None
        except Exception as e:
            logger.error(f"スキーマ削除エラー: {e}")
            return False
    
    def set_as_default(self, schema_id: UUID) -> bool:
        """指定したスキーマをデフォルトに設定"""
        sb = self._get_client()
        
        try:
            # すべてのスキーマのデフォルトフラグを解除
            sb.table(self.SCHEMAS_TABLE).update({"is_default": False}).neq("id", "00000000-0000-0000-0000-000000000000").execute()
            
            # 指定したスキーマをデフォルトに設定
            result = sb.table(self.SCHEMAS_TABLE).update({"is_default": True}).eq("id", str(schema_id)).execute()
            
            return result is not None
        except Exception as e:
            logger.error(f"デフォルトスキーマ設定エラー: {e}")
            return False
    
    def duplicate(self, source_schema_id: UUID, new_name: str) -> CustomSchema:
        """スキーマの複製"""
        source_schema = self.get_by_id(source_schema_id)
        if not source_schema:
            raise ValueError("複製元のスキーマが見つかりません")
        
        # 新しいスキーマを作成（IDをクリア、デフォルトフラグをFalseに）
        new_schema = CustomSchema(
            id=None,
            name=new_name,
            description=f"{source_schema.description} (コピー)" if source_schema.description else "コピー",
            is_default=False,
            is_active=True,
            created_by=source_schema.created_by,
            base_schema_version=source_schema.base_schema_version,
            schema_groups=source_schema.schema_groups.copy(),
            fields=[
                SchemaField(
                    id=None,  # 新しいIDが自動生成される
                    field_key=field.field_key,
                    field_label=field.field_label,
                    field_description=field.field_description,
                    field_type=field.field_type,
                    is_required=field.is_required,
                    array_item_type=field.array_item_type,
                    group_name=field.group_name,
                    display_order=field.display_order,
                    validation_rules=field.validation_rules,
                    enum_options=[
                        EnumOption(
                            id=None,  # 新しいIDが自動生成される
                            value=option.value,
                            label=option.label,
                            display_order=option.display_order
                        )
                        for option in field.enum_options
                    ]
                )
                for field in source_schema.fields
            ]
        )
        
        return self.create(new_schema)
    
    def _batch_insert_fields(self, sb, schema_id: str, fields: Optional[List[SchemaField]]) -> None:
        """フィールドとenum_optionsをバッチinsert"""
        if not fields:
            return

        # フィールドをバッチinsert
        field_payloads = [
            {
                "custom_schema_id": str(schema_id),
                "field_key": field.field_key,
                "field_label": field.field_label,
                "field_description": field.field_description,
                "field_type": field.field_type,
                "is_required": field.is_required,
                "array_item_type": field.array_item_type,
                "group_name": field.group_name,
                "display_order": field.display_order,
                "validation_rules": self._validation_rules_to_dict(field.validation_rules) if field.validation_rules else {}
            }
            for field in fields
        ]

        field_result = sb.table(self.FIELDS_TABLE).insert(field_payloads).execute()
        if not field_result.data:
            return

        # insert結果からfield_idを取得し、enum_optionsをバッチinsert
        enum_payloads = []
        for i, field_record in enumerate(field_result.data):
            field_id = field_record["id"]
            original_field = fields[i]
            if original_field.enum_options:
                for option in original_field.enum_options:
                    enum_payloads.append({
                        "schema_field_id": field_id,
                        "option_value": option.value,
                        "option_label": option.label,
                        "display_order": option.display_order
                    })

        if enum_payloads:
            sb.table(self.ENUM_OPTIONS_TABLE).insert(enum_payloads).execute()

    def _unset_other_defaults(self, current_schema_id: UUID):
        """他のスキーマのデフォルトフラグを解除"""
        sb = self._get_client()
        try:
            sb.table(self.SCHEMAS_TABLE).update({"is_default": False}).neq("id", str(current_schema_id)).execute()
        except Exception as e:
            logger.error(f"他のデフォルトフラグ解除エラー: {e}")
    
    def _validation_rules_to_dict(self, rules: ValidationRules) -> Dict[str, Any]:
        """ValidationRulesをJSONB用の辞書に変換"""
        result = {}
        if rules.minimum is not None:
            result["minimum"] = rules.minimum
        if rules.maximum is not None:
            result["maximum"] = rules.maximum
        if rules.min_length is not None:
            result["min_length"] = rules.min_length
        if rules.max_length is not None:
            result["max_length"] = rules.max_length
        if rules.pattern:
            result["pattern"] = rules.pattern
        return result
    
    def _dict_to_validation_rules(self, data: Dict[str, Any]) -> Optional[ValidationRules]:
        """辞書からValidationRulesを復元"""
        if not data:
            return None
        
        return ValidationRules(
            minimum=data.get("minimum"),
            maximum=data.get("maximum"),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
            pattern=data.get("pattern")
        )
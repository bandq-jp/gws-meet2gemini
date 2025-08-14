"""
カスタムスキーマ管理ユースケース

DDD/オニオンアーキテクチャに従い、アプリケーション層で
ビジネスロジックの管理を行う。
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.domain.entities.custom_schema import CustomSchema, SchemaField, SchemaGroup, EnumOption, ValidationRules
from app.domain.repositories.custom_schema_repository import CustomSchemaRepository
from app.domain.schemas.structured_extraction_schema import StructuredExtractionSchema


class ManageCustomSchemasUseCase:
    """カスタムスキーマ管理ユースケース"""
    
    def __init__(self, repository: CustomSchemaRepository):
        self.repository = repository
    
    def create_schema(self, schema: CustomSchema) -> CustomSchema:
        """カスタムスキーマを作成"""
        # バリデーション
        errors = schema.validate_schema()
        if errors:
            raise ValueError(f"スキーマが無効です: {', '.join(errors)}")
        
        return self.repository.create(schema)
    
    def get_schema(self, schema_id: UUID) -> Optional[CustomSchema]:
        """カスタムスキーマを取得"""
        return self.repository.get_by_id(schema_id)
    
    def get_all_schemas(self, include_inactive: bool = False) -> List[CustomSchema]:
        """全カスタムスキーマを取得"""
        return self.repository.get_all(include_inactive)
    
    def get_default_schema(self) -> Optional[CustomSchema]:
        """デフォルトスキーマを取得"""
        return self.repository.get_default_schema()
    
    def update_schema(self, schema: CustomSchema) -> CustomSchema:
        """カスタムスキーマを更新"""
        # バリデーション
        errors = schema.validate_schema()
        if errors:
            raise ValueError(f"スキーマが無効です: {', '.join(errors)}")
        
        return self.repository.update(schema)
    
    def delete_schema(self, schema_id: UUID) -> bool:
        """カスタムスキーマを削除"""
        # デフォルトスキーマの削除は禁止
        schema = self.repository.get_by_id(schema_id)
        if schema and schema.is_default:
            raise ValueError("デフォルトスキーマは削除できません")
        
        return self.repository.delete(schema_id)
    
    def set_default_schema(self, schema_id: UUID) -> bool:
        """指定したスキーマをデフォルトに設定"""
        schema = self.repository.get_by_id(schema_id)
        if not schema:
            raise ValueError("指定されたスキーマが存在しません")
        
        if not schema.is_active:
            raise ValueError("非アクティブなスキーマはデフォルトに設定できません")
        
        return self.repository.set_as_default(schema_id)
    
    def duplicate_schema(self, source_schema_id: UUID, new_name: str) -> CustomSchema:
        """スキーマを複製"""
        if not new_name.strip():
            raise ValueError("新しいスキーマ名は必須です")
        
        # 同名のスキーマが存在しないかチェック
        existing_schemas = self.repository.get_all()
        if any(s.name == new_name for s in existing_schemas):
            raise ValueError(f"スキーマ名 '{new_name}' は既に存在します")
        
        return self.repository.duplicate(source_schema_id, new_name)
    
    def get_default_schema_definition(self) -> CustomSchema:
        """現在のコード定義からデフォルトスキーマを生成"""
        # 既存のStructuredExtractionSchemaからカスタムスキーマを生成
        schema_groups_data = StructuredExtractionSchema.get_all_schema_groups()
        
        schema_groups = []
        fields = []
        
        for schema_dict, group_name in schema_groups_data:
            # グループを作成
            schema_groups.append(SchemaGroup(
                name=group_name,
                description=group_name
            ))
            
            # フィールドを処理
            properties = schema_dict.get("properties", {})
            required_fields = schema_dict.get("required", [])
            
            for field_key, field_def in properties.items():
                field = self._convert_json_schema_to_field(
                    field_key, field_def, group_name, field_key in required_fields
                )
                fields.append(field)
        
        return CustomSchema(
            id=None,
            name="システムデフォルトスキーマ",
            description="システムに組み込まれているデフォルトの構造化データ抽出スキーマ",
            is_default=True,
            is_active=True,
            base_schema_version="v1.0",
            schema_groups=schema_groups,
            fields=fields
        )
    
    def initialize_default_schema_in_db(self) -> CustomSchema:
        """デフォルトスキーマをデータベースに初期化（初回セットアップ用）"""
        # 既にデフォルトスキーマが存在するかチェック
        existing_default = self.repository.get_default_schema()
        if existing_default:
            return existing_default
        
        # システム定義からデフォルトスキーマを作成
        default_schema = self.get_default_schema_definition()
        return self.repository.create(default_schema)
    
    def _convert_json_schema_to_field(
        self, 
        field_key: str, 
        field_def: Dict[str, Any], 
        group_name: str, 
        is_required: bool
    ) -> SchemaField:
        """JSON Schema定義からSchemaFieldに変換"""
        field_type = field_def.get("type", "string")
        description = field_def.get("description", "")
        
        # 列挙型オプションの処理
        enum_options = []
        enum_values = field_def.get("enum", [])
        
        # 配列の場合、itemsの中の列挙型を確認
        array_item_type = None
        if field_type == "array":
            items = field_def.get("items", {})
            array_item_type = items.get("type", "string")
            if "enum" in items:
                enum_values = items["enum"]
        
        # 列挙型オプションを作成
        for i, value in enumerate(enum_values):
            enum_options.append(EnumOption(
                id=None,
                value=value,
                label=None,
                display_order=i
            ))
        
        # バリデーションルール
        validation_rules = None
        if any(key in field_def for key in ["minimum", "maximum", "minLength", "maxLength", "pattern"]):
            validation_rules = ValidationRules(
                minimum=field_def.get("minimum"),
                maximum=field_def.get("maximum"),
                min_length=field_def.get("minLength"),
                max_length=field_def.get("maxLength"),
                pattern=field_def.get("pattern")
            )
        
        # 表示用のラベルを生成（field_key から推測または description を使用）
        field_label = self._generate_field_label(field_key, description)
        
        return SchemaField(
            id=None,
            field_key=field_key,
            field_label=field_label,
            field_description=description,
            field_type=field_type,
            is_required=is_required,
            array_item_type=array_item_type,
            group_name=group_name,
            display_order=0,  # 後で適切に設定
            validation_rules=validation_rules,
            enum_options=enum_options
        )
    
    def _generate_field_label(self, field_key: str, description: str) -> str:
        """フィールドキーから表示用ラベルを生成"""
        # descriptionの最初の部分を使用（「:」より前）
        if description and "：" in description:
            return description.split("：")[0]
        elif description and ":" in description:
            return description.split(":")[0]
        
        # フィールドキーから推測
        label_map = {
            "transfer_activity_status": "転職活動状況",
            "agent_count": "エージェント数",
            "current_agents": "現在のエージェント",
            "introduced_jobs": "紹介求人",
            "job_appeal_points": "求人の魅力点",
            "job_concerns": "求人の懸念点",
            "companies_in_selection": "選考中の企業",
            "other_offer_salary": "他社オファー年収",
            "other_company_intention": "他社意向度",
            "transfer_reasons": "転職理由",
            "transfer_trigger": "転職のきっかけ",
            "desired_timing": "希望時期",
            "timing_details": "希望時期詳細",
            "current_job_status": "現職状況",
            "transfer_status_memo": "転職状況メモ",
            "transfer_axis_primary": "転職軸（最重要）",
            "transfer_priorities": "転職軸（全般）",
            "career_history": "職歴",
            "current_duties": "現職業務",
            "company_good_points": "現職の良い点",
            "company_bad_points": "現職の悪い点",
            "enjoyed_work": "楽しかった仕事",
            "difficult_work": "辛かった仕事",
            "experience_industry": "経験業界",
            "experience_field_hr": "経験領域（人材）",
            "desired_industry": "希望業界",
            "industry_reason": "業界希望理由",
            "desired_position": "希望職種",
            "position_industry_reason": "職種・業界希望理由",
            "current_salary": "現年収",
            "salary_breakdown": "年収内訳",
            "desired_first_year_salary": "初年度希望年収",
            "base_incentive_ratio": "基本給・インセンティブ比率",
            "max_future_salary": "将来最大年収",
            "salary_memo": "給与メモ",
            "remote_time_memo": "リモート・時間メモ",
            "ca_ra_focus": "CA起点/RA起点",
            "customer_acquisition": "集客方法・比率",
            "new_existing_ratio": "新規・既存比率",
            "business_vision": "事業構想",
            "desired_employee_count": "希望従業員数",
            "culture_scale_memo": "企業文化・規模メモ",
            "career_vision": "キャリアビジョン"
        }
        
        return label_map.get(field_key, field_key.replace("_", " ").title())
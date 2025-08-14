#!/usr/bin/env python3
"""デフォルトスキーマ生成のテストスクリプト"""

from app.application.use_cases.manage_custom_schemas import ManageCustomSchemasUseCase
from app.infrastructure.supabase.repositories.custom_schema_repository_impl import CustomSchemaRepositoryImpl

def test_schema_generation():
    try:
        repository = CustomSchemaRepositoryImpl()
        use_case = ManageCustomSchemasUseCase(repository)
        
        print("=== デフォルトスキーマ定義生成テスト ===")
        default_schema = use_case.get_default_schema_definition()
        
        print(f"スキーマ名: {default_schema.name}")
        print(f"説明: {default_schema.description}")
        print(f"グループ数: {len(default_schema.schema_groups)}")
        print(f"フィールド数: {len(default_schema.fields)}")
        
        print("\n=== グループ一覧 ===")
        for i, group in enumerate(default_schema.schema_groups):
            print(f"{i+1}. {group.name} - {group.description}")
        
        print("\n=== フィールドサンプル（最初の10個）===")
        for i, field in enumerate(default_schema.fields[:10]):
            print(f"{i+1}. {field.field_key}")
            print(f"   ラベル: {field.field_label}")
            print(f"   型: {field.field_type}")
            print(f"   グループ: {field.group_name}")
            print(f"   選択肢数: {len(field.enum_options)}")
            if field.enum_options:
                print(f"   選択肢例: {field.enum_options[0].value}")
            print()
        
        # バリデーション
        errors = default_schema.validate_schema()
        if errors:
            print(f"=== バリデーションエラー ===")
            for error in errors:
                print(f"- {error}")
        else:
            print("=== バリデーション結果: OK ===")
        
    except Exception as e:
        print(f"エラー発生: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_schema_generation()
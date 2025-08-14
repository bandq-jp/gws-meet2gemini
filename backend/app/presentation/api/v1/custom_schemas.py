"""
カスタムスキーマ管理のAPIエンドポイント

FastAPIルーターでカスタムスキーマのCRUD操作を提供。
DDD/オニオンアーキテクチャに従い、プレゼンテーション層で
HTTPリクエスト/レスポンスの変換を行う。
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime

from app.application.use_cases.manage_custom_schemas import ManageCustomSchemasUseCase
from app.domain.entities.custom_schema import CustomSchema, SchemaField, SchemaGroup, EnumOption, ValidationRules
from app.infrastructure.supabase.repositories.custom_schema_repository_impl import CustomSchemaRepositoryImpl


# DTOクラス（Data Transfer Objects）
class EnumOptionDTO(BaseModel):
    """列挙型選択肢DTO"""
    id: Optional[UUID] = None
    value: str
    label: Optional[str] = None
    display_order: int = 0


class ValidationRulesDTO(BaseModel):
    """バリデーションルールDTO"""
    minimum: Optional[int] = None
    maximum: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None


class SchemaFieldDTO(BaseModel):
    """スキーマフィールドDTO"""
    id: Optional[UUID] = None
    field_key: str
    field_label: str
    field_description: Optional[str] = None
    field_type: str = Field(..., pattern="^(string|number|integer|array|boolean|object)$")
    is_required: bool = False
    array_item_type: Optional[str] = None
    group_name: str = ""
    display_order: int = 0
    validation_rules: Optional[ValidationRulesDTO] = None
    enum_options: List[EnumOptionDTO] = Field(default_factory=list)


class SchemaGroupDTO(BaseModel):
    """スキーマグループDTO"""
    name: str
    description: str


class CustomSchemaDTO(BaseModel):
    """カスタムスキーマDTO"""
    id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    created_by: Optional[str] = None
    base_schema_version: Optional[str] = None
    schema_groups: List[SchemaGroupDTO] = Field(default_factory=list)
    fields: List[SchemaFieldDTO] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateSchemaRequest(BaseModel):
    """スキーマ作成リクエスト"""
    name: str
    description: Optional[str] = None
    is_default: bool = False
    schema_groups: List[SchemaGroupDTO] = Field(default_factory=list)
    fields: List[SchemaFieldDTO] = Field(default_factory=list)


class UpdateSchemaRequest(BaseModel):
    """スキーマ更新リクエスト"""
    name: str
    description: Optional[str] = None
    is_default: bool = False
    is_active: bool = True
    schema_groups: List[SchemaGroupDTO] = Field(default_factory=list)
    fields: List[SchemaFieldDTO] = Field(default_factory=list)


class DuplicateSchemaRequest(BaseModel):
    """スキーマ複製リクエスト"""
    new_name: str


# DTOとドメインエンティティの変換
def dto_to_domain(dto: CustomSchemaDTO) -> CustomSchema:
    """DTOからドメインエンティティに変換"""
    return CustomSchema(
        id=dto.id,
        name=dto.name,
        description=dto.description,
        is_default=dto.is_default,
        is_active=dto.is_active,
        created_by=dto.created_by,
        base_schema_version=dto.base_schema_version,
        schema_groups=[
            SchemaGroup(name=g.name, description=g.description) 
            for g in dto.schema_groups
        ],
        fields=[
            SchemaField(
                id=f.id,
                field_key=f.field_key,
                field_label=f.field_label,
                field_description=f.field_description,
                field_type=f.field_type,
                is_required=f.is_required,
                array_item_type=f.array_item_type,
                group_name=f.group_name,
                display_order=f.display_order,
                validation_rules=ValidationRules(
                    minimum=f.validation_rules.minimum,
                    maximum=f.validation_rules.maximum,
                    min_length=f.validation_rules.min_length,
                    max_length=f.validation_rules.max_length,
                    pattern=f.validation_rules.pattern
                ) if f.validation_rules else None,
                enum_options=[
                    EnumOption(
                        id=opt.id,
                        value=opt.value,
                        label=opt.label,
                        display_order=opt.display_order
                    )
                    for opt in f.enum_options
                ]
            )
            for f in dto.fields
        ],
        created_at=dto.created_at,
        updated_at=dto.updated_at
    )


def domain_to_dto(entity: CustomSchema) -> CustomSchemaDTO:
    """ドメインエンティティからDTOに変換"""
    return CustomSchemaDTO(
        id=entity.id,
        name=entity.name,
        description=entity.description,
        is_default=entity.is_default,
        is_active=entity.is_active,
        created_by=entity.created_by,
        base_schema_version=entity.base_schema_version,
        schema_groups=[
            SchemaGroupDTO(name=g.name, description=g.description) 
            for g in entity.schema_groups
        ],
        fields=[
            SchemaFieldDTO(
                id=f.id,
                field_key=f.field_key,
                field_label=f.field_label,
                field_description=f.field_description,
                field_type=f.field_type,
                is_required=f.is_required,
                array_item_type=f.array_item_type,
                group_name=f.group_name,
                display_order=f.display_order,
                validation_rules=ValidationRulesDTO(
                    minimum=f.validation_rules.minimum,
                    maximum=f.validation_rules.maximum,
                    min_length=f.validation_rules.min_length,
                    max_length=f.validation_rules.max_length,
                    pattern=f.validation_rules.pattern
                ) if f.validation_rules else None,
                enum_options=[
                    EnumOptionDTO(
                        id=opt.id,
                        value=opt.value,
                        label=opt.label,
                        display_order=opt.display_order
                    )
                    for opt in f.enum_options
                ]
            )
            for f in entity.fields
        ],
        created_at=entity.created_at,
        updated_at=entity.updated_at
    )


# 依存性注入
def get_use_case() -> ManageCustomSchemasUseCase:
    """ユースケースのファクトリ関数"""
    repository = CustomSchemaRepositoryImpl()
    return ManageCustomSchemasUseCase(repository)


router = APIRouter(prefix="/custom-schemas", tags=["custom-schemas"])


@router.get("/", response_model=List[CustomSchemaDTO])
def get_all_schemas(
    include_inactive: bool = False,
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """全カスタムスキーマを取得"""
    try:
        schemas = use_case.get_all_schemas(include_inactive)
        return [domain_to_dto(schema) for schema in schemas]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"スキーマの取得に失敗しました: {str(e)}"
        )


@router.get("/default", response_model=Optional[CustomSchemaDTO])
def get_default_schema(
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """デフォルトスキーマを取得"""
    try:
        schema = use_case.get_default_schema()
        return domain_to_dto(schema) if schema else None
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"デフォルトスキーマの取得に失敗しました: {str(e)}"
        )


@router.get("/default-definition", response_model=CustomSchemaDTO)
def get_default_schema_definition(
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """システム定義のデフォルトスキーマを取得"""
    try:
        schema = use_case.get_default_schema_definition()
        return domain_to_dto(schema)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"デフォルトスキーマ定義の取得に失敗しました: {str(e)}"
        )


@router.post("/init-default", response_model=CustomSchemaDTO)
def initialize_default_schema(
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """デフォルトスキーマをデータベースに初期化"""
    try:
        schema = use_case.initialize_default_schema_in_db()
        return domain_to_dto(schema)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"デフォルトスキーマの初期化に失敗しました: {str(e)}"
        )


@router.get("/{schema_id}", response_model=CustomSchemaDTO)
def get_schema(
    schema_id: UUID,
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """指定IDのカスタムスキーマを取得"""
    try:
        schema = use_case.get_schema(schema_id)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたスキーマが見つかりません"
            )
        return domain_to_dto(schema)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"スキーマの取得に失敗しました: {str(e)}"
        )


@router.post("/", response_model=CustomSchemaDTO, status_code=status.HTTP_201_CREATED)
def create_schema(
    request: CreateSchemaRequest,
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """カスタムスキーマを作成"""
    try:
        schema_dto = CustomSchemaDTO(
            name=request.name,
            description=request.description,
            is_default=request.is_default,
            schema_groups=request.schema_groups,
            fields=request.fields
        )
        schema = dto_to_domain(schema_dto)
        created_schema = use_case.create_schema(schema)
        return domain_to_dto(created_schema)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"スキーマの作成に失敗しました: {str(e)}"
        )


@router.put("/{schema_id}", response_model=CustomSchemaDTO)
def update_schema(
    schema_id: UUID,
    request: UpdateSchemaRequest,
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """カスタムスキーマを更新"""
    try:
        schema_dto = CustomSchemaDTO(
            id=schema_id,
            name=request.name,
            description=request.description,
            is_default=request.is_default,
            is_active=request.is_active,
            schema_groups=request.schema_groups,
            fields=request.fields
        )
        schema = dto_to_domain(schema_dto)
        updated_schema = use_case.update_schema(schema)
        return domain_to_dto(updated_schema)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"スキーマの更新に失敗しました: {str(e)}"
        )


@router.delete("/{schema_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schema(
    schema_id: UUID,
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """カスタムスキーマを削除"""
    try:
        success = use_case.delete_schema(schema_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたスキーマが見つかりません"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"スキーマの削除に失敗しました: {str(e)}"
        )


@router.post("/{schema_id}/set-default", response_model=Dict[str, str])
def set_default_schema(
    schema_id: UUID,
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """指定したスキーマをデフォルトに設定"""
    try:
        success = use_case.set_default_schema(schema_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="指定されたスキーマが見つかりません"
            )
        return {"message": "デフォルトスキーマを設定しました"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"デフォルトスキーマの設定に失敗しました: {str(e)}"
        )


@router.post("/{schema_id}/duplicate", response_model=CustomSchemaDTO)
def duplicate_schema(
    schema_id: UUID,
    request: DuplicateSchemaRequest,
    use_case: ManageCustomSchemasUseCase = Depends(get_use_case)
):
    """スキーマを複製"""
    try:
        duplicated_schema = use_case.duplicate_schema(schema_id, request.new_name)
        return domain_to_dto(duplicated_schema)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"スキーマの複製に失敗しました: {str(e)}"
        )
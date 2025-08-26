from __future__ import annotations
from fastapi import APIRouter, Query, HTTPException

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError, ZohoFieldValidator, ZohoFieldMappingError

router = APIRouter()


@router.get("/app-hc/search", response_model=dict)
async def search_app_hc(name: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=50)):
    """Read-only: APP-hc(=CustomModule1) を候補者名で検索し、最低限の情報を返却。

    Returns: { items: [{record_id, candidate_name, candidate_id}], count }
    """
    try:
        client = ZohoClient()
        items = client.search_app_hc_by_name(name=name.strip(), limit=limit)
        return {"items": items, "count": len(items)}
    except ZohoAuthError as e:
        # Zoho認証エラーは400で返すが、詳細なエラーメッセージを含める
        raise HTTPException(
            status_code=400, 
            detail=f"Zoho authentication failed: {str(e)}. Please check Zoho CRM credentials."
        )
    except Exception as e:
        # その他のエラーは500で返し、Zoho APIが利用できない旨を明示
        raise HTTPException(
            status_code=500, 
            detail=f"Zoho CRM service unavailable: {str(e)}. Search functionality temporarily disabled."
        )


@router.get("/modules", response_model=dict)
async def list_modules():
    """Read-only: Zoho CRM modules の一覧（api_name とラベル）を返す。"""
    client = ZohoClient()
    try:
        mods = client.list_modules()
        return {"items": mods, "count": len(mods)}
    except ZohoAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Zoho modules failed: {e}")


@router.get("/fields", response_model=dict)
async def list_fields(module: str = Query(..., min_length=1)):
    """Read-only: 指定モジュールのフィールド一覧（api_name と display_label）。"""
    client = ZohoClient()
    try:
        fields = client.list_fields(module)
        return {"items": fields, "count": len(fields), "module": module}
    except ZohoAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Zoho fields failed: {e}")


@router.get("/app-hc/{record_id}", response_model=dict)
async def get_app_hc_detail(record_id: str):
    """Read-only: APP-hc(=CustomModule1) の単一レコード詳細。

    Returns: { record: {...} }
    """
    try:
        client = ZohoClient()
        record = client.get_app_hc_record(record_id)
        return {"record": record, "record_id": record_id}
    except ZohoAuthError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Zoho authentication failed: {str(e)}. Please check Zoho CRM credentials."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Zoho CRM service unavailable: {str(e)}. Record retrieval temporarily disabled."
        )


@router.get("/validate/field-mapping", response_model=dict)
async def validate_field_mapping(module: str = Query("jobSeeker", description="検証対象モジュール")):
    """フィールドマッピングの妥当性を検証（構造化データ→Zohoフィールドのマッピング）"""
    try:
        validator = ZohoFieldValidator()
        result = validator.validate_field_mapping(module)
        return {
            "validation_result": result,
            "summary": {
                "total_fields": result["total_mapped_fields"],
                "valid_fields": result["valid_fields_count"], 
                "missing_fields": result["missing_fields_count"],
                "is_valid": result["is_valid"]
            }
        }
    except ZohoFieldMappingError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Field mapping validation failed: {str(e)}"
        )
    except ZohoAuthError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Zoho authentication failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Field mapping validation error: {str(e)}"
        )


@router.get("/validate/record-layout/{record_id}", response_model=dict)
async def validate_record_layout(
    record_id: str, 
    module: str = Query("jobSeeker", description="検証対象モジュール")
):
    """特定レコードのレイアウト検証（構造化データ書き込み対応チェック）"""
    try:
        validator = ZohoFieldValidator()
        result = validator.validate_record_layout(record_id, module)
        return {
            "validation_result": result,
            "summary": {
                "record_id": record_id,
                "has_required_layout": result["record_has_required_layout"],
                "available_fields": result["available_fields_count"],
                "unavailable_fields": result["unavailable_fields_count"],
                "field_mapping_valid": result["field_mapping_valid"]
            },
            "recommendation": {
                "can_write_structured_data": result["record_has_required_layout"],
                "issues": [
                    f"{len(result['missing_field_definitions'])}個のフィールド定義が不足" 
                    if result['missing_field_definitions'] else None,
                    f"{result['unavailable_fields_count']}個のフィールドがレコードに存在しない" 
                    if result['unavailable_fields_count'] > 0 else None
                ]
            }
        }
    except ZohoFieldMappingError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Record layout validation failed: {str(e)}"
        )
    except ZohoAuthError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Zoho authentication failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Record layout validation error: {str(e)}"
        )


@router.post("/validate/pre-write/{record_id}", response_model=dict)
async def validate_pre_write(record_id: str, structured_data: dict):
    """書き込み前の総合検証（実際の構造化データを使用した書き込み可否チェック）"""
    try:
        validator = ZohoFieldValidator()
        result = validator.pre_write_validation(record_id, structured_data)
        return {
            "validation_result": result,
            "summary": {
                "record_id": record_id,
                "can_proceed_with_write": result["can_proceed_with_write"],
                "writable_fields": result["writable_fields_count"],
                "blocked_fields": result["blocked_fields_count"],
                "input_data_fields": result["input_data_fields"]
            },
            "details": {
                "writable_fields": result["writable_fields"],
                "blocked_fields": result["blocked_fields"]
            },
            "recommendation": {
                "proceed": result["can_proceed_with_write"],
                "message": "書き込み可能です" if result["can_proceed_with_write"] else "書き込みに問題があります",
                "issues": [
                    f"{result['blocked_fields_count']}個のフィールドが書き込み不可" 
                    if result['blocked_fields_count'] > 0 else None,
                    "レコードレイアウトに問題があります" 
                    if not result['layout_validation']['record_has_required_layout'] else None
                ]
            }
        }
    except ZohoFieldMappingError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Pre-write validation failed: {str(e)}"
        )
    except ZohoAuthError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Zoho authentication failed: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Pre-write validation error: {str(e)}"
        )

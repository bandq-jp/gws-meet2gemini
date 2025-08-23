from __future__ import annotations
from fastapi import APIRouter, Query, HTTPException

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError

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


@router.get("/app-hc/{record_id}/layout-check", response_model=dict)
async def check_app_hc_layout(record_id: str):
    """求職者レコードのレイアウトをチェックして、構造化出力可能かどうかを判定する

    Returns: {
        status: "success"|"error",
        layout_id: str,
        layout_name: str, 
        layout_display_label: str,
        is_valid_layout: bool,
        message: str
    }
    """
    try:
        client = ZohoClient()
        layout_check_result = client.check_record_layout(record_id)
        return layout_check_result
    except ZohoAuthError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Zoho authentication failed: {str(e)}. Please check Zoho CRM credentials."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Layout check service unavailable: {str(e)}."
        )

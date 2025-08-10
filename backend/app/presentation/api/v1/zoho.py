from __future__ import annotations
from fastapi import APIRouter, Query, HTTPException

from app.infrastructure.zoho.client import ZohoClient, ZohoAuthError

router = APIRouter()


@router.get("/app-hc/search", response_model=dict)
async def search_app_hc(name: str = Query(..., min_length=1), limit: int = Query(5, ge=1, le=50)):
    """Read-only: APP-hc(=CustomModule1) を候補者名で検索し、最低限の情報を返却。

    Returns: { items: [{record_id, candidate_name, candidate_id}], count }
    """
    client = ZohoClient()
    try:
        items = client.search_app_hc_by_name(name=name.strip(), limit=limit)
        return {"items": items, "count": len(items)}
    except ZohoAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Zoho search failed: {e}")


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
    client = ZohoClient()
    try:
        record = client.get_app_hc_record(record_id)
        return {"record": record, "record_id": record_id}
    except ZohoAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Zoho record failed: {e}")

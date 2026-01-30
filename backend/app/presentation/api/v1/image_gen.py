"""
画像生成 API ルーター

テンプレート管理、リファレンス画像管理、セッション管理、画像生成のエンドポイント。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

from app.application.use_cases import image_gen as use_cases
from app.infrastructure.supabase.repositories.image_gen_repository import (
    OUTPUTS_BUCKET,
    REFERENCES_BUCKET,
    ImageGenRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/image-gen", tags=["image-gen"])


# ── Schemas ──


class TemplateCreate(BaseModel):
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    aspect_ratio: str = "auto"
    image_size: str = "1K"
    system_prompt: Optional[str] = None
    visibility: str = "public"
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    aspect_ratio: Optional[str] = None
    image_size: Optional[str] = None
    system_prompt: Optional[str] = None
    visibility: Optional[str] = None
    thumbnail_url: Optional[str] = None


class SessionCreate(BaseModel):
    template_id: Optional[str] = None
    title: Optional[str] = None
    aspect_ratio: str = "auto"
    image_size: str = "1K"
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None


class GenerateRequest(BaseModel):
    prompt: str
    aspect_ratio: Optional[str] = None
    image_size: Optional[str] = None


class ReorderRequest(BaseModel):
    reference_ids: List[str]


# ── Templates ──


@router.get("/templates")
def list_templates(
    created_by: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    return use_cases.list_templates(created_by=created_by)


@router.get("/templates/{template_id}")
def get_template(template_id: str) -> Dict[str, Any]:
    result = use_cases.get_template(template_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


@router.post("/templates")
def create_template(body: TemplateCreate) -> Dict[str, Any]:
    return use_cases.create_template(**body.model_dump())


@router.put("/templates/{template_id}")
def update_template(template_id: str, body: TemplateUpdate) -> Dict[str, Any]:
    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=400, detail="No fields to update")
    return use_cases.update_template(template_id, payload)


@router.delete("/templates/{template_id}")
def delete_template(template_id: str) -> Dict[str, str]:
    use_cases.delete_template(template_id)
    return {"status": "deleted"}


# ── References ──


@router.post("/templates/{template_id}/references")
async def upload_reference(
    template_id: str,
    file: UploadFile = File(...),
    label: str = Form("style"),
) -> Dict[str, Any]:
    if label not in ("object", "person", "style"):
        raise HTTPException(status_code=400, detail="label must be object, person, or style")

    content = await file.read()
    mime = file.content_type or "image/png"

    try:
        return use_cases.upload_reference(
            template_id=template_id,
            filename=file.filename or "image.png",
            file_bytes=content,
            mime_type=mime,
            size_bytes=len(content),
            label=label,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/references/{reference_id}")
def delete_reference(reference_id: str) -> Dict[str, str]:
    use_cases.delete_reference(reference_id)
    return {"status": "deleted"}


@router.put("/templates/{template_id}/references/order")
def reorder_references(template_id: str, body: ReorderRequest) -> Dict[str, str]:
    use_cases.reorder_references(template_id, body.reference_ids)
    return {"status": "reordered"}


# ── Sessions ──


@router.get("/sessions")
def list_sessions(
    created_by: Optional[str] = Query(None),
) -> List[Dict[str, Any]]:
    return use_cases.list_sessions(created_by=created_by)


@router.get("/sessions/{session_id}")
def get_session(session_id: str) -> Dict[str, Any]:
    result = use_cases.get_session(session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.post("/sessions")
def create_session(body: SessionCreate) -> Dict[str, Any]:
    return use_cases.create_session(**body.model_dump())


# ── Image Generation ──


@router.post("/sessions/{session_id}/generate")
def generate_image(session_id: str, body: GenerateRequest) -> Dict[str, Any]:
    try:
        return use_cases.generate_image(
            session_id=session_id,
            prompt=body.prompt,
            aspect_ratio=body.aspect_ratio,
            image_size=body.image_size,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Image generation failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Image generation failed")


# ── Image Serving ──


@router.get("/images/{bucket}/{path:path}")
def serve_image(bucket: str, path: str) -> Response:
    if bucket not in (REFERENCES_BUCKET, OUTPUTS_BUCKET):
        raise HTTPException(status_code=400, detail="Invalid bucket")
    try:
        repo = ImageGenRepository()
        data = repo.download_image(bucket, path)
        # Detect mime type from extension
        mime = "image/png"
        if path.endswith(".jpeg") or path.endswith(".jpg"):
            mime = "image/jpeg"
        elif path.endswith(".webp"):
            mime = "image/webp"
        return Response(content=data, media_type=mime)
    except Exception as e:
        logger.error("Failed to serve image %s/%s: %s", bucket, path, e)
        raise HTTPException(status_code=404, detail="Image not found")

"""
画像生成ユースケース

テンプレート管理、リファレンス画像管理、セッション管理、画像生成を統合する。
Multi-turn会話対応: セッション内の過去メッセージ（Thought Signature含む）を
Gemini APIに渡して文脈を維持する。
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from google.genai import types

from app.infrastructure.config.settings import get_settings
from app.infrastructure.gemini.image_generator import (
    GeminiImageGenerator,
    _deserialize_to_content,
)
from app.infrastructure.supabase.repositories.image_gen_repository import (
    ImageGenRepository,
    OUTPUTS_BUCKET,
    REFERENCES_BUCKET,
)

logger = logging.getLogger(__name__)


def _get_repo() -> ImageGenRepository:
    return ImageGenRepository()


def _get_generator() -> GeminiImageGenerator:
    settings = get_settings()
    return GeminiImageGenerator(api_key=settings.image_gen_gemini_api_key)


# ── Templates ──


def list_templates(created_by: Optional[str] = None) -> List[Dict[str, Any]]:
    return _get_repo().list_templates(created_by=created_by)


def get_template(template_id: str) -> Optional[Dict[str, Any]]:
    return _get_repo().get_template(template_id)


def create_template(
    name: str,
    description: Optional[str] = None,
    category: Optional[str] = None,
    aspect_ratio: str = "auto",
    image_size: str = "1K",
    system_prompt: Optional[str] = None,
    visibility: str = "public",
    created_by: Optional[str] = None,
    created_by_email: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "name": name,
        "description": description,
        "category": category,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
        "system_prompt": system_prompt,
        "visibility": visibility,
        "created_by": created_by,
        "created_by_email": created_by_email,
    }
    return _get_repo().create_template(payload)


def update_template(template_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "name", "description", "category", "aspect_ratio",
        "image_size", "system_prompt", "visibility", "thumbnail_url",
    }
    filtered = {k: v for k, v in payload.items() if k in allowed}
    return _get_repo().update_template(template_id, filtered)


def delete_template(template_id: str) -> bool:
    return _get_repo().delete_template(template_id)


# ── References ──


def upload_reference(
    template_id: str,
    filename: str,
    file_bytes: bytes,
    mime_type: str,
    size_bytes: int,
    label: str = "style",
) -> Dict[str, Any]:
    # Validate max references (14)
    repo = _get_repo()
    template = repo.get_template(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")

    existing_refs = template.get("image_gen_references", [])
    if len(existing_refs) >= 14:
        raise ValueError("Maximum 14 reference images allowed per template")

    # Validate person label count (max 5)
    if label == "person":
        person_count = sum(1 for r in existing_refs if r.get("label") == "person")
        if person_count >= 5:
            raise ValueError("Maximum 5 person reference images allowed")

    return repo.add_reference(
        template_id=template_id,
        filename=filename,
        file_bytes=file_bytes,
        mime_type=mime_type,
        size_bytes=size_bytes,
        label=label,
    )


def delete_reference(reference_id: str) -> bool:
    return _get_repo().delete_reference(reference_id)


def reorder_references(template_id: str, reference_ids: List[str]) -> bool:
    return _get_repo().reorder_references(template_id, reference_ids)


# ── Sessions ──


def list_sessions(created_by: Optional[str] = None) -> List[Dict[str, Any]]:
    return _get_repo().list_sessions(created_by=created_by)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    repo = _get_repo()
    session = repo.get_session(session_id)
    if not session:
        return None
    messages = repo.list_messages(session_id)
    session["messages"] = messages
    return session


def create_session(
    template_id: Optional[str] = None,
    title: Optional[str] = None,
    aspect_ratio: str = "auto",
    image_size: str = "1K",
    created_by: Optional[str] = None,
    created_by_email: Optional[str] = None,
) -> Dict[str, Any]:
    payload = {
        "template_id": template_id,
        "title": title,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
        "created_by": created_by,
        "created_by_email": created_by_email,
    }
    return _get_repo().create_session(payload)


# ── Usage / Quota ──


class QuotaExceededError(Exception):
    """Raised when the monthly image generation quota is exceeded."""
    pass


def get_usage() -> Dict[str, Any]:
    """Get current month's image generation usage and limit."""
    settings = get_settings()
    now_jst = datetime.now(timezone(timedelta(hours=9)))
    year, month = now_jst.year, now_jst.month

    repo = _get_repo()
    used = repo.count_monthly_generations(year, month)
    # 個別APIキー設定時は無制限
    is_unlimited = settings.image_gen_has_dedicated_key or settings.image_gen_monthly_limit <= 0
    limit = settings.image_gen_monthly_limit

    return {
        "used": used,
        "limit": limit,
        "remaining": None if is_unlimited else max(0, limit - used),
        "is_unlimited": is_unlimited,
        "period": f"{year}-{month:02d}",
    }


# ── Conversation History Builder ──


def _build_gemini_history(
    repo: ImageGenRepository,
    session_id: str,
) -> List[types.Content]:
    """
    セッションの過去メッセージから Gemini SDK Content のリストを構築する。

    - assistant メッセージ: metadata.response_parts に保存された
      Thought Signature 付き Parts をそのまま復元
    - user メッセージ: text_content から Content を構築
    """
    messages = repo.list_messages(session_id)
    history: List[types.Content] = []

    for msg in messages:
        role = msg.get("role", "user")
        metadata = msg.get("metadata") or {}

        if role == "assistant":
            # response_parts が保存されている場合（Thought Signature付き）
            response_parts = metadata.get("response_parts")
            if response_parts:
                content = _deserialize_to_content("model", response_parts)
                history.append(content)
            else:
                # 旧形式: response_parts がないレガシーメッセージ
                # Storageから画像をダウンロードしてContentを構築（Thought Signatureなし）
                parts: List[types.Part] = []
                text_content = msg.get("text_content")
                if text_content:
                    parts.append(types.Part.from_text(text=text_content))
                storage_path = msg.get("storage_path")
                if storage_path:
                    try:
                        img = repo.download_image(OUTPUTS_BUCKET, storage_path)
                        mime = "image/png"
                        if storage_path.endswith(".jpeg") or storage_path.endswith(".jpg"):
                            mime = "image/jpeg"
                        parts.append(types.Part.from_bytes(data=img, mime_type=mime))
                    except Exception as e:
                        logger.warning("Failed to download image %s: %s", storage_path, e)
                if parts:
                    history.append(types.Content(role="model", parts=parts))
        else:
            # user message
            text_content = msg.get("text_content")
            if text_content:
                history.append(
                    types.Content(
                        role="user",
                        parts=[types.Part.from_text(text=text_content)],
                    )
                )

    return history


# ── Image Generation ──


def generate_image(
    session_id: str,
    prompt: str,
    aspect_ratio: Optional[str] = None,
    image_size: Optional[str] = None,
) -> Dict[str, Any]:
    """
    セッション内で画像を生成する（Multi-turn会話対応）。

    1. 月間クォータチェック
    2. セッション情報を取得
    3. テンプレートのリファレンス画像を取得
    4. 過去の会話履歴を構築（Thought Signature含む）
    5. Gemini API で画像生成（chat APIでThought Signature管理）
    6. 生成画像をStorageに保存
    7. レスポンスの全Parts（Thought Signature含む）をmetadataに保存
    """
    # Quota check
    usage = get_usage()
    if not usage["is_unlimited"] and usage["remaining"] <= 0:
        raise QuotaExceededError(
            f"月間画像生成上限（{usage['limit']}枚）に達しました。来月まで生成できません。"
        )

    repo = _get_repo()
    session = repo.get_session(session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # Session settings (can be overridden per request)
    effective_ratio = aspect_ratio or session.get("aspect_ratio", "auto")
    effective_size = image_size or session.get("image_size", "1K")

    # Get template and reference images
    reference_images: List[tuple[bytes, str]] = []
    system_prompt: Optional[str] = None
    template_id = session.get("template_id")

    if template_id:
        template = repo.get_template(template_id)
        if template:
            system_prompt = template.get("system_prompt")
            reference_images = repo.get_reference_images(template_id)

    # Build conversation history (with Thought Signatures) from past messages
    gemini_history = _build_gemini_history(repo, session_id)

    # Save user message
    repo.add_message({
        "session_id": session_id,
        "role": "user",
        "text_content": prompt,
    })

    # Generate image with conversation context
    generator = _get_generator()
    result = generator.generate(
        prompt=prompt,
        reference_images=reference_images if reference_images else None,
        aspect_ratio=effective_ratio,
        image_size=effective_size,
        system_prompt=system_prompt,
        history=gemini_history if gemini_history else None,
    )

    # Save generated image to storage
    image_url = None
    storage_path = None
    if result.image_data:
        storage_path = repo.upload_output_image(
            session_id=session_id,
            image_data=result.image_data,
            mime_type=result.mime_type or "image/png",
        )
        image_url = f"/api/v1/image-gen/images/{OUTPUTS_BUCKET}/{storage_path}"

    # Save assistant message with response_parts (includes Thought Signatures)
    assistant_msg = repo.add_message({
        "session_id": session_id,
        "role": "assistant",
        "text_content": result.text,
        "image_url": image_url,
        "storage_path": storage_path,
        "metadata": {
            "usage": result.usage,
            "latency_ms": result.latency_ms,
            "aspect_ratio": effective_ratio,
            "image_size": effective_size,
            "reference_count": len(reference_images),
            "history_length": len(gemini_history),
            # Thought Signature付きの全Parts（base64エンコード済み）
            # 次回のmulti-turn会話でこのまま復元される
            "response_parts": result.response_parts,
        },
    })

    # Update session timestamp
    repo.update_session(session_id, {"updated_at": datetime.now(timezone.utc).isoformat()})

    return assistant_msg


def get_image_url(bucket: str, path: str) -> str:
    """画像の署名付きURLを取得"""
    repo = _get_repo()
    return repo.get_image_signed_url(bucket, path)

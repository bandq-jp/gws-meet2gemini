"""
Gemini 画像生成クライアント

gemini-3.1-flash-image-preview を使用し、リファレンス画像をもとに新しい画像を生成する。
最大14枚のリファレンス画像、人物一貫性最大5人、解像度1K/2K/4K対応。
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-image-preview"

SUPPORTED_ASPECT_RATIOS = [
    "1:1", "2:3", "3:2", "3:4", "4:3",
    "4:5", "5:4", "9:16", "16:9", "21:9",
]

SUPPORTED_IMAGE_SIZES = ["1K", "2K", "4K"]


@dataclass
class ImageGenResult:
    """画像生成結果"""
    text: Optional[str]
    image_data: Optional[bytes]
    mime_type: Optional[str]
    usage: Optional[Dict[str, Any]]
    latency_ms: int


class GeminiImageGenerator:
    """Gemini 3 Pro Image Preview を使った画像生成"""

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        key = api_key or settings.gemini_api_key
        if not key:
            raise ValueError(
                "Gemini API key is required. Set GEMINI_API_KEY or GOOGLE_API_KEY."
            )
        self.client = genai.Client(api_key=key)

    def generate(
        self,
        prompt: str,
        reference_images: Optional[List[tuple[bytes, str]]] = None,
        aspect_ratio: str = "auto",
        image_size: str = "1K",
        system_prompt: Optional[str] = None,
    ) -> ImageGenResult:
        """
        画像を生成する。

        Args:
            prompt: ユーザーのプロンプト
            reference_images: [(image_bytes, mime_type), ...] 最大14枚
            aspect_ratio: アスペクト比 (auto or supported ratios)
            image_size: 解像度 (1K, 2K, 4K)
            system_prompt: テンプレート固有のシステムプロンプト

        Returns:
            ImageGenResult with text and image data
        """
        t0 = perf_counter()

        # Build contents
        contents: List[Any] = []

        if system_prompt:
            contents.append(
                f"[System Context]\n{system_prompt}\n\n[User Request]\n{prompt}"
            )
        else:
            contents.append(prompt)

        # Add reference images (max 14)
        if reference_images:
            for img_bytes, mime in reference_images[:14]:
                contents.append(
                    types.Part.from_bytes(data=img_bytes, mime_type=mime)
                )

        # Build config
        image_config_kwargs: Dict[str, Any] = {}
        if aspect_ratio and aspect_ratio != "auto":
            if aspect_ratio in SUPPORTED_ASPECT_RATIOS:
                image_config_kwargs["aspect_ratio"] = aspect_ratio
        if image_size and image_size in SUPPORTED_IMAGE_SIZES:
            image_config_kwargs["image_size"] = image_size

        config_kwargs: Dict[str, Any] = {
            "response_modalities": ["TEXT", "IMAGE"],
        }
        if image_config_kwargs:
            config_kwargs["image_config"] = types.ImageConfig(**image_config_kwargs)

        logger.info(
            "Generating image: model=%s, refs=%d, ratio=%s, size=%s",
            MODEL,
            len(reference_images) if reference_images else 0,
            aspect_ratio,
            image_size,
        )

        response = self.client.models.generate_content(
            model=MODEL,
            contents=contents,
            config=types.GenerateContentConfig(**config_kwargs),
        )

        latency_ms = int((perf_counter() - t0) * 1000)

        # Extract text and image from response
        result_text = None
        result_image_data = None
        result_mime_type = None

        if response and response.candidates:
            for candidate in response.candidates:
                if not hasattr(candidate, "content") or not candidate.content:
                    continue
                for part in candidate.content.parts:
                    if hasattr(part, "thought") and part.thought:
                        continue
                    if hasattr(part, "text") and part.text:
                        result_text = (result_text or "") + part.text
                    elif hasattr(part, "inline_data") and part.inline_data:
                        result_image_data = part.inline_data.data
                        result_mime_type = part.inline_data.mime_type

        # Extract usage
        usage_dict = None
        usage = getattr(response, "usage_metadata", None)
        if usage:
            usage_dict = {
                "prompt_token_count": getattr(usage, "prompt_token_count", None),
                "candidates_token_count": getattr(usage, "candidates_token_count", None),
                "total_token_count": getattr(usage, "total_token_count", None),
            }

        logger.info(
            "Image generated: latency=%dms, has_image=%s, text_len=%d",
            latency_ms,
            result_image_data is not None,
            len(result_text) if result_text else 0,
        )

        return ImageGenResult(
            text=result_text,
            image_data=result_image_data,
            mime_type=result_mime_type or "image/png",
            usage=usage_dict,
            latency_ms=latency_ms,
        )

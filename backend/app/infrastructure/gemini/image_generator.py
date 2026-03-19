"""
Gemini 画像生成クライアント

gemini-3.1-flash-image-preview を使用し、リファレンス画像をもとに新しい画像を生成する。
Google Search + Image Search グラウンディング対応。
最大14枚のリファレンス画像、解像度1K/2K/4K対応。

Multi-turn対応:
- client.chats.create() でセッションごとの会話を維持
- Thought Signatureをレスポンスから抽出してDBに保存
- 過去メッセージの復元時にThought Signatureを含めて正確にContent再構築
"""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)

MODEL = "gemini-3.1-flash-image-preview"

SUPPORTED_ASPECT_RATIOS = [
    "1:1", "1:4", "1:8", "2:3", "3:2", "3:4", "4:1", "4:3",
    "4:5", "5:4", "8:1", "9:16", "16:9", "21:9",
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
    # レスポンスの全Parts情報（Thought Signature含む）をJSON化して保存用
    response_parts: Optional[List[Dict[str, Any]]] = None


def _serialize_response_parts(
    candidate_content: types.Content,
) -> List[Dict[str, Any]]:
    """
    レスポンスのContent.partsをJSON-serializable dictのリストに変換。
    Thought Signatureをbase64エンコードして保持する。

    NOTE: inline_data（画像バイナリ）は含めない。4K画像のbase64は5-10MBになり、
    JSONB metadataカラムへのINSERTでSupabaseのstatement timeoutを引き起こす。
    画像はSupabase Storageに別途保存済みなので、履歴復元時にダウンロードする。
    ここではthought_signatureとテキスト情報のみ保存する。
    """
    serialized = []
    for part in (candidate_content.parts or []):
        entry: Dict[str, Any] = {}
        if hasattr(part, "thought") and part.thought:
            entry["thought"] = True
        if hasattr(part, "text") and part.text:
            entry["text"] = part.text
        if hasattr(part, "inline_data") and part.inline_data:
            # 画像データ自体は保存しない（巨大すぎる）
            # mime_typeだけ記録し、画像はStorageから復元する
            entry["has_inline_data"] = True
            entry["inline_data_mime_type"] = part.inline_data.mime_type
        if hasattr(part, "thought_signature") and part.thought_signature:
            entry["thought_signature"] = base64.b64encode(
                part.thought_signature
            ).decode("ascii")
        if entry:
            serialized.append(entry)
    return serialized


def _deserialize_to_content(
    role: str,
    serialized_parts: List[Dict[str, Any]],
    image_data: Optional[bytes] = None,
    image_mime_type: Optional[str] = None,
) -> types.Content:
    """
    JSON化されたParts情報からtypes.Contentを復元する。
    Thought Signatureを含めて正確に再構築する。

    image_data/image_mime_type: inline_dataが省略されている場合に
    Storageからダウンロードした画像データを注入するために使用。
    """
    parts: List[types.Part] = []
    for entry in serialized_parts:
        kwargs: Dict[str, Any] = {}
        if entry.get("thought"):
            kwargs["thought"] = True
        if entry.get("text"):
            kwargs["text"] = entry["text"]
        if entry.get("inline_data"):
            # 旧形式: inline_dataがそのまま保存されていた場合
            kwargs["inline_data"] = types.Blob(
                data=base64.b64decode(entry["inline_data"]["data"]),
                mime_type=entry["inline_data"]["mime_type"],
            )
        elif entry.get("has_inline_data") and image_data:
            # 新形式: inline_dataは省略されており、Storageから注入
            kwargs["inline_data"] = types.Blob(
                data=image_data,
                mime_type=image_mime_type or entry.get("inline_data_mime_type", "image/png"),
            )
        if entry.get("thought_signature"):
            kwargs["thought_signature"] = base64.b64decode(
                entry["thought_signature"]
            )
        if kwargs:
            parts.append(types.Part(**kwargs))
    return types.Content(role=role, parts=parts)


class GeminiImageGenerator:
    """Gemini 3.1 Flash Image Preview を使った画像生成（Multi-turn対応）"""

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
        image_size: str = "4K",
        system_prompt: Optional[str] = None,
        history: Optional[List[types.Content]] = None,
    ) -> ImageGenResult:
        """
        画像を生成する（Multi-turn会話対応）。

        Args:
            prompt: ユーザーのプロンプト
            reference_images: [(image_bytes, mime_type), ...] 最大14枚
            aspect_ratio: アスペクト比 (auto or supported ratios)
            image_size: 解像度 (1K, 2K, 4K)
            system_prompt: テンプレート固有のシステムプロンプト
            history: Gemini SDK Content形式の会話履歴（Thought Signature含む）

        Returns:
            ImageGenResult with text, image data, and serialized response parts
        """
        t0 = perf_counter()

        # Build image_config
        image_config_kwargs: Dict[str, Any] = {}
        if aspect_ratio and aspect_ratio != "auto":
            if aspect_ratio in SUPPORTED_ASPECT_RATIOS:
                image_config_kwargs["aspect_ratio"] = aspect_ratio
        if image_size and image_size in SUPPORTED_IMAGE_SIZES:
            image_config_kwargs["image_size"] = image_size

        # Build config
        config_kwargs: Dict[str, Any] = {
            "response_modalities": ["TEXT", "IMAGE"],
        }

        # System instruction (native Gemini parameter)
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        # Google Search + Image Search grounding
        # リファレンス画像がある場合はSearch無効（同時使用非対応）
        use_search = not reference_images
        if use_search:
            config_kwargs["tools"] = [
                types.Tool(
                    google_search=types.GoogleSearch(
                        search_types=types.SearchTypes(
                            web_search=types.WebSearch(),
                            image_search=types.ImageSearch(),
                        )
                    )
                )
            ]

        if image_config_kwargs:
            config_kwargs["image_config"] = types.ImageConfig(**image_config_kwargs)

        logger.info(
            "Generating image: model=%s, refs=%d, ratio=%s, size=%s, search=%s, history=%d",
            MODEL,
            len(reference_images) if reference_images else 0,
            aspect_ratio,
            image_size,
            use_search,
            len(history) if history else 0,
        )

        config = types.GenerateContentConfig(**config_kwargs)

        # Build contents for current turn
        current_parts: List[Any] = [prompt]

        # リファレンス画像は初回ターン（履歴なし）のみ添付。
        # 2回目以降は会話履歴に初回の画像が含まれるので再送不要。
        if reference_images and not history:
            for img_bytes, mime in reference_images[:14]:
                current_parts.append(
                    types.Part.from_bytes(data=img_bytes, mime_type=mime)
                )

        # Use chat API for multi-turn (handles thought signatures in curated_history)
        chat = self.client.chats.create(
            model=MODEL,
            config=config,
            history=history,
        )

        response = chat.send_message(current_parts)

        latency_ms = int((perf_counter() - t0) * 1000)

        # Extract text and image from response
        result_text = None
        result_image_data = None
        result_mime_type = None
        response_parts = None

        if response and response.candidates:
            for candidate in response.candidates:
                if not hasattr(candidate, "content") or not candidate.content:
                    continue
                # Serialize ALL parts (including thought_signature) for DB storage
                response_parts = _serialize_response_parts(candidate.content)
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
            response_parts=response_parts,
        )

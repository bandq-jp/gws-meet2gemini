from __future__ import annotations
import os
from typing import Optional

from app.domain.services.llm_extractor_port import LLMExtractorPort


def _bool_env(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


def get_llm_extractor() -> LLMExtractorPort:
    """Factory returning the configured LLM extractor (OpenAI or Gemini).

    Switch with env var `LLM_PROVIDER` == "openai" | "gemini" (default: gemini).
    """
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    if provider == "openai":
        from app.infrastructure.openai.structured_extractor import (
            OpenAIStructuredExtractor,
        )

        model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        temp_raw: Optional[str] = os.getenv("OPENAI_TEMPERATURE")
        temperature = float(temp_raw) if temp_raw not in (None, "") else None
        max_tokens = int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "4096"))
        reasoning_effort = os.getenv("OPENAI_REASONING_EFFORT") or None
        # Reasoning models generally do not accept temperature. Guard automatically.
        lower_model = model.lower()
        if reasoning_effort or ("thinking" in lower_model or lower_model.startswith("o3") or lower_model.startswith("o4")):
            temperature = None
        return OpenAIStructuredExtractor(
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
            reasoning_effort=reasoning_effort,
        )

    # default to gemini
    from app.presentation.api.v1.settings import (
        get_current_gemini_settings,
    )
    from app.infrastructure.gemini.structured_extractor import (
        StructuredDataExtractor as GeminiExtractor,
    )

    gs = get_current_gemini_settings()
    return GeminiExtractor(
        model=gs.gemini_model,
        temperature=gs.gemini_temperature,
        max_tokens=gs.gemini_max_tokens,
    )

from __future__ import annotations
import json
from typing import Dict, Any, Optional, List

from app.domain.services.llm_extractor_port import LLMExtractorPort
from .client import get_openai_client


class OpenAIStructuredExtractor(LLMExtractorPort):
    def __init__(
        self,
        *,
        model: str,
        temperature: Optional[float],
        max_output_tokens: int,
        reasoning_effort: Optional[str] = None,
    ):
        self.client = get_openai_client()
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.usage_events: List[Dict[str, Any]] = []

    def _common_args(self) -> Dict[str, Any]:
        args: Dict[str, Any] = {
            "model": self.model,
            "max_output_tokens": self.max_output_tokens,
        }
        # Reasoning models: include reasoning.effort when provided
        if self.reasoning_effort:
            args["reasoning"] = {"effort": self.reasoning_effort}
        # Some reasoning models do not support temperature. Only include when not None.
        if self.temperature is not None:
            args["temperature"] = self.temperature
        return args

    def _call_json_schema(
        self,
        *,
        sys_prompt: str,
        user_text: str,
        schema: Dict[str, Any],
    ) -> (Dict[str, Any], Optional[Dict[str, Any]]):
        """Call Responses API with JSON Schema using text.format. Returns (data, usage)."""
        # Primary attempt: use text.format with json_schema
        req_args = {
            **self._common_args(),
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": sys_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "structured_fields",
                        "schema": schema,
                        "strict": True,
                    },
                }
            },
        }
        try:
            resp = self.client.responses.create(**req_args)
        except Exception:
            # Fallback: remove text.format and let model return JSON; we'll parse robustly
            req_args_fallback = {
                **self._common_args(),
                "input": [
                    {"role": "system", "content": [{"type": "input_text", "text": sys_prompt}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
                ],
            }
            resp = self.client.responses.create(**req_args_fallback)
        usage = None
        if getattr(resp, "usage", None) is not None:
            # Convert SDK object to plain dict if possible
            try:
                usage = resp.usage.model_dump()
            except Exception:
                try:
                    usage = json.loads(resp.usage.json())
                except Exception:
                    usage = None

        # Robustly parse output JSON
        # Prefer convenience property when available
        text_payload = None
        try:
            text_payload = resp.output_text
        except Exception:
            text_payload = None
        if not text_payload:
            # Walk content tree as fallback
            try:
                for item in getattr(resp, "output", []) or []:
                    for c in getattr(item, "content", []) or []:
                        if getattr(c, "type", None) in ("output_text", "text") and getattr(c, "text", None):
                            text_payload = c.text
                            break
                    if text_payload:
                        break
            except Exception:
                pass

        if not text_payload:
            raise ValueError("OpenAI structured response missing text content")

        try:
            data = json.loads(text_payload)
        except Exception as e:
            # Try to extract a JSON object/array substring
            import re
            m = re.search(r"\{.*\}|\[.*\]", text_payload, flags=re.S)
            if not m:
                raise ValueError(
                    f"OpenAI structured response could not be parsed as JSON: {e}; snippet={text_payload[:200]}"
                )
            data = json.loads(m.group(0))

        return data, usage

    def extract_all_structured_data(
        self,
        text_content: str,
        *,
        candidate_name: Optional[str],
        agent_name: Optional[str],
        use_parallel: bool = True,
    ) -> Dict[str, Any]:
        # Keep group-wise extraction logic consistent with Gemini implementation
        from app.domain.schemas.structured_extraction_schema import (
            StructuredExtractionSchema,
        )
        groups = StructuredExtractionSchema.get_all_schema_groups()
        merged: Dict[str, Any] = {}

        # reset usage events
        self.usage_events.clear()

        for schema_dict, group_name in groups:
            data = self.extract_structured_data_group(
                text_content, schema_dict, group_name, candidate_name, agent_name
            )
            merged.update(data)
        return merged

    def extract_structured_data_group(
        self,
        text_content: str,
        schema_dict: Dict[str, Any],
        group_name: str,
        candidate_name: Optional[str],
        agent_name: Optional[str],
    ) -> Dict[str, Any]:
        sys = (
            f"You are a precise information extractor. Extract only the fields defined in the JSON Schema for group '{group_name}'. "
            f"Unknown or unspecified fields must be null. Candidate: {candidate_name or 'N/A'} | Agent: {agent_name or 'N/A'}"
        )
        data, usage = self._call_json_schema(
            sys_prompt=sys, user_text=text_content, schema=schema_dict
        )

        # Normalize usage event to existing ai_usage_logs shape
        if usage is not None:
            # Responses API typically returns input_tokens/output_tokens
            prompt_tokens = usage.get("input_tokens") or usage.get("prompt_tokens")
            output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
            total_tokens = None
            if prompt_tokens is not None and output_tokens is not None:
                try:
                    total_tokens = int(prompt_tokens) + int(output_tokens)
                except Exception:
                    total_tokens = None
            self.usage_events.append(
                {
                    "provider": "openai",
                    "group_name": group_name,
                    "model": self.model,
                    "prompt_token_count": prompt_tokens,
                    "candidates_token_count": output_tokens,
                    "cached_content_token_count": None,
                    "total_token_count": total_tokens,
                    "finish_reason": None,
                    "response_chars": None,
                    "latency_ms": usage.get("time_in_ms") if isinstance(usage.get("time_in_ms"), int) else None,
                    "usage_raw": usage,
                }
            )

        return data

from __future__ import annotations
import os
from openai import OpenAI


def get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required for OpenAI provider")
    return OpenAI(api_key=api_key)


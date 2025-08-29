from __future__ import annotations
from typing import Dict, Any, Optional, Protocol, List


class LLMExtractorPort(Protocol):
    """Port for structured data extraction providers.

    Implementations should populate `usage_events` with dicts containing
    at minimum: `group_name`, `model`, and token usage fields when available.
    """

    usage_events: List[Dict[str, Any]]

    def extract_all_structured_data(
        self,
        text_content: str,
        *,
        candidate_name: Optional[str],
        agent_name: Optional[str],
        use_parallel: bool = True,
    ) -> Dict[str, Any]:
        ...

    def extract_structured_data_group(
        self,
        text_content: str,
        schema_dict: Dict[str, Any],
        group_name: str,
        candidate_name: Optional[str],
        agent_name: Optional[str],
    ) -> Dict[str, Any]:
        ...


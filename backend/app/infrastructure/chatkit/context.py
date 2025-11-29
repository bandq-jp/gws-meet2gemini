from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class MarketingRequestContext:
    """Per-request context used by ChatKit store and server."""

    user_id: str
    user_email: str
    user_name: str | None = None
    scope: Dict[str, Any] | None = None
    model_asset_id: str | None = None

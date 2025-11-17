from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class MarketingConversation:
    id: str
    title: Optional[str]
    status: str
    owner_email: Optional[str]
    owner_clerk_id: Optional[str]
    marketing_goal: Optional[str] = None
    description: Optional[str] = None
    target_urls: list[str] = field(default_factory=list)
    target_keywords: list[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    latest_summary: Optional[str] = None
    last_message_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class MarketingMessage:
    id: str
    conversation_id: str
    role: str
    message_type: str
    plain_text: Optional[str]
    content: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

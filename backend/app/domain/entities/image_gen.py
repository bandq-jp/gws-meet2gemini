from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ImageGenTemplate:
    id: Optional[str] = None
    name: str = ""
    description: Optional[str] = None
    category: Optional[str] = None
    aspect_ratio: str = "auto"
    image_size: str = "1K"
    system_prompt: Optional[str] = None
    thumbnail_url: Optional[str] = None
    visibility: str = "public"
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None
    references: List[ImageGenReference] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ImageGenReference:
    id: Optional[str] = None
    template_id: Optional[str] = None
    filename: str = ""
    storage_path: str = ""
    mime_type: Optional[str] = None
    size_bytes: Optional[int] = None
    sort_order: int = 0
    label: str = "style"
    created_at: Optional[datetime] = None


@dataclass
class ImageGenSession:
    id: Optional[str] = None
    template_id: Optional[str] = None
    title: Optional[str] = None
    aspect_ratio: str = "auto"
    image_size: str = "1K"
    created_by: Optional[str] = None
    created_by_email: Optional[str] = None
    messages: List[ImageGenMessage] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class ImageGenMessage:
    id: Optional[str] = None
    session_id: Optional[str] = None
    role: str = "user"
    text_content: Optional[str] = None
    image_url: Optional[str] = None
    storage_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None

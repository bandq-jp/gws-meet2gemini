from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class StructuredData:
    meeting_id: str
    data: Dict[str, Any]

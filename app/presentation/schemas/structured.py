from __future__ import annotations
from pydantic import BaseModel
from typing import Any, Dict

class StructuredOut(BaseModel):
    meeting_id: str
    data: Dict[str, Any]

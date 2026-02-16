from __future__ import annotations
from typing import Any, Dict, Optional

from app.infrastructure.config.settings import get_settings
from app.infrastructure.zoho.client import ZohoClient


class GetJDDetailUseCase:
    def __init__(self):
        self.zoho_client = ZohoClient()
        self.settings = get_settings()

    def execute(self, jd_id: str, version: Optional[str] = None) -> Dict[str, Any]:
        v = version or self.settings.zoho_jd_module_version
        result = self.zoho_client.get_job_description(jd_id, version=v)
        if not result:
            return {"error": "求人票レコードが見つかりません"}
        # Strip internal fields
        result.pop("_raw", None)
        result["module_version"] = result.pop("_module_version", v)
        return result

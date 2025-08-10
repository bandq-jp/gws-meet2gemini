from __future__ import annotations
import time
import json
from typing import Any, Dict, List, Optional
from urllib import request, parse, error

from app.infrastructure.config.settings import get_settings


class ZohoAuthError(RuntimeError):
    pass


class ZohoClient:
    """Minimal read-only Zoho CRM REST client (no writes).

    - Uses refresh token flow to obtain short-lived access tokens.
    - Only performs GET requests to CRM APIs.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0

    def _token_valid(self) -> bool:
        return bool(self._access_token) and (time.time() < self._token_expiry - 30)

    def _fetch_access_token(self) -> str:
        if not (self.settings.zoho_client_id and self.settings.zoho_client_secret and self.settings.zoho_refresh_token):
            raise ZohoAuthError("Zoho credentials are not configured. Set ZOHO_CLIENT_ID/SECRET/REFRESH_TOKEN.")

        token_url = f"{self.settings.zoho_accounts_base_url}/oauth/v2/token"
        data = parse.urlencode(
            {
                "refresh_token": self.settings.zoho_refresh_token,
                "client_id": self.settings.zoho_client_id,
                "client_secret": self.settings.zoho_client_secret,
                "grant_type": "refresh_token",
            }
        ).encode("utf-8")
        req = request.Request(token_url, data=data, method="POST")
        try:
            with request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as e:
            raise ZohoAuthError(f"Failed to refresh token: {e.read().decode('utf-8', 'ignore')}") from e

        access = payload.get("access_token")
        if not access:
            raise ZohoAuthError(f"Invalid token response: {payload}")
        self._access_token = access
        # Zoho returns expires_in (seconds)
        self._token_expiry = time.time() + int(payload.get("expires_in", 3600))
        return access

    def _get_access_token(self) -> str:
        if self._token_valid():
            return self._access_token  # type: ignore[return-value]
        return self._fetch_access_token()

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        base = self.settings.zoho_api_base_url.rstrip("/")
        url = f"{base}{path}"
        if params:
            url += ("?" + parse.urlencode(params))
        headers = {"Authorization": f"Zoho-oauthtoken {self._get_access_token()}"}
        req = request.Request(url, headers=headers, method="GET")
        try:
            with request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8")
                return json.loads(text) if text else {}
        except error.HTTPError as e:
            # 204 No Content → treat as empty
            if e.code == 204:
                return {}
            body = e.read().decode("utf-8", "ignore")
            raise RuntimeError(f"Zoho GET {path} failed: {e.code} {body}") from e

    # --- Metadata helpers ---
    def get_field_api_name(self, module_api_name: str, display_label: str) -> Optional[str]:
        """Resolve field API name by display label for a module (best-effort)."""
        data = self._get("/crm/v2/settings/fields", {"module": module_api_name}) or {}
        for f in data.get("fields", []) or []:
            # Match on display_label (user-facing) or field_label
            if (f.get("display_label") == display_label) or (f.get("field_label") == display_label):
                return f.get("api_name")
        return None

    def list_modules(self) -> List[Dict[str, Any]]:
        """List CRM modules (api_name and singular_label/label)."""
        data = self._get("/crm/v2/settings/modules") or {}
        items = []
        for m in data.get("modules", []) or []:
            items.append(
                {
                    "api_name": m.get("api_name"),
                    "singular_label": m.get("singular_label"),
                    "label": m.get("module_name") or m.get("label"),
                    "generated_type": m.get("generated_type"),
                    "deletable": m.get("deletable"),
                    "creatable": m.get("creatable"),
                }
            )
        return items

    def list_fields(self, module_api_name: str) -> List[Dict[str, Any]]:
        """List fields for a module (api_name and display_label)."""
        data = self._get("/crm/v2/settings/fields", {"module": module_api_name}) or {}
        out: List[Dict[str, Any]] = []
        for f in data.get("fields", []) or []:
            out.append(
                {
                    "api_name": f.get("api_name"),
                    "display_label": f.get("display_label") or f.get("field_label"),
                    "data_type": f.get("data_type"),
                    "system_mandatory": f.get("system_mandatory"),
                }
            )
        return out

    # --- APP-hc (CustomModule1) helpers ---
    def search_app_hc_by_name(self, name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search APP-hc by candidate name (partial). Read-only.

        Strategy: try contains → starts_with → equals to accommodate module-specific operator constraints.
        Returns records with minimal fields: id (Zoho record id), candidate name, candidate id (custom field).
        """
        module_api = self.settings.zoho_app_hc_module

        # Resolve field API names if not provided
        name_field = self.settings.zoho_app_hc_name_field_api or self.get_field_api_name(module_api, "求職者名")
        id_field = self.settings.zoho_app_hc_id_field_api or self.get_field_api_name(module_api, "求職者ID")
        if not name_field:
            raise RuntimeError(
                "APP-hc name field API not resolvable. Set ZOHO_APP_HC_MODULE/ZOHO_APP_HC_NAME_FIELD_API explicitly or use /api/v1/zoho/modules and /api/v1/zoho/fields to discover."
            )

        # Helper to call search with a specific operator and minimal fields
        def _search_with(op: str) -> Dict[str, Any]:
            crit = f"({name_field}:{op}:{name})"
            params: Dict[str, Any] = {"criteria": crit, "per_page": limit}
            fields = ["id", name_field]
            if id_field:
                fields.append(id_field)
            params["fields"] = ",".join(fields)
            return self._get(f"/crm/v2/{module_api}/search", params) or {}

        data: Dict[str, Any] = {}
        last_err: Optional[Exception] = None
        for op in ("contains", "starts_with", "equals"):
            try:
                data = _search_with(op)
                break
            except Exception as e:
                # Keep last error and try next operator
                last_err = e
                continue
        if not data and last_err:
            raise last_err
        records = []
        for r in data.get("data", []) or []:
            records.append(
                {
                    "record_id": r.get("id"),
                    "candidate_name": r.get(name_field),
                    "candidate_id": (r.get(id_field) if id_field else None),
                    "raw": r,
                }
            )
        return records

    def get_app_hc_record(self, record_id: str) -> Dict[str, Any]:
        """Fetch single APP-hc record by Zoho record id with all fields (read-only)."""
        module_api = self.settings.zoho_app_hc_module
        data = self._get(f"/crm/v2/{module_api}/{record_id}") or {}
        items = data.get("data") or []
        return items[0] if items else {}

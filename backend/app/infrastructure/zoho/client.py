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
            # 検索に失敗した場合（例：サポート外の演算子）、例外を発生させる代わりに空の結果を返す。
            # これにより、APIクライアント側では「候補者が見つからなかった」として処理される。
            pass
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
    
    def check_record_layout(self, record_id: str) -> Dict[str, Any]:
        """レコードのレイアウトをチェックし、「自動入力・マッチング用」かどうかを判定する
        
        Args:
            record_id: ZohoレコードID
            
        Returns:
            Dict containing layout info and validation result
        """
        try:
            record = self.get_app_hc_record(record_id)
            if not record:
                return {
                    "status": "error",
                    "message": "レコードが見つかりません",
                    "is_valid_layout": False
                }
            
            layout_info = record.get("Layout", {})
            layout_name = layout_info.get("name", "")
            layout_display_label = layout_info.get("display_label", "")
            layout_id = layout_info.get("id", "")
            
            # 「自動入力・マッチング用」レイアウトかチェック
            is_auto_input_layout = (
                layout_name == "自動入力・マッチング用" or 
                layout_display_label == "自動入力・マッチング用"
            )
            
            return {
                "status": "success",
                "layout_id": layout_id,
                "layout_name": layout_name,
                "layout_display_label": layout_display_label,
                "is_valid_layout": is_auto_input_layout,
                "message": (
                    "適切なレイアウトです" if is_auto_input_layout 
                    else f"このレコードは'{layout_display_label}'レイアウトです。構造化出力を行うには「自動入力・マッチング用」レイアウトに変更してください。"
                )
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": f"レイアウトチェックでエラーが発生しました: {str(e)}",
                "is_valid_layout": False
            }
    

# class ZohoBaseClient:
#     def __init__(self) -> None:
#         self.settings = get_settings()
#         self._access_token: Optional[str] = None
#         self._token_expiry: float = 0.0

#     def _token_valid(self) -> bool:
#         # 有効なアクセストークンがあり、期限切れでない場合 True
#         return bool(self._access_token) and (time.time() < self._token_expiry - 30)

#     def _fetch_access_token(self) -> str:
#         # 必要な認証情報が設定されているか確認
#         if not (self.settings.zoho_client_id and self.settings.zoho_client_secret and self.settings.zoho_refresh_token):
#             raise Exception("Zoho credentials not configured")

#         token_url = f"{self.settings.zoho_accounts_base_url}/oauth/v2/token"
#         data = parse.urlencode({
#             "refresh_token": self.settings.zoho_refresh_token,
#             "client_id": self.settings.zoho_client_id,
#             "client_secret": self.settings.zoho_client_secret,
#             "grant_type": "refresh_token",
#         }).encode("utf-8")

#         req = request.Request(token_url, data=data, method="POST")
#         with request.urlopen(req, timeout=30) as resp:
#             payload = json.loads(resp.read().decode("utf-8"))

#         access = payload.get("access_token")
#         if not access:
#             raise Exception(f"Invalid token response: {payload}")

#         self._access_token = access
#         self._token_expiry = time.time() + int(payload.get("expires_in", 3600))
#         return access

#     def _get_access_token(self) -> str:
#         if self._token_valid():
#             return self._access_token
#         return self._fetch_access_token()

#     def _make_headers(self) -> Dict[str, str]:
#         return {
#             "Authorization": f"Zoho-oauthtoken {self._get_access_token()}",
#             "Content-Type": "application/json"
#         }



# class ZohoClient(ZohoBaseClient):
    # def list_modules(self) -> List[Dict[str, Any]]:
    #     """List CRM modules (api_name and singular_label/label)."""
    #     data = self._get("/crm/v2/settings/modules") or {}
    #     items = []
    #     for m in data.get("modules", []) or []:
    #         items.append(
    #             {
    #                 "api_name": m.get("api_name"),
    #                 "singular_label": m.get("singular_label"),
    #                 "label": m.get("module_name") or m.get("label"),
    #                 "generated_type": m.get("generated_type"),
    #                 "deletable": m.get("deletable"),
    #                 "creatable": m.get("creatable"),
    #             }
    #         )
    #     return items

    # def list_fields(self, module_api_name: str) -> List[Dict[str, Any]]:
    #     """List fields for a module (api_name and display_label)."""
    #     data = self._get("/crm/v2/settings/fields", {"module": module_api_name}) or {}
    #     out: List[Dict[str, Any]] = []
    #     for f in data.get("fields", []) or []:
    #         out.append(
    #             {
    #                 "api_name": f.get("api_name"),
    #                 "display_label": f.get("display_label") or f.get("field_label"),
    #                 "data_type": f.get("data_type"),
    #                 "system_mandatory": f.get("system_mandatory"),
    #             }
    #         )
    #     return out

    # # --- APP-hc (CustomModule1) helpers ---
    # def search_app_hc_by_name(self, name: str, limit: int = 5) -> List[Dict[str, Any]]:
    #     """Search APP-hc by candidate name (partial). Read-only.

    #     Strategy: try contains → starts_with → equals to accommodate module-specific operator constraints.
    #     Returns records with minimal fields: id (Zoho record id), candidate name, candidate id (custom field).
    #     """
    #     module_api = self.settings.zoho_app_hc_module

    #     # Resolve field API names if not provided
    #     name_field = self.settings.zoho_app_hc_name_field_api or self.get_field_api_name(module_api, "求職者名")
    #     id_field = self.settings.zoho_app_hc_id_field_api or self.get_field_api_name(module_api, "求職者ID")
    #     if not name_field:
    #         raise RuntimeError(
    #             "APP-hc name field API not resolvable. Set ZOHO_APP_HC_MODULE/ZOHO_APP_HC_NAME_FIELD_API explicitly or use /api/v1/zoho/modules and /api/v1/zoho/fields to discover."
    #         )

    #     # Helper to call search with a specific operator and minimal fields
    #     def _search_with(op: str) -> Dict[str, Any]:
    #         crit = f"({name_field}:{op}:{name})"
    #         params: Dict[str, Any] = {"criteria": crit, "per_page": limit}
    #         fields = ["id", name_field]
    #         if id_field:
    #             fields.append(id_field)
    #         params["fields"] = ",".join(fields)
    #         return self._get(f"/crm/v2/{module_api}/search", params) or {}

    #     data: Dict[str, Any] = {}
    #     last_err: Optional[Exception] = None
    #     for op in ("contains", "starts_with", "equals"):
    #         try:
    #             data = _search_with(op)
    #             break
    #         except Exception as e:
    #             # Keep last error and try next operator
    #             last_err = e
    #             continue
    #     if not data and last_err:
    #         raise last_err
    #     records = []
    #     for r in data.get("data", []) or []:
    #         records.append(
    #             {
    #                 "record_id": r.get("id"),
    #                 "candidate_name": r.get(name_field),
    #                 "candidate_id": (r.get(id_field) if id_field else None),
    #                 "raw": r,
    #             }
    #         )
    #     return records

    # def get_app_hc_record(self, record_id: str) -> Dict[str, Any]:
    #     """Fetch single APP-hc record by Zoho record id with all fields (read-only)."""
    #     module_api = self.settings.zoho_app_hc_module
    #     data = self._get(f"/crm/v2/{module_api}/{record_id}") or {}
    #     items = data.get("data") or []
    #     return items[0] if items else {}


class ZohoWriteClient:
    """Zoho CRM書き込み専用クライアント（構造化出力からZohoレコード更新用）"""
    
    def __init__(self) -> None:
        self.settings = get_settings()
        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        
        # 構造化出力フィールド → Zohoフィールドのマッピング
        self.field_mapping = {
            # グループ1: 転職活動状況・エージェント関連
            "transfer_activity_status": "transfer_activity_status",
            "agent_count": "agent_count", 
            "current_agents": "current_agents",
            "introduced_jobs": "introduced_jobs",
            "job_appeal_points": "job_appeal_points",
            "job_concerns": "job_concerns",
            "companies_in_selection": "companies_in_selection",
            "other_offer_salary": "other_offer_salary",
            "other_company_intention": "other_company_intention",
            
            # グループ2: 転職理由・希望時期・メモ・転職軸
            "transfer_reasons": "transfer_reasons",
            "transfer_trigger": "transfer_trigger",
            "desired_timing": "desired_timing",
            "timing_details": "timing_details",
            "current_job_status": "current_job_status",
            "transfer_status_memo": "transfer_status_memo",
            "transfer_axis_primary": "field45",  # 転職軸（重要ポイント）
            "transfer_priorities": "transfer_priorities",
            
            # グループ3: 職歴・経験
            "career_history": "career_history",
            "current_duties": "field131",  # 現職での担当業務
            "company_good_points": "company_good_points", 
            "company_bad_points": "company_bad_points",
            "enjoyed_work": "enjoyed_work",
            "difficult_work": "difficult_work",
            
            # グループ4: 業界・職種
            "experience_industry": "experience_industry",
            "experience_field_hr": "experience_field_hr",
            "desired_industry": "desired_industry",
            "industry_reason": "industry_reason",
            "desired_position": "desired_position",
            "position_industry_reason": "position_industry_reason",
            
            # グループ5: 年収・待遇・働き方
            "current_salary": "current_salary",
            "salary_breakdown": "field48",  # 現年収内訳
            "desired_first_year_salary": "desired_first_year_salary",
            "base_incentive_ratio": "base_incentive_ratio",
            "max_future_salary": "max_future_salary",
            "salary_memo": "salary_memo",
            "remote_time_memo": "remote_time_memo",
            "ca_ra_focus": "ca_ra_focus",
            "customer_acquisition": "customer_acquisition",
            "new_existing_ratio": "new_existing_ratio",
            
            # グループ6: 会社カルチャー・規模・キャリア
            "business_vision": "business_vision",
            "desired_employee_count": "desired_employee_count",
            "culture_scale_memo": "culture_scale_memo",
            "career_vision": "career_vision",
        }
    
    def _token_valid(self) -> bool:
        return bool(self._access_token) and (time.time() < self._token_expiry - 30)
    
    def _fetch_access_token(self) -> str:
        if not (self.settings.zoho_client_id and self.settings.zoho_client_secret and self.settings.zoho_refresh_token):
            raise ZohoAuthError("Zoho credentials are not configured. Set ZOHO_CLIENT_ID/SECRET/REFRESH_TOKEN.")
        
        token_url = f"{self.settings.zoho_accounts_base_url}/oauth/v2/token"
        data = parse.urlencode({
            "refresh_token": self.settings.zoho_refresh_token,
            "client_id": self.settings.zoho_client_id,
            "client_secret": self.settings.zoho_client_secret,
            "grant_type": "refresh_token",
        }).encode("utf-8")
        
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
        self._token_expiry = time.time() + int(payload.get("expires_in", 3600))
        return access
    
    def _get_access_token(self) -> str:
        if self._token_valid():
            return self._access_token  # type: ignore[return-value]
        return self._fetch_access_token()
    
    def _convert_structured_data_to_zoho(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """構造化出力データをZohoフィールド形式に変換"""
        zoho_data = {}
        
        for structured_field, value in structured_data.items():
            if value is None:
                continue  # null値はスキップ
                
            zoho_field = self.field_mapping.get(structured_field)
            if not zoho_field:
                continue  # マッピングが見つからない場合はスキップ
            
            # データ型変換
            if isinstance(value, list):
                if len(value) == 0:
                    continue  # 空配列はスキップ
                # multiselectpicklistフィールドは配列のまま送信、その他は改行区切りテキストに変換
                multiselect_fields = [
                    "transfer_reasons", "desired_industry", "desired_position", 
                    "business_vision", "career_vision", "desired_employee_count",
                    "experience_industry", "experience_field_hr"  # 追加
                ]
                if structured_field in multiselect_fields:
                    zoho_data[zoho_field] = value  # 配列のまま送信
                else:
                    # その他の配列は改行区切りテキストに変換
                    zoho_data[zoho_field] = "\n".join(str(v) for v in value if v)
            elif isinstance(value, (int, float)):
                zoho_data[zoho_field] = value
            elif isinstance(value, str) and value.strip():
                zoho_data[zoho_field] = value.strip()
        
        return zoho_data
    
    def update_jobseeker_record(self, record_id: str, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """jobSeekerレコードを構造化データで更新"""
        module_api = self.settings.zoho_app_hc_module
        
        # 構造化データをZoho形式に変換
        zoho_data = self._convert_structured_data_to_zoho(structured_data)
        
        if not zoho_data:
            return {"status": "no_data", "message": "No valid data to update"}
        
        # Zoho CRM API呼び出し
        base_url = self.settings.zoho_api_base_url.rstrip("/")
        url = f"{base_url}/crm/v2/{module_api}/{record_id}"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {self._get_access_token()}",
            "Content-Type": "application/json"
        }
        
        payload = json.dumps({"data": [zoho_data]}).encode("utf-8")
        req = request.Request(url, data=payload, headers=headers, method="PUT")
        
        try:
            with request.urlopen(req, timeout=30) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "success", 
                    "status_code": resp.getcode(),
                    "data": response_data,
                    "updated_fields": list(zoho_data.keys())
                }
        except error.HTTPError as e:
            error_body = e.read().decode("utf-8", "ignore")
            return {
                "status": "error",
                "status_code": e.code,
                "error": error_body,
                "attempted_data": zoho_data
            }

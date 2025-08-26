from __future__ import annotations
import time
import json
from typing import Any, Dict, List, Optional
from urllib import request, parse, error

from app.infrastructure.config.settings import get_settings


class ZohoAuthError(RuntimeError):
    pass


class ZohoFieldMappingError(RuntimeError):
    """Zoho フィールドマッピング関連のエラー"""
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
        """構造化出力データをZohoフィールド形式に変換（再実行・上書き対応）"""
        zoho_data = {}
        
        for structured_field, value in structured_data.items():
            zoho_field = self.field_mapping.get(structured_field)
            if not zoho_field:
                continue  # マッピングが見つからない場合はスキップ
            
            # 空値やNoneの場合も明示的にクリアするため送信対象にする
            if value is None or value == "" or (isinstance(value, list) and len(value) == 0):
                # 空値は空文字列として送信（Zohoで既存値をクリア）
                zoho_data[zoho_field] = ""
                continue
            
            # multiselectpicklistフィールドの定義
            multiselect_fields = [
                "transfer_reasons", "desired_industry", "desired_position", 
                "business_vision", "career_vision", "desired_employee_count",
                "experience_industry", "experience_field_hr"
            ]
            
            # データ型変換
            if structured_field in multiselect_fields:
                # multiselectpicklistフィールドは常に配列として処理
                if isinstance(value, list):
                    # 既に配列の場合：構造化出力をそのまま送信（「特になし」なども保持）
                    clean_values = [str(v).strip() for v in value if str(v).strip()]
                    zoho_data[zoho_field] = clean_values
                elif isinstance(value, str):
                    # 文字列の場合：改行区切りで分割して配列に変換（「特になし」などもそのまま保持）
                    clean_value = value.strip()
                    if clean_value:
                        # 改行区切りで分割して配列にする
                        values = [v.strip() for v in clean_value.split('\n') if v.strip()]
                        zoho_data[zoho_field] = values if values else [clean_value]
                    else:
                        zoho_data[zoho_field] = []
                else:
                    # その他の型は空配列
                    zoho_data[zoho_field] = []
            elif isinstance(value, list):
                # multiselect以外の配列は改行区切りテキストに変換
                clean_values = [str(v).strip() for v in value if v and str(v).strip()]
                zoho_data[zoho_field] = "\n".join(clean_values) if clean_values else ""
            elif isinstance(value, (int, float)):
                zoho_data[zoho_field] = value
            elif isinstance(value, str):
                # 文字列の場合はそのまま送信
                zoho_data[zoho_field] = value.strip()
            else:
                # その他の型は文字列に変換
                zoho_data[zoho_field] = str(value).strip()
        
        return zoho_data
    
    def update_jobseeker_record(self, record_id: str, structured_data: Dict[str, Any], skip_validation: bool = False, candidate_name: str = None) -> Dict[str, Any]:
        """jobSeekerレコードを構造化データで更新
        
        Args:
            record_id: 更新対象レコードID
            structured_data: 構造化データ
            skip_validation: バリデーションスキップフラグ（デフォルト: False）
            candidate_name: 求職者名（ログ用）
        """
        module_api = self.settings.zoho_app_hc_module
        
        # デバッグログを追加
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"📝 Zoho書き込み開始: 求職者「{candidate_name or '不明'}」(record_id={record_id}), skip_validation={skip_validation}")
        
        # バリデーション実行（skip_validation=True でない場合）
        if not skip_validation:
            try:
                validator = ZohoFieldValidator()
                validation_result = validator.pre_write_validation(record_id, structured_data)
                
                if not validation_result["can_proceed_with_write"]:
                    # 検証失敗時の詳細メッセージ
                    error_details = []
                    if not validation_result["layout_validation"]["field_mapping_valid"]:
                        missing_count = validation_result["layout_validation"]["missing_field_definitions"]
                        error_details.append(f"フィールド定義不足: {len(missing_count)}個")
                    if validation_result["blocked_fields_count"] > 0:
                        error_details.append(f"書き込み不可フィールド: {validation_result['blocked_fields_count']}個")
                    
                    error_message = f"Zohoフィールドマッピング検証に失敗しました: {', '.join(error_details)}"
                    logger.error(f"{error_message} - record_id={record_id}")
                    
                    # 検証失敗時は例外を発生させてZoho書き込みを中止
                    raise ZohoFieldMappingError(error_message)
                
                logger.info(f"✅ Zohoフィールドマッピング検証成功: 求職者「{candidate_name or '不明'}」(record_id={record_id}), 書き込み可能フィールド={validation_result['writable_fields_count']}個")
                
            except ZohoFieldMappingError:
                # 検証エラーはそのまま再発生
                raise
            except Exception as e:
                # その他の検証エラーも書き込み中止の対象
                logger.error(f"Zoho書き込み前検証で予期しないエラー: record_id={record_id}, error={str(e)}")
                raise ZohoFieldMappingError(f"書き込み前検証でエラーが発生しました: {str(e)}")
        
        # 構造化データをZoho形式に変換
        zoho_data = self._convert_structured_data_to_zoho(structured_data)
        
        if not zoho_data:
            return {"status": "no_data", "message": "No mappable data to update"}
        
        # Zoho CRM API呼び出し
        base_url = self.settings.zoho_api_base_url.rstrip("/")
        url = f"{base_url}/crm/v2/{module_api}/{record_id}"
        
        headers = {
            "Authorization": f"Zoho-oauthtoken {self._get_access_token()}",
            "Content-Type": "application/json"
        }
        
        payload = json.dumps({"data": [zoho_data]}).encode("utf-8")
        req = request.Request(url, data=payload, headers=headers, method="PUT")
        
        # 詳細ログを追加
        logger.info(f"🚀 Zoho API呼び出し: 求職者「{candidate_name or '不明'}」(record_id={record_id})")
        logger.info(f"📄 送信フィールド({len(zoho_data)}個): {list(zoho_data.keys())}")
        logger.info(f"📋 送信データ詳細: {zoho_data}")
        logger.debug(f"🌐 API URL: {url}")
        
        try:
            with request.urlopen(req, timeout=30) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                
                # 成功時のログを詳細化
                logger.info(f"🎉 Zoho書き込み成功: 求職者「{candidate_name or '不明'}」(record_id={record_id})")
                logger.info(f"📈 HTTP応答: {resp.getcode()}, 更新フィールド数: {len(zoho_data)}")
                
                # Zohoレスポンスから更新されたレコード情報を取得
                if response_data and 'data' in response_data and response_data['data']:
                    updated_record = response_data['data'][0] if response_data['data'] else {}
                    if 'id' in updated_record:
                        logger.info(f"💾 Zoho更新確認: レコードID={updated_record['id']}")
                        # 更新成功・失敗の詳細を確認
                        if 'status' in updated_record:
                            status = updated_record['status']
                            logger.info(f"📋 Zoho更新ステータス: {status}")
                            if 'details' in updated_record:
                                details = updated_record['details']
                                logger.info(f"📄 Zoho更新詳細: {details}")
                else:
                    logger.warning(f"⚠️ Zoho応答にデータが含まれていません: {response_data}")
                
                logger.info(f"📜 Zoho応答詳細: {response_data}")
                return {
                    "status": "success", 
                    "status_code": resp.getcode(),
                    "data": response_data,
                    "updated_fields": list(zoho_data.keys())
                }
        except error.HTTPError as e:
            error_body = e.read().decode("utf-8", "ignore")
            logger.error(f"❌ Zoho書き込み失敗（HTTP）: 求職者「{candidate_name or '不明'}」(record_id={record_id})")
            logger.error(f"💥 HTTPエラー詳細: status_code={e.code}, body={error_body}")
            
            # エラー内容をより詳しく取得
            error_msg = f"HTTP {e.code}: {error_body}"
            try:
                error_json = json.loads(error_body)
                # Zoho APIのエラーメッセージを抽出
                if "data" in error_json and error_json["data"]:
                    zoho_errors = []
                    for item in error_json["data"]:
                        if "message" in item:
                            zoho_errors.append(item["message"])
                        if "details" in item:
                            zoho_errors.append(str(item["details"]))
                    if zoho_errors:
                        error_msg = "; ".join(zoho_errors)
                elif "message" in error_json:
                    error_msg = error_json["message"]
            except (json.JSONDecodeError, KeyError):
                pass  # JSONパースに失敗した場合は元のerror_msgを使用
            
            return {
                "status": "error",
                "status_code": e.code,
                "error": error_msg,
                "raw_error": error_body,
                "attempted_data": zoho_data
            }
        except Exception as e:
            logger.error(f"💀 Zoho書き込み予期しないエラー: 求職者「{candidate_name or '不明'}」(record_id={record_id})")
            logger.error(f"🚨 エラー詳細: {type(e).__name__}: {str(e)}")
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "attempted_data": zoho_data
            }


class ZohoFieldValidator(ZohoClient):
    """Zoho フィールドマッピングとレイアウト検証クラス"""
    
    def __init__(self) -> None:
        super().__init__()
        # ZohoWriteClient と同じマッピングを参照
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
        
        # フィールド情報キャッシュ
        self._field_cache: Optional[Dict[str, Any]] = None
        
    def validate_field_mapping(self, module_api_name: str = None) -> Dict[str, Any]:
        """フィールドマッピングの妥当性を検証
        
        Args:
            module_api_name: 検証対象モジュール（デフォルト: jobSeeker）
            
        Returns:
            検証結果辞書
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not module_api_name:
            module_api_name = self.settings.zoho_app_hc_module or "jobSeeker"
        
        logger.info(f"Zohoフィールドマッピング検証開始: module={module_api_name}")
        
        try:
            # Zohoフィールド一覧を取得
            zoho_fields = self.list_fields(module_api_name)
            zoho_field_apis = {field['api_name'] for field in zoho_fields}
            
            # マッピング対象フィールドの検証
            missing_fields = []
            valid_fields = []
            
            for structured_field, zoho_field_api in self.field_mapping.items():
                if zoho_field_api in zoho_field_apis:
                    valid_fields.append({
                        "structured_field": structured_field,
                        "zoho_field_api": zoho_field_api,
                        "status": "exists"
                    })
                else:
                    missing_fields.append({
                        "structured_field": structured_field,
                        "zoho_field_api": zoho_field_api,
                        "status": "missing"
                    })
            
            validation_result = {
                "module_api_name": module_api_name,
                "total_mapped_fields": len(self.field_mapping),
                "valid_fields_count": len(valid_fields),
                "missing_fields_count": len(missing_fields),
                "valid_fields": valid_fields,
                "missing_fields": missing_fields,
                "is_valid": len(missing_fields) == 0,
                "zoho_total_fields": len(zoho_fields)
            }
            
            if missing_fields:
                logger.warning(f"Zohoフィールドマッピング検証で不足フィールド検出: {len(missing_fields)}個")
                logger.debug(f"不足フィールド詳細: {missing_fields}")
            else:
                logger.info(f"Zohoフィールドマッピング検証成功: {len(valid_fields)}個すべて存在")
                
            return validation_result
            
        except Exception as e:
            logger.error(f"Zohoフィールドマッピング検証エラー: {str(e)}")
            raise ZohoFieldMappingError(f"フィールドマッピング検証に失敗しました: {str(e)}")
    
    def validate_record_layout(self, record_id: str, module_api_name: str = None) -> Dict[str, Any]:
        """特定レコードのレイアウト検証
        
        Args:
            record_id: 検証対象レコードID
            module_api_name: 検証対象モジュール（デフォルト: jobSeeker）
            
        Returns:
            レイアウト検証結果辞書
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not module_api_name:
            module_api_name = self.settings.zoho_app_hc_module or "jobSeeker"
            
        logger.info(f"Zohoレコードレイアウト検証開始: record_id={record_id}, module={module_api_name}")
        
        try:
            # レコード詳細を取得
            record_data = self.get_app_hc_record(record_id)
            
            if not record_data:
                raise ZohoFieldMappingError(f"レコードが見つかりません: {record_id}")
            
            # フィールドマッピング検証
            field_validation = self.validate_field_mapping(module_api_name)
            
            # レコード内のフィールド存在確認
            available_fields = []
            unavailable_fields = []
            
            for mapping in field_validation["valid_fields"]:
                zoho_field_api = mapping["zoho_field_api"]
                if zoho_field_api in record_data:
                    available_fields.append({
                        "structured_field": mapping["structured_field"],
                        "zoho_field_api": zoho_field_api,
                        "current_value": record_data.get(zoho_field_api),
                        "status": "available"
                    })
                else:
                    unavailable_fields.append({
                        "structured_field": mapping["structured_field"],
                        "zoho_field_api": zoho_field_api,
                        "status": "not_in_record"
                    })
            
            layout_result = {
                "record_id": record_id,
                "module_api_name": module_api_name,
                "field_mapping_valid": field_validation["is_valid"],
                "available_fields_count": len(available_fields),
                "unavailable_fields_count": len(unavailable_fields),
                "available_fields": available_fields,
                "unavailable_fields": unavailable_fields,
                "missing_field_definitions": field_validation["missing_fields"],
                "record_has_required_layout": len(unavailable_fields) == 0 and field_validation["is_valid"],
                "record_field_count": len(record_data),
            }
            
            if not layout_result["record_has_required_layout"]:
                issues = []
                if not field_validation["is_valid"]:
                    issues.append(f"{field_validation['missing_fields_count']}個のフィールド定義が不足")
                if unavailable_fields:
                    issues.append(f"{len(unavailable_fields)}個のフィールドがレコードに存在しない")
                logger.warning(f"レコードレイアウト検証で問題検出: {', '.join(issues)}")
            else:
                logger.info(f"Zohoレコードレイアウト検証成功: record_id={record_id}")
                
            return layout_result
            
        except Exception as e:
            logger.error(f"Zohoレコードレイアウト検証エラー: record_id={record_id}, error={str(e)}")
            raise ZohoFieldMappingError(f"レコードレイアウト検証に失敗しました: {str(e)}")
    
    def pre_write_validation(self, record_id: str, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """書き込み前の総合検証
        
        Args:
            record_id: 対象レコードID
            structured_data: 書き込み予定の構造化データ
            
        Returns:
            総合検証結果辞書
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Zoho書き込み前検証開始: record_id={record_id}, data_fields={len(structured_data)}")
        
        try:
            # レコードレイアウト検証
            layout_result = self.validate_record_layout(record_id)
            
            # 実際の書き込み対象フィールドを分析
            writable_fields = []
            blocked_fields = []
            
            for structured_field, value in structured_data.items():
                zoho_field_api = self.field_mapping.get(structured_field)
                if not zoho_field_api:
                    # マッピング定義なし（スキップされる）
                    continue
                    
                # レイアウト検証結果から該当フィールドを確認
                field_available = False
                for available_field in layout_result["available_fields"]:
                    if available_field["structured_field"] == structured_field:
                        writable_fields.append({
                            "structured_field": structured_field,
                            "zoho_field_api": zoho_field_api,
                            "new_value": value,
                            "current_value": available_field["current_value"],
                            "status": "writable"
                        })
                        field_available = True
                        break
                
                if not field_available:
                    blocked_fields.append({
                        "structured_field": structured_field,
                        "zoho_field_api": zoho_field_api,
                        "new_value": value,
                        "status": "blocked",
                        "reason": "field_not_available_in_record"
                    })
            
            pre_write_result = {
                "record_id": record_id,
                "layout_validation": layout_result,
                "input_data_fields": len(structured_data),
                "writable_fields_count": len(writable_fields),
                "blocked_fields_count": len(blocked_fields),
                "writable_fields": writable_fields,
                "blocked_fields": blocked_fields,
                "can_proceed_with_write": layout_result["record_has_required_layout"] and len(blocked_fields) == 0,
                "validation_passed": layout_result["record_has_required_layout"]
            }
            
            if not pre_write_result["can_proceed_with_write"]:
                issues = []
                if not layout_result["record_has_required_layout"]:
                    issues.append("レコードレイアウトに問題がある")
                if blocked_fields:
                    issues.append(f"{len(blocked_fields)}個のフィールドが書き込み不可")
                logger.warning(f"Zoho書き込み前検証で問題検出: {', '.join(issues)}")
            else:
                logger.info(f"Zoho書き込み前検証成功: {len(writable_fields)}個のフィールドが書き込み可能")
                
            return pre_write_result
            
        except Exception as e:
            logger.error(f"Zoho書き込み前検証エラー: record_id={record_id}, error={str(e)}")
            raise ZohoFieldMappingError(f"書き込み前検証に失敗しました: {str(e)}")

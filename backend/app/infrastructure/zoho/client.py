from __future__ import annotations
import time
import json
import threading
from typing import Any, Dict, List, Optional, Tuple
from urllib import request, parse, error

from app.infrastructure.config.settings import get_settings
import logging

logger = logging.getLogger(__name__)

# --- Shared access token cache (per-process) ---
_token_lock = threading.Lock()
_shared_access_token: Optional[str] = None
_shared_token_expiry: float = 0.0


def _token_valid_shared() -> bool:
    return bool(_shared_access_token) and (time.time() < _shared_token_expiry - 30)


def _refresh_access_token(settings) -> Tuple[str, int]:
    """Perform refresh-token flow and return (access_token, expires_in)."""
    if not (settings.zoho_client_id and settings.zoho_client_secret and settings.zoho_refresh_token):
        raise ZohoAuthError("Zoho credentials are not configured. Set ZOHO_CLIENT_ID/SECRET/REFRESH_TOKEN.")

    token_url = f"{settings.zoho_accounts_base_url}/oauth/v2/token"
    data = parse.urlencode(
        {
            "refresh_token": settings.zoho_refresh_token,
            "client_id": settings.zoho_client_id,
            "client_secret": settings.zoho_client_secret,
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

    expires_in = int(payload.get("expires_in", 3600))
    return access, expires_in


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

    def _get_access_token(self) -> str:
        global _shared_access_token, _shared_token_expiry
        # Fast path: shared cache hit
        if _token_valid_shared():
            self._access_token = _shared_access_token  # type: ignore[assignment]
            self._token_expiry = _shared_token_expiry
            return self._access_token  # type: ignore[return-value]

        # Refresh under lock to avoid burst refresh (Zoho 10req/10min limit)
        with _token_lock:
            if _token_valid_shared():
                self._access_token = _shared_access_token  # type: ignore[assignment]
                self._token_expiry = _shared_token_expiry
                return self._access_token  # type: ignore[return-value]

            access, expires_in = _refresh_access_token(self.settings)
            _shared_access_token = access
            _shared_token_expiry = time.time() + expires_in
            self._access_token = access
            self._token_expiry = _shared_token_expiry
            logger.info("[zoho] access token refreshed (expires_in=%ss)", expires_in)
            return access

    def _post(self, path: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal POST helper (JSON) with shared auth handling."""
        base = self.settings.zoho_api_base_url.rstrip("/")
        url = f"{base}{path}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {self._get_access_token()}",
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode("utf-8")
        req = request.Request(url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8")
                return json.loads(text) if text else {}
        except error.HTTPError as e:
            if e.code == 204:
                return {}
            body = e.read().decode("utf-8", "ignore")
            raise RuntimeError(f"Zoho POST {path} failed: {e.code} {body}") from e
        except ZohoAuthError:
            # bubble up to caller; they decide whether to surface 400 or continue
            raise

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

        # Search Records API helper
        def _search_api(op: str) -> Dict[str, Any]:
            crit = f"({name_field}:{op}:{name})"
            params: Dict[str, Any] = {"criteria": crit, "per_page": limit}
            fields = ["id", name_field]
            if id_field:
                fields.append(id_field)
            params["fields"] = ",".join(fields)
            return self._get(f"/crm/v2/{module_api}/search", params) or {}

        data: List[Dict[str, Any]] = []
        last_err: Optional[Exception] = None
        # contains is often unsupported on custom modules; try safer ops first
        for op in ("starts_with", "equals", "contains"):
            try:
                legacy = _search_api(op)
                data = legacy.get("data", []) or []
                if data:
                    logger.info("[zoho] search op=%s hit=%s", op, len(data))
                    break
            except Exception as e:
                last_err = e
                logger.warning("[zoho] search API failed op=%s err=%s", op, e)
                continue

        if not data and last_err:
            # Return empty for caller-friendly "not found" behavior
            pass
        records = []
        for r in data or []:
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

    def search_app_hc_by_exact_name(self, name: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search APP-hc by candidate name with strict equality (equals).

        Returns records with minimal fields: id (Zoho record id), candidate name, candidate id (custom field).
        0 or multiple hits should be handled by the caller (we do not pick one heuristically).
        """
        module_api = self.settings.zoho_app_hc_module

        # Resolve field API names if not provided
        name_field = self.settings.zoho_app_hc_name_field_api or self.get_field_api_name(module_api, "求職者名")
        id_field = self.settings.zoho_app_hc_id_field_api or self.get_field_api_name(module_api, "求職者ID")
        if not name_field:
            raise RuntimeError(
                "APP-hc name field API not resolvable. Set ZOHO_APP_HC_MODULE/ZOHO_APP_HC_NAME_FIELD_API explicitly or use /api/v1/zoho/modules and /api/v1/zoho/fields to discover."
            )

        def _search_api_equals() -> Dict[str, Any]:
            crit = f"({name_field}:equals:{name})"
            params: Dict[str, Any] = {"criteria": crit, "per_page": limit}
            fields = ["id", name_field]
            if id_field:
                fields.append(id_field)
            params["fields"] = ",".join(fields)
            return self._get(f"/crm/v2/{module_api}/search", params) or {}

        logger.info("[zoho] search exact (search API): module=%s name=%s", module_api, name)
        data: List[Dict[str, Any]] = []
        try:
            legacy = _search_api_equals()
            data = legacy.get("data", []) or []
        except ZohoAuthError:
            raise
        except Exception as e:
            logger.warning("[zoho] search exact failed: %s", e)

        records = []
        for r in data or []:
            records.append(
                {
                    "record_id": r.get("id"),
                    "candidate_name": r.get(name_field),
                    "candidate_id": (r.get(id_field) if id_field else None),
                    "raw": r,
                }
            )
        logger.info("[zoho] search exact results: count=%s", len(records))
        return records

    # --- 流入経路検索・集計メソッド (Marketing ChatKit用) ---

    # Zoho CRM APP-hc フィールドのAPIマッピング
    # 実際のZohoフィールド名（field14, customer_status等）を使用
    CHANNEL_FIELD_API = "field14"  # 流入経路
    STATUS_FIELD_API = "customer_status"  # 顧客ステータス
    NAME_FIELD_API = "Name"  # 求職者名（デフォルト）
    DATE_FIELD_API = "field18"  # 登録日（date型、YYYY-MM-DD形式）

    def _fetch_all_records(
        self,
        max_pages: int = 10,
    ) -> List[Dict[str, Any]]:
        """Records APIで全レコードを取得（ページング対応）

        Note:
            Zoho Search APIは日付フィールドの比較演算子(greater_equal等)を
            サポートしていないため、日付フィルタが必要な場合はRecords APIで
            全件取得し、クライアントサイドでフィルタリングする必要がある。

        Args:
            max_pages: 最大ページ数（200件/ページ、デフォルト10ページ=2000件）

        Returns:
            全レコードのリスト
        """
        module_api = self.settings.zoho_app_hc_module
        all_records: List[Dict[str, Any]] = []
        page = 1

        while page <= max_pages:
            params = {"per_page": 200, "page": page}
            try:
                result = self._get(f"/crm/v2/{module_api}", params) or {}
                data = result.get("data", []) or []
                info = result.get("info", {}) or {}

                all_records.extend(data)

                if not info.get("more_records"):
                    break
                page += 1
            except Exception as e:
                logger.warning("[zoho] _fetch_all_records page %d failed: %s", page, e)
                break

        logger.info("[zoho] _fetch_all_records: total=%d pages=%d", len(all_records), page)
        return all_records

    def _filter_by_date(
        self,
        records: List[Dict[str, Any]],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> List[Dict[str, Any]]:
        """レコードを登録日（field18）でフィルタリング

        Args:
            records: フィルタ対象のレコード
            date_from: 開始日（YYYY-MM-DD形式、この日を含む）
            date_to: 終了日（YYYY-MM-DD形式、この日を含む）

        Returns:
            フィルタ後のレコード
        """
        if not date_from and not date_to:
            return records

        filtered = []
        for r in records:
            # field18（登録日）は YYYY-MM-DD 形式
            reg_date = r.get(self.DATE_FIELD_API, "")
            if not reg_date:
                continue

            # 日付比較（文字列比較でOK、YYYY-MM-DD形式なので）
            if date_from and reg_date < date_from:
                continue
            if date_to and reg_date > date_to:
                continue

            filtered.append(r)

        return filtered

    def search_by_criteria(
        self,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        name: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """条件指定で求職者（APP-hc）を検索

        Note:
            Zoho CRM Search APIは日付フィールドの比較演算子(greater_equal,
            less_equal, between等)をサポートしていない。そのため、日付フィルタが
            指定された場合はRecords APIで全件取得後、クライアントサイドで
            フィルタリングを行う。

        Args:
            channel: 流入経路（例: paid_meta, sco_bizreach, org_hitocareer）
            status: 顧客ステータス（例: 1. リード, 3. 面談待ち）
            name: 求職者名（部分一致）
            date_from: 登録日開始（YYYY-MM-DD）- field18でフィルタ
            date_to: 登録日終了（YYYY-MM-DD）- field18でフィルタ
            limit: 取得件数（最大200）

        Returns:
            検索結果のリスト
        """
        module_api = self.settings.zoho_app_hc_module
        has_date_filter = bool(date_from or date_to)

        # 日付フィルタがある場合: Records API + クライアントサイドフィルタ
        # Zoho Search APIは日付の比較演算子をサポートしていないため
        if has_date_filter:
            logger.info(
                "[zoho] search_by_criteria: using Records API + client-side filter "
                "(date_from=%s, date_to=%s, channel=%s, status=%s)",
                date_from, date_to, channel, status
            )

            # 全レコード取得
            all_records = self._fetch_all_records(max_pages=15)

            # 日付フィルタ（field18: 登録日）
            filtered = self._filter_by_date(all_records, date_from, date_to)

            # 追加フィルタ（channel, status, name）
            if channel:
                filtered = [r for r in filtered if r.get(self.CHANNEL_FIELD_API) == channel]
            if status:
                filtered = [r for r in filtered if r.get(self.STATUS_FIELD_API) == status]
            if name:
                name_lower = name.lower()
                filtered = [
                    r for r in filtered
                    if name_lower in (r.get("Name") or "").lower()
                ]

            # limit適用
            data = filtered[:limit]

        else:
            # 日付フィルタなし: 従来のロジック（Search API or Records API）
            criteria_parts: List[str] = []

            if channel:
                criteria_parts.append(f"({self.CHANNEL_FIELD_API}:equals:{channel})")

            if status:
                criteria_parts.append(f"({self.STATUS_FIELD_API}:equals:{status})")

            if name:
                name_field = self.settings.zoho_app_hc_name_field_api or self.NAME_FIELD_API
                criteria_parts.append(f"({name_field}:contains:{name})")

            if not criteria_parts:
                # 条件なし: Records APIで取得
                params: Dict[str, Any] = {"per_page": min(limit, 200)}
                try:
                    result = self._get(f"/crm/v2/{module_api}", params) or {}
                    data = result.get("data", []) or []
                except Exception as e:
                    logger.warning("[zoho] search_by_criteria (all) failed: %s", e)
                    data = []
            else:
                # 条件あり: Search APIで検索
                criteria = "(" + "and".join(criteria_parts) + ")"
                params = {"criteria": criteria, "per_page": min(limit, 200)}

                logger.info("[zoho] search_by_criteria: criteria=%s", criteria)
                try:
                    result = self._get(f"/crm/v2/{module_api}/search", params) or {}
                    data = result.get("data", []) or []
                except Exception as e:
                    logger.warning("[zoho] search_by_criteria failed: %s", e)
                    data = []

        # 結果を整形（APIフィールド名を使用して取得）
        records = []
        for r in data:
            # Owner情報の取得
            owner = r.get("Owner")
            pic = None
            if isinstance(owner, dict):
                pic = owner.get("name")
            elif owner:
                pic = owner

            records.append({
                "record_id": r.get("id"),
                "求職者名": r.get("Name") or r.get("求職者名"),
                "流入経路": r.get(self.CHANNEL_FIELD_API),
                "顧客ステータス": r.get(self.STATUS_FIELD_API),
                "PIC": pic,
                "登録日": r.get(self.DATE_FIELD_API),  # field18 (登録日) を使用
                "更新日": r.get("Modified_Time"),
            })

        logger.info("[zoho] search_by_criteria results: count=%s", len(records))
        return records

    def count_by_channel(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, int]:
        """流入経路ごとの求職者数を集計

        Args:
            date_from: 集計期間開始（YYYY-MM-DD）
            date_to: 集計期間終了（YYYY-MM-DD）

        Returns:
            流入経路ごとの件数辞書
        """
        # 流入経路マスタ
        channels = [
            "sco_bizreach", "sco_dodaX", "sco_ambi", "sco_rikunavi",
            "sco_nikkei", "sco_liiga", "sco_openwork", "sco_carinar", "sco_dodaX_D&P",
            "paid_google", "paid_meta", "paid_affiliate",
            "org_hitocareer", "org_jobs",
            "feed_indeed", "referral", "other",
        ]

        results: Dict[str, int] = {}

        for channel in channels:
            try:
                records = self.search_by_criteria(
                    channel=channel,
                    date_from=date_from,
                    date_to=date_to,
                    limit=200,
                )
                results[channel] = len(records)
            except Exception as e:
                logger.warning("[zoho] count_by_channel failed for %s: %s", channel, e)
                results[channel] = 0

        logger.info("[zoho] count_by_channel results: total=%s", sum(results.values()))
        return results

    def count_by_status(
        self,
        channel: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> Dict[str, int]:
        """ステータスごとの求職者数を集計（ファネル分析用）

        Args:
            channel: 流入経路でフィルタ（省略時は全体）
            date_from: 集計期間開始（YYYY-MM-DD）
            date_to: 集計期間終了（YYYY-MM-DD）

        Returns:
            ステータスごとの件数辞書
        """
        # ステータスマスタ（実際のZoho設定に合わせる - 番号とステータスの間にスペースあり）
        statuses = [
            "1. リード", "2. コンタクト", "3. 面談待ち", "4. 面談済み",
            "5. 提案中", "6. 応募意思獲得", "7. 打診済み",
            "8. 一次面接待ち", "9. 一次面接済み",
            "10. 最終面接待ち", "11. 最終面接済み",
            "12. 内定", "13. 内定承諾", "14. 入社",
            "15. 入社後退職（入社前退職含む）", "16. クローズ",
            "17. 連絡禁止", "18. 中長期対応", "19. 他社送客",
        ]

        results: Dict[str, int] = {}

        for status in statuses:
            try:
                records = self.search_by_criteria(
                    channel=channel,
                    status=status,
                    date_from=date_from,
                    date_to=date_to,
                    limit=200,
                )
                results[status] = len(records)
            except Exception as e:
                logger.warning("[zoho] count_by_status failed for %s: %s", status, e)
                results[status] = 0

        logger.info("[zoho] count_by_status results: total=%s", sum(results.values()))
        return results

    def get_channel_definitions(self) -> Dict[str, str]:
        """流入経路の定義一覧を返す"""
        return {
            "sco_bizreach": "BizReachスカウト経由で獲得したリード",
            "sco_dodaX": "dodaXスカウト経由で獲得したリード",
            "sco_ambi": "Ambiスカウト経由で獲得したリード",
            "sco_rikunavi": "リクナビスカウト経由で獲得したリード",
            "sco_nikkei": "日経転職版スカウト経由で獲得したリード",
            "sco_liiga": "外資就活ネクストスカウト経由で獲得したリード",
            "sco_openwork": "OpenWorkスカウト経由で獲得したリード",
            "sco_carinar": "Carinarスカウト経由で獲得したリード",
            "sco_dodaX_D&P": "dodaXダイヤモンド/プラチナスカウト経由で獲得したリード",
            "paid_google": "Googleリスティング広告経由で獲得したリード",
            "paid_meta": "Meta広告経由で獲得したリード",
            "paid_affiliate": "アフィリエイト広告経由で獲得したリード",
            "org_hitocareer": "SEOメディア（hitocareer）経由で獲得したリード",
            "org_jobs": "自社求人サイト経由で獲得したリード",
            "feed_indeed": "Indeed経由で獲得したリード",
            "referral": "紹介経由で獲得したリード",
            "other": "その他",
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
            "transfer_reasons": "field58",  # 転職検討理由（複数選択可）'
            "transfer_trigger": "field96",  # 転職検討理由 / きっかけ'
            "desired_timing": "field66",  # 転職希望の時期'
            "timing_details": "field27",  # 転職希望時期の詳細'
            "current_job_status": "field67",  # 現職状況'
            "transfer_status_memo": "transfer_status_memo",
            # "transfer_axis_primary": "field45",  # 転職軸（重要ポイント）- 使用しない
            "transfer_priorities": "transfer_priorities",
            
            # グループ3: 職歴・経験
            "career_history": "field85",  # 職歴'
            "current_duties": "field131",  # 現職での担当業務
            "company_good_points": "field46",  # 現職企業の良いところ'
            "company_bad_points": "field56",  # 現職企業の悪いところ'
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
            "current_salary": "field28",  # 現年収（数字のみ）'
            "salary_breakdown": "field35",  # 現年収内訳'
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
        access, expires_in = _refresh_access_token(self.settings)
        self._access_token = access
        self._token_expiry = time.time() + expires_in
        return access
    
    def _get_access_token(self) -> str:
        global _shared_access_token, _shared_token_expiry
        if _token_valid_shared():
            self._access_token = _shared_access_token  # type: ignore[assignment]
            self._token_expiry = _shared_token_expiry
            return self._access_token  # type: ignore[return-value]

        with _token_lock:
            if _token_valid_shared():
                self._access_token = _shared_access_token  # type: ignore[assignment]
                self._token_expiry = _shared_token_expiry
                return self._access_token  # type: ignore[return-value]

            # Fallback to instance fetch (also updates shared via self variables after)
            access, expires_in = _refresh_access_token(self.settings)
            _shared_access_token = access
            _shared_token_expiry = time.time() + expires_in
            self._access_token = access
            self._token_expiry = _shared_token_expiry
            logger.info("[zoho] access token refreshed (write) expires_in=%s", expires_in)
            return access
    
    def _convert_structured_data_to_zoho(self, structured_data: Dict[str, Any]) -> Dict[str, Any]:
        """構造化出力データをZohoフィールド形式に変換（再実行・上書き対応）"""
        zoho_data = {}

        # フィールド長制限定義（文字数制限のあるテキストフィールド）
        text_field_limits = {
            # テキストフィールドの255文字制限
            "difficult_work": 255,
            "enjoyed_work": 255,
            "salary_memo": 255,
            "remote_time_memo": 255,
            "transfer_status_memo": 255,
            "culture_scale_memo": 255,
            "industry_reason": 255,
            "position_industry_reason": 255,
            "max_future_salary": 255,
            "customer_acquisition": 255,
            "base_incentive_ratio": 255,
            "new_existing_ratio": 255,
            # より長いテキストフィールド（あれば）
            "transfer_priorities": 1000,
            "companies_in_selection": 500,
            "other_company_intention": 500,
            "job_appeal_points": 500,
            "job_concerns": 500,
            "introduced_jobs": 500,
            "other_offer_salary": 255,
            "ca_ra_focus": 255,
        }

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
                converted_text = "\n".join(clean_values) if clean_values else ""

                # 文字数制限チェック
                if structured_field in text_field_limits:
                    max_length = text_field_limits[structured_field]
                    if len(converted_text) > max_length:
                        original_length = len(converted_text)
                        converted_text = converted_text[:max_length].rstrip()  # 切り詰めて末尾空白除去
                        logger.warning(f"📏 フィールド長制限適用: {structured_field} ({original_length}文字 -> {len(converted_text)}文字)")

                zoho_data[zoho_field] = converted_text
            elif isinstance(value, (int, float)):
                zoho_data[zoho_field] = value
            elif isinstance(value, str):
                # 文字列の場合は文字数制限チェック
                cleaned_value = value.strip()

                if structured_field in text_field_limits:
                    max_length = text_field_limits[structured_field]
                    if len(cleaned_value) > max_length:
                        original_length = len(cleaned_value)
                        cleaned_value = cleaned_value[:max_length].rstrip()  # 切り詰めて末尾空白除去
                        logger.warning(f"📏 フィールド長制限適用: {structured_field} ({original_length}文字 -> {len(cleaned_value)}文字)")

                zoho_data[zoho_field] = cleaned_value
            else:
                # その他の型は文字列に変換してから文字数制限チェック
                converted_value = str(value).strip()

                if structured_field in text_field_limits:
                    max_length = text_field_limits[structured_field]
                    if len(converted_value) > max_length:
                        original_length = len(converted_value)
                        converted_value = converted_value[:max_length].rstrip()  # 切り詰めて末尾空白除去
                        logger.warning(f"📏 フィールド長制限適用: {structured_field} ({original_length}文字 -> {len(converted_value)}文字)")

                zoho_data[zoho_field] = converted_value

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

                logger.info(f"📜 Zoho応答詳細: {response_data}")

                # レスポンスボディ内でエラーが含まれているかチェック
                has_errors = False
                error_messages = []

                if response_data and 'data' in response_data and response_data['data']:
                    for record in response_data['data']:
                        # 個別レコードでエラーステータスをチェック
                        if record.get('status') == 'error':
                            has_errors = True
                            error_code = record.get('code', 'UNKNOWN')
                            error_message = record.get('message', 'Unknown error')
                            error_details = record.get('details', {})

                            # 詳細なエラーメッセージを構築
                            detailed_message = f"{error_code}: {error_message}"
                            if error_details:
                                if isinstance(error_details, dict):
                                    detail_parts = []
                                    for key, value in error_details.items():
                                        detail_parts.append(f"{key}={value}")
                                    detailed_message += f" ({', '.join(detail_parts)})"
                                else:
                                    detailed_message += f" ({error_details})"

                            error_messages.append(detailed_message)
                            logger.error(f"❌ Zoho個別レコードエラー: {detailed_message}")

                if has_errors:
                    # エラーが含まれている場合は失敗として処理
                    combined_error = "; ".join(error_messages)
                    logger.error(f"❌ Zoho書き込み失敗（応答エラー）: 求職者「{candidate_name or '不明'}」(record_id={record_id})")
                    logger.error(f"💥 エラー詳細: {combined_error}")

                    return {
                        "status": "error",
                        "status_code": resp.getcode(),
                        "error": combined_error,
                        "raw_response": response_data,
                        "attempted_data": zoho_data
                    }

                # エラーがない場合は成功として処理
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
            "transfer_reasons": "field58",  # 転職検討理由（複数選択可）'
            "transfer_trigger": "field96",  # 転職検討理由 / きっかけ'
            "desired_timing": "field66",  # 転職希望の時期'
            "timing_details": "field27",  # 転職希望時期の詳細'
            "current_job_status": "field67",  # 現職状況'
            "transfer_status_memo": "transfer_status_memo",
            # "transfer_axis_primary": "field45",  # 転職軸（重要ポイント）- 使用しない
            "transfer_priorities": "transfer_priorities",
            
            # グループ3: 職歴・経験
            "career_history": "field85",  # 職歴'
            "current_duties": "field131",  # 現職での担当業務
            "company_good_points": "field46",  # 現職企業の良いところ'
            "company_bad_points": "field56",  # 現職企業の悪いところ'
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
            "current_salary": "field28",  # 現年収（数字のみ）'
            "salary_breakdown": "field35",  # 現年収内訳'
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

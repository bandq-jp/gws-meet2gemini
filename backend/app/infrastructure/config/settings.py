from __future__ import annotations
import os
from functools import lru_cache
import dotenv

# Load environment from .env if present (local dev)
dotenv.load_dotenv()

class Settings:
    # Google Auth
    service_account_json: str = os.getenv("SERVICE_ACCOUNT_JSON", "service_account.json")
    impersonate_subjects: list[str] = [s.strip() for s in os.getenv("GOOGLE_SUBJECT_EMAILS", "").split(",") if s.strip()]

    # Supabase
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

    # Runtime
    environment: str = os.getenv("ENV", os.getenv("ENVIRONMENT", "local"))

    # Gemini
    gemini_api_key: str = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    gemini_fallback_model: str = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
    gemini_temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.1"))
    gemini_max_tokens: int = int(os.getenv("GEMINI_MAX_TOKENS", "20000"))

    # Zoho CRM (read-only)
    zoho_accounts_base_url: str = os.getenv("ZOHO_ACCOUNTS_BASE_URL", "https://accounts.zoho.jp")
    zoho_api_base_url: str = os.getenv("ZOHO_API_BASE_URL", "https://www.zohoapis.jp")
    zoho_client_id: str | None = os.getenv("ZOHO_CLIENT_ID") or None
    zoho_client_secret: str | None = os.getenv("ZOHO_CLIENT_SECRET") or None
    zoho_refresh_token: str | None = os.getenv("ZOHO_REFRESH_TOKEN") or None
    # APP-hc module configuration
    zoho_app_hc_module: str = os.getenv("ZOHO_APP_HC_MODULE", "CustomModule1")
    # If not set, field API names will be auto-discovered by display label lookup
    zoho_app_hc_name_field_api: str | None = os.getenv("ZOHO_APP_HC_NAME_FIELD_API") or None
    zoho_app_hc_id_field_api: str | None = os.getenv("ZOHO_APP_HC_ID_FIELD_API") or None

    # Cloud Tasks / Cloud Run
    gcp_project: str = os.getenv("GCP_PROJECT", os.getenv("GOOGLE_CLOUD_PROJECT", ""))
    tasks_location: str = os.getenv("TASKS_LOCATION", os.getenv("REGION", "asia-northeast1"))
    tasks_queue: str = os.getenv("TASKS_QUEUE", "meet2gemini-collect")
    # Cloud Run のワーカーURL（後述の worker エンドポイントのフルURL）
    tasks_worker_url: str = os.getenv("TASKS_WORKER_URL", "")
    tasks_autoproc_worker_url: str = os.getenv("TASKS_AUTOPROC_WORKER_URL", "")
    # OIDC で署名するサービスアカウント（Cloud Tasks 側）
    tasks_oidc_service_account: str = os.getenv("TASKS_OIDC_SERVICE_ACCOUNT", "")
    # 監査/追加制御用：期待するQueue名（ヘッダ検証）
    expected_queue_name: str = os.getenv("TASKS_EXPECTED_QUEUE_NAME", "meet2gemini-collect")

    # Auto-process settings
    candidate_title_regex: str | None = os.getenv("CANDIDATE_TITLE_REGEX") or None
    autoproc_max_items: int = int(os.getenv("AUTOPROC_MAX_ITEMS", "20"))
    
    # Auto-process parallel execution settings
    autoproc_parallel_workers: int = int(os.getenv("AUTOPROC_PARALLEL_WORKERS", "5"))
    autoproc_batch_size: int = int(os.getenv("AUTOPROC_BATCH_SIZE", "10"))
    
    # Auto-process monitoring settings
    autoproc_success_rate_threshold: float = float(os.getenv("AUTOPROC_SUCCESS_RATE_THRESHOLD", "0.9"))
    autoproc_queue_alert_threshold: int = int(os.getenv("AUTOPROC_QUEUE_ALERT_THRESHOLD", "50"))
    autoproc_error_rate_threshold: float = float(os.getenv("AUTOPROC_ERROR_RATE_THRESHOLD", "0.05"))
    
    # Auto-process schedule settings
    autoproc_backlog_schedule: str = os.getenv("AUTOPROC_BACKLOG_SCHEDULE", "0 */2 * * *")
    autoproc_realtime_schedule: str = os.getenv("AUTOPROC_REALTIME_SCHEDULE", "*/30 10-23 * * *")
    autoproc_maintenance_schedule: str = os.getenv("AUTOPROC_MAINTENANCE_SCHEDULE", "0 1 * * *")
    
    # Auto-process cost optimization
    autoproc_gemini_model_small_threshold: int = int(os.getenv("AUTOPROC_GEMINI_MODEL_SMALL_THRESHOLD", "5000"))
    autoproc_gemini_model_large_threshold: int = int(os.getenv("AUTOPROC_GEMINI_MODEL_LARGE_THRESHOLD", "15000"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    s = Settings()
    # Derive auto-process worker URL if not explicitly provided
    if not s.tasks_autoproc_worker_url and s.tasks_worker_url:
        # Best-effort replacement of known collect worker path → auto-process worker path
        if "/api/v1/meetings/collect/worker" in s.tasks_worker_url:
            s.tasks_autoproc_worker_url = s.tasks_worker_url.replace(
                "/api/v1/meetings/collect/worker", "/api/v1/structured/auto-process/worker"
            )
        elif "/collect/worker" in s.tasks_worker_url:
            s.tasks_autoproc_worker_url = s.tasks_worker_url.replace(
                "/collect/worker", "/structured/auto-process/worker"
            )
        else:
            # Fallback: construct the URL from base
            if s.tasks_worker_url.endswith("/api/v1/meetings/collect/worker"):
                base_url = s.tasks_worker_url.replace("/api/v1/meetings/collect/worker", "")
                s.tasks_autoproc_worker_url = f"{base_url}/api/v1/structured/auto-process/worker"
            else:
                s.tasks_autoproc_worker_url = s.tasks_worker_url
    return s

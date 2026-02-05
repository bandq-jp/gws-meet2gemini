from __future__ import annotations
import os
from functools import lru_cache
import dotenv

# Load environment from .env if present (local dev)
dotenv.load_dotenv()

def _default_marketing_upload_base_url() -> str:
    explicit = os.getenv("MARKETING_UPLOAD_BASE_URL")
    if explicit is not None:
        return explicit
    env = os.getenv("ENV", os.getenv("ENVIRONMENT", "local")).lower()
    if env == "local":
        return "http://localhost:3000"
    return ""

class Settings:
    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # Google Auth
    service_account_json: str = os.getenv("SERVICE_ACCOUNT_JSON", "service_account.json")
    impersonate_subjects: list[str] = [s.strip() for s in os.getenv("GOOGLE_SUBJECT_EMAILS", "").split(",") if s.strip()]
    # Meeting source switch (google_docs / notta / both)
    meeting_source: str = os.getenv("MEETING_SOURCE", "google_docs")

    # Notta (shared drive xlsx)
    notta_drive_id: str = os.getenv("NOTTA_DRIVE_ID", "")
    notta_folder_id: str = os.getenv("NOTTA_FOLDER_ID", "")
    notta_folder_name: str = os.getenv("NOTTA_FOLDER_NAME", "")
    notta_impersonate_subject: str = os.getenv("NOTTA_IMPERSONATE_SUBJECT", "")
    notta_organizer_email: str = os.getenv("NOTTA_ORGANIZER_EMAIL", "notta_shared_drive")

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

    # Marketing chat / ChatKit
    marketing_agent_model: str = os.getenv("MARKETING_AGENT_MODEL", "gpt-5.1")
    marketing_reasoning_effort: str = os.getenv("MARKETING_REASONING_EFFORT", "high")
    marketing_search_country: str = os.getenv("MARKETING_SEARCH_COUNTRY", "JP")
    marketing_enable_web_search: bool = os.getenv("MARKETING_ENABLE_WEB_SEARCH", "true").lower() != "false"
    marketing_enable_code_interpreter: bool = os.getenv("MARKETING_ENABLE_CODE_INTERPRETER", "true").lower() != "false"
    marketing_enable_canvas: bool = os.getenv("MARKETING_ENABLE_CANVAS", "true").lower() != "false"
    marketing_workflow_id: str = os.getenv("MARKETING_WORKFLOW_ID", "wf_690a1d2e1ce881908e92b6826428f3af060621f24cf1b2bb")
    marketing_chatkit_token_secret: str = os.getenv("MARKETING_CHATKIT_TOKEN_SECRET", "")
    marketing_chatkit_token_ttl: int = int(os.getenv("MARKETING_CHATKIT_TOKEN_TTL", "900"))
    marketing_chatkit_api_base: str = os.getenv("MARKETING_CHATKIT_API_BASE", "/api/v1/marketing/chatkit")
    # ブラウザがアップロード先にアクセスするときのベースURL（必須: スキーム/ホスト付き）
    marketing_upload_base_url: str = _default_marketing_upload_base_url()

    # Local MCP settings (STDIO-based) - default enabled for faster initialization
    use_local_mcp: bool = os.getenv("USE_LOCAL_MCP", "true").lower() == "true"
    local_mcp_ga4_enabled: bool = os.getenv("LOCAL_MCP_GA4_ENABLED", "true").lower() == "true"
    local_mcp_gsc_enabled: bool = os.getenv("LOCAL_MCP_GSC_ENABLED", "true").lower() == "true"
    local_mcp_meta_ads_enabled: bool = os.getenv("LOCAL_MCP_META_ADS_ENABLED", "true").lower() == "true"
    mcp_client_timeout_seconds: int = int(os.getenv("MCP_CLIENT_TIMEOUT_SECONDS", "120"))
    # Meta Ads MCP authentication (long-lived access token)
    meta_access_token: str = os.getenv("META_ACCESS_TOKEN", "")

    # Hosted MCP settings (HTTP-based, remote Cloud Run)
    ga4_mcp_server_url: str = os.getenv("GA4_MCP_SERVER_URL", "")
    ga4_mcp_authorization: str = os.getenv("GA4_MCP_AUTHORIZATION", "")
    meta_ads_mcp_server_url: str = os.getenv("META_ADS_MCP_SERVER_URL", "")
    meta_ads_mcp_authorization: str = os.getenv("META_ADS_MCP_AUTHORIZATION", "")
    ahrefs_mcp_server_url: str = os.getenv("AHREFS_MCP_SERVER_URL", "")
    ahrefs_mcp_authorization: str = os.getenv("AHREFS_MCP_AUTHORIZATION", "")
    gsc_mcp_server_url: str = os.getenv("GSC_MCP_SERVER_URL", "")
    gsc_mcp_api_key: str = os.getenv("GSC_MCP_API_KEY", "")
    wordpress_mcp_server_url: str = os.getenv("WORDPRESS_MCP_SERVER_URL", "")
    wordpress_mcp_authorization: str = os.getenv("WORDPRESS_MCP_AUTHORIZATION", "")
    wordpress_achieve_mcp_server_url: str = os.getenv("WORDPRESS_ACHIEVE_MCP_SERVER_URL", "")
    wordpress_achieve_mcp_authorization: str = os.getenv("WORDPRESS_ACHIEVE_MCP_AUTHORIZATION", "")

    # Sub-agent model settings (for OpenAI Agents SDK multi-agent)
    sub_agent_model: str = os.getenv("SUB_AGENT_MODEL", "gpt-5-mini")
    sub_agent_enable_web_search: bool = os.getenv("SUB_AGENT_ENABLE_WEB_SEARCH", "true").lower() == "true"
    sub_agent_enable_code_interpreter: bool = os.getenv("SUB_AGENT_ENABLE_CODE_INTERPRETER", "false").lower() == "true"

    # Reasoning translation (for displaying in Japanese)
    reasoning_translate_model: str = os.getenv("REASONING_TRANSLATE_MODEL", "gpt-5-nano")

    # Google ADK settings (V2 marketing AI)
    use_adk: bool = os.getenv("USE_ADK", "false").lower() == "true"
    adk_orchestrator_model: str = os.getenv("ADK_ORCHESTRATOR_MODEL", "gemini-3-flash-preview")
    adk_sub_agent_model: str = os.getenv("ADK_SUB_AGENT_MODEL", "gemini-3-flash-preview")
    # Max LLM calls per run (0 or negative = unlimited, default 500)
    # Set higher for complex multi-agent workflows, set to 0 for unlimited deep investigation
    adk_max_llm_calls: int = int(os.getenv("ADK_MAX_LLM_CALLS", "0"))
    # Max output tokens per response (Gemini 3 Flash max: 65536)
    adk_max_output_tokens: int = int(os.getenv("ADK_MAX_OUTPUT_TOKENS", "65536"))

    # ADK Memory Service settings
    memory_service_type: str = os.getenv("MEMORY_SERVICE_TYPE", "supabase")
    memory_auto_save: bool = os.getenv("MEMORY_AUTO_SAVE", "true").lower() == "true"
    memory_preload_enabled: bool = os.getenv("MEMORY_PRELOAD_ENABLED", "true").lower() == "true"
    memory_max_results: int = int(os.getenv("MEMORY_MAX_RESULTS", "5"))
    memory_embedding_model: str = os.getenv("MEMORY_EMBEDDING_MODEL", "gemini-embedding-001")
    memory_embedding_dimensions: int = int(os.getenv("MEMORY_EMBEDDING_DIMENSIONS", "768"))

    # Company Database (Google Sheets)
    company_db_spreadsheet_id: str = os.getenv("COMPANY_DB_SPREADSHEET_ID", "")
    company_db_cache_ttl: int = int(os.getenv("COMPANY_DB_CACHE_TTL", "300"))


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

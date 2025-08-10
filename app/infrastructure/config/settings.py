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

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

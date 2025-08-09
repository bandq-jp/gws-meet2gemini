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

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Whoopy"
    app_domain: str = "whoopy.hu"
    secret_key: str = "dev-change-me-whoopy-2026"
    database_url: str = f"sqlite:///{BASE_DIR / 'marketplace.db'}"
    admin_email: str = "admin@whoopy.local"
    admin_password: str = "admin1234"
    currency: str = "HUF"
    default_country: str = "HU"
    session_cookie: str = "whoopy_session"
    host: str = "127.0.0.1"
    port: int = 8090
    # Future ERP bridge (e_commerce_erp on :8010)
    erp_api_base: str = "http://127.0.0.1:8010/api/v1"
    erp_enabled: bool = False
    public_base_url: str = "http://127.0.0.1:8090"
    # Whoopy Management API (ERP / automation) — header: X-API-Key
    api_key: str = "whoopy-dev-api-key-change-me"


settings = Settings()

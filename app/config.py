from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Whoopy"
    app_domain: str = "whoopy.hu"
    # development | production
    environment: Literal["development", "production"] = "development"
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
    # Payments: demo | stripe | simplepay | auto
    payment_provider: str = "auto"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_currency: str = "huf"
    simplepay_merchant: str = ""
    simplepay_secret_key: str = ""
    simplepay_sandbox: bool = True
    simplepay_currency: str = "HUF"
    # Outbound webhooks (Whoopy → ERP / external)
    webhook_enabled: bool = False
    webhook_url: str = "http://127.0.0.1:8010/api/v1/webhooks/whoopy"
    webhook_secret: str = "whoopy-webhook-secret-change-me"
    webhook_timeout_sec: float = 8.0
    # Production hardening
    seed_on_startup: bool = True
    force_https: bool = False
    session_https_only: bool = False
    session_same_site: Literal["lax", "strict", "none"] = "lax"
    cors_origins: str = ""  # comma-separated; empty = no CORS middleware
    trusted_hosts: str = ""  # comma-separated; empty = allow all
    rate_limit_enabled: bool = True
    rate_limit_api_per_minute: int = 120
    docs_enabled: bool = True  # set false in production if desired

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [x.strip() for x in self.trusted_hosts.split(",") if x.strip()]

    def insecure_defaults(self) -> list[str]:
        bad: list[str] = []
        if self.secret_key.startswith("dev-change-me"):
            bad.append("SECRET_KEY")
        if self.api_key.startswith("whoopy-dev-api-key"):
            bad.append("API_KEY")
        if self.webhook_secret.startswith("whoopy-webhook-secret-change"):
            bad.append("WEBHOOK_SECRET")
        if self.admin_password in ("admin1234", "admin", "password"):
            bad.append("ADMIN_PASSWORD")
        return bad


settings = Settings()

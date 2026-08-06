from pathlib import Path
import logging
import sqlite3

from app.config import BASE_DIR, settings
from app.database import Base, engine

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "11"
VERSION_FILE = BASE_DIR / ".schema_version"
DB_PATH = BASE_DIR / "marketplace.db"

# Dev wipe biztonsági háló: ha a kód új oszlopokat vár, de a SQLite még régi
_REQUIRED_COLUMNS = {
    "store_settings": {"company_name", "invoice_footer", "chat_widget_html"},
    "orders": {"invoice_status", "tax_total", "net_total", "access_token", "billing_city"},
    "carts": {"gift_card_code", "delivery_mode"},
}


def _sqlite_missing_required_columns() -> bool:
    if not DB_PATH.exists():
        return False
    try:
        con = sqlite3.connect(DB_PATH)
        try:
            for table, required in _REQUIRED_COLUMNS.items():
                rows = con.execute(f"pragma table_info({table})").fetchall()
                if not rows:
                    return True
                cols = {r[1] for r in rows}
                if not required.issubset(cols):
                    return True
        finally:
            con.close()
    except Exception:
        return True
    return False


def ensure_fresh_schema() -> None:
    """
    Dev SQLite: schema version bump → recreate DB.
    Production / Postgres: never wipe — only create_all (additive).
    """
    is_sqlite = settings.database_url.startswith("sqlite")
    allow_wipe = is_sqlite and not settings.is_production

    current = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""
    stale_shape = allow_wipe and _sqlite_missing_required_columns()

    if allow_wipe and DB_PATH.exists() and (current != SCHEMA_VERSION or stale_shape):
        logger.warning(
            "Schema version %s → %s (stale_shape=%s): recreating SQLite DB",
            current,
            SCHEMA_VERSION,
            stale_shape,
        )
        engine.dispose()
        DB_PATH.unlink(missing_ok=True)

    Base.metadata.create_all(bind=engine)

    if allow_wipe or not VERSION_FILE.exists():
        VERSION_FILE.write_text(SCHEMA_VERSION, encoding="utf-8")
    elif current != SCHEMA_VERSION and not allow_wipe:
        logger.warning(
            "Schema version file is %s but code is %s — production/Postgres: "
            "migrate manually; DB was NOT wiped.",
            current,
            SCHEMA_VERSION,
        )
        VERSION_FILE.write_text(SCHEMA_VERSION, encoding="utf-8")

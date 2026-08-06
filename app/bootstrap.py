from pathlib import Path
import logging
import sqlite3

from app.config import BASE_DIR, settings
from app.database import Base, engine

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "15"
VERSION_FILE = BASE_DIR / ".schema_version"
DB_PATH = BASE_DIR / "marketplace.db"

# Dev wipe biztonsági háló: ha a kód új oszlopokat vár, de a SQLite még régi
_REQUIRED_COLUMNS = {
    "store_settings": {"company_name", "invoice_footer", "chat_widget_html"},
    "orders": {"invoice_status", "tax_total", "net_total", "access_token", "billing_city", "utm_source", "is_b2b"},
    "carts": {"gift_card_code", "delivery_mode", "utm_source", "is_b2b"},
    "campaigns": {"ab_group", "impressions"},
    "return_requests": {"label_code", "refund_status"},
}

# SQLite ADD COLUMN — storefront ops v14 + price history v15
_STORE_SETTINGS_ALTERS = [
    ("maintenance_message", "TEXT DEFAULT 'A bolt átmenetileg zárva van. Hamarosan visszatérünk.'"),
    ("announcement_enabled", "BOOLEAN DEFAULT 0"),
    ("announcement_text", "VARCHAR(512) DEFAULT ''"),
    ("announcement_link", "VARCHAR(512) DEFAULT ''"),
    ("announcement_link_label", "VARCHAR(64) DEFAULT 'Részletek'"),
    ("announcement_bg", "VARCHAR(32) DEFAULT '#0f766e'"),
    ("announcement_starts_at", "DATETIME"),
    ("announcement_ends_at", "DATETIME"),
    ("ticker_enabled", "BOOLEAN DEFAULT 1"),
    ("business_hours", "VARCHAR(255) DEFAULT 'H–P 9:00–17:00'"),
    ("free_shipping_threshold_huf", "FLOAT DEFAULT 25000"),
]

_PRICE_HISTORY_ALTERS = [
    ("previous_price", "FLOAT"),
    ("source", "VARCHAR(64) DEFAULT 'system'"),
]


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


def _sqlite_apply_additive_alters() -> None:
    if not DB_PATH.exists():
        return
    try:
        con = sqlite3.connect(DB_PATH)
        try:
            cols = {r[1] for r in con.execute("pragma table_info(store_settings)").fetchall()}
            for name, ddl in _STORE_SETTINGS_ALTERS:
                if cols and name not in cols:
                    con.execute(f"ALTER TABLE store_settings ADD COLUMN {name} {ddl}")
                    logger.info("SQLite ALTER store_settings ADD %s", name)

            ph_cols = {r[1] for r in con.execute("pragma table_info(price_history)").fetchall()}
            for name, ddl in _PRICE_HISTORY_ALTERS:
                if ph_cols and name not in ph_cols:
                    con.execute(f"ALTER TABLE price_history ADD COLUMN {name} {ddl}")
                    logger.info("SQLite ALTER price_history ADD %s", name)
            con.commit()
        finally:
            con.close()
    except Exception:
        logger.exception("SQLite additive ALTER failed")


def ensure_fresh_schema() -> None:
    """
    Dev SQLite: hiányzó kötelező oszlopok → recreate (ha lehetséges).
    Version bump: create_all + additive ALTER (zárolt DB-nél wipe nélkül).
    Production / Postgres: never wipe.
    """
    is_sqlite = settings.database_url.startswith("sqlite")
    allow_wipe = is_sqlite and not settings.is_production

    current = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""
    current = current.replace(">", "").strip()
    stale_shape = allow_wipe and _sqlite_missing_required_columns()

    if allow_wipe and DB_PATH.exists() and stale_shape:
        logger.warning("Schema stale_shape: recreating SQLite DB (version %s → %s)", current, SCHEMA_VERSION)
        try:
            engine.dispose()
            DB_PATH.unlink(missing_ok=True)
        except PermissionError:
            logger.warning("SQLite wipe blocked (file locked) — falling back to additive ALTER")

    Base.metadata.create_all(bind=engine)
    if is_sqlite:
        _sqlite_apply_additive_alters()

    VERSION_FILE.write_text(SCHEMA_VERSION, encoding="utf-8")
    if current and current != SCHEMA_VERSION and not allow_wipe:
        logger.warning(
            "Schema version file is %s but code is %s — production/Postgres: migrate manually.",
            current,
            SCHEMA_VERSION,
        )

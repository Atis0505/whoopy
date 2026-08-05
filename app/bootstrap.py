from pathlib import Path
import logging

from app.config import BASE_DIR, settings
from app.database import Base, engine

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "8"
VERSION_FILE = BASE_DIR / ".schema_version"
DB_PATH = BASE_DIR / "marketplace.db"


def ensure_fresh_schema() -> None:
    """
    Dev SQLite: schema version bump → recreate DB.
    Production / Postgres: never wipe — only create_all (additive).
    """
    is_sqlite = settings.database_url.startswith("sqlite")
    allow_wipe = is_sqlite and not settings.is_production

    current = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""

    if allow_wipe and current != SCHEMA_VERSION and DB_PATH.exists():
        logger.warning("Schema version %s → %s: recreating SQLite DB", current, SCHEMA_VERSION)
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

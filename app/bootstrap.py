from pathlib import Path

from app.config import BASE_DIR, settings
from app.database import Base, engine

SCHEMA_VERSION = "7"
VERSION_FILE = BASE_DIR / ".schema_version"
DB_PATH = BASE_DIR / "marketplace.db"


def ensure_fresh_schema() -> None:
    """Recreate SQLite DB when schema version changes (dev-friendly)."""
    current = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""
    if current == SCHEMA_VERSION and settings.database_url.startswith("sqlite"):
        # still ensure tables exist
        Base.metadata.create_all(bind=engine)
        return

    if settings.database_url.startswith("sqlite") and DB_PATH.exists():
        engine.dispose()
        DB_PATH.unlink(missing_ok=True)

    Base.metadata.create_all(bind=engine)
    VERSION_FILE.write_text(SCHEMA_VERSION, encoding="utf-8")

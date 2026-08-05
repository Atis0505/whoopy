from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

is_sqlite = settings.database_url.startswith("sqlite")
connect_args = {"check_same_thread": False} if is_sqlite else {}

engine_kwargs = {
    "connect_args": connect_args,
}
if not is_sqlite:
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 5,
            "max_overflow": 10,
        }
    )

engine = create_engine(settings.database_url, **engine_kwargs)


@event.listens_for(engine, "connect")
def _sqlite_pragma(dbapi_connection, _connection_record):
    if is_sqlite:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

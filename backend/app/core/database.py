from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


engine = (
    create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    if settings.DATABASE_URL
    else None
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


def get_db():
    if engine is None:
        raise RuntimeError(
            "DATABASE_URL must be configured to use the legacy SQLAlchemy database."
        )
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

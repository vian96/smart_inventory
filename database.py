from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:///./inventory.db"

# check_same_thread=False специфичен только для SQLite
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Базовый класс для всех моделей (SQLAlchemy 2.0 style)"""


def get_db():
    """Dependency для получения сессии БД в эндпоинтах"""
    db = _session_local()
    try:
        yield db
    finally:
        db.close()

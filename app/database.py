from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

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


# SQLite в памяти (в основном для тестов)
SQLALCHEMY_INMEMORY_DATABASE_URL = "sqlite://"

inmemory_engine = create_engine(
    SQLALCHEMY_INMEMORY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_inmemory_session_local = sessionmaker(autocommit=False, autoflush=False, bind=inmemory_engine)


def get_inmemory_db():
    db = _inmemory_session_local()
    try:
        yield db
    finally:
        db.close()

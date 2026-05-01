from datetime import timedelta

import pytest
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from app.auth import (
    ALGORITHM,
    SECRET_KEY,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.database import Base, _inmemory_session_local, inmemory_engine
from app.models import User

# --- Настройка тестовой БД ---


@pytest.fixture(scope="function")
def db_session():
    """Создает чистую сессию БД для каждого теста."""
    Base.metadata.create_all(bind=inmemory_engine)
    session = _inmemory_session_local()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=inmemory_engine)


@pytest.fixture
def test_user(db_session: Session):
    """Создает тестового пользователя."""
    user = User(
        username="test_auth_user",
        hashed_password=get_password_hash("secure_password"),
        role="manager",
    )
    db_session.add(user)
    db_session.commit()
    return user


# --- Тесты authenticate_user ---


def test_authenticate_user_not_found(db_session: Session):
    """Негативный кейс: пользователь не существует."""
    user = authenticate_user(db_session, "non_existent", "password")
    assert user is None


def test_authenticate_user_wrong_password(db_session: Session, test_user: User):
    """Негативный кейс: неверный пароль."""
    user = authenticate_user(db_session, test_user.username, "wrong_password")
    assert user is None


# --- Тесты get_current_user (FastAPI Dependency) ---


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session: Session):
    """Негативный кейс: токен невалиден (плохая подпись или формат)."""
    invalid_token = "not-a-real-jwt-token"
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=invalid_token, db=db_session)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert excinfo.value.detail == "Could not validate credentials"


@pytest.mark.asyncio
async def test_get_current_user_missing_sub(db_session: Session):
    """Негативный кейс: в токене отсутствует поле 'sub'."""
    data = {"some_other_field": "data"}
    token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=token, db=db_session)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_user_removed(db_session: Session):
    """
    Негативный кейс: токен валиден, но пользователь
    был удален из БД в промежутке.
    """
    token = create_access_token(data={"sub": "ghost_user"})

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=token, db=db_session)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_current_user_expired_token(db_session: Session, test_user: User):
    """Негативный кейс: срок действия токена истек."""
    token = create_access_token(
        data={"sub": test_user.username}, expires_delta=timedelta(minutes=-1)
    )

    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token=token, db=db_session)

    assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED


# --- Тесты вспомогательных функций ---


def test_verify_password_fail():
    """Проверка того, что verify_password возвращает False при несовпадении."""
    pw_hash = get_password_hash("correct")
    assert verify_password("wrong", pw_hash) is False

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import TokenData

# Конфигурация безопасности
SECRET_KEY = "super-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Настройка контекста шифрования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# URL, на который клиент будет отправлять credentials для получения токена
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка соответствия пароля его хешу."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Генерация bcrypt хеша из сырого пароля."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена доступа."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Annotated[Session, Depends(get_db)]
) -> User:
    """
    Зависимость (dependency) для получения текущего пользователя из JWT.
    Используется для защиты эндпоинтов.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        raise credentials_exception from e

    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Дополнительный слой проверки, если нужно проверять статус 'active'.
    В данной версии возвращает пользователя напрямую.
    """
    return current_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """
    Проверяет существование пользователя и валидность пароля.
    Возвращает объект User при успехе, иначе None.
    """
    user = db.query(User).filter(User.username == username).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

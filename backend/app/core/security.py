from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_BCRYPT_MAX_BYTES = 72


def _prepare_password_for_bcrypt(password: str) -> str:
    """bcrypt only supports passwords up to 72 bytes.
    Truncate safely before hashing/verifying to avoid runtime crashes.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) <= _BCRYPT_MAX_BYTES:
        return password
    return password_bytes[:_BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def hash_password(password: str) -> str:
    return pwd_context.hash(_prepare_password_for_bcrypt(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(
        _prepare_password_for_bcrypt(plain_password),
        hashed_password,
    )


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
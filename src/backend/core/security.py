"""Security, password hashing, and JWT utilities."""

import os
import jwt
from datetime import datetime, timedelta
from typing import Optional
from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext

from backend.core.config import logger
from backend.models.user import UserInDB

security_bearer = HTTPBearer(auto_error=False)
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
argon2_hasher = PasswordHasher()

# Get or configure JWT secret
_env_secret = os.getenv("JWT_SECRET", "").strip()
_is_prod = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).lower() == "production"

if not _env_secret or _env_secret == "CHANGE_THIS_DEV_SECRET":
    if _is_prod:
        raise RuntimeError("[SECURITY CRITICAL] JWT_SECRET must be explicitly set in production environment!")
    logger.warning("[Security] JWT_SECRET is missing or set to default. Using DEV fallback secret.")
    JWT_SECRET = "DEV_FALLBACK_SECRET_KEY_DO_NOT_USE_IN_PROD_9876543210"
else:
    JWT_SECRET = _env_secret

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))  # Default 7 days
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "agy_session")
AUTH_COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "true" if _is_prod else "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against an Argon2 or legacy bcrypt hash."""
    try:
        if hashed_password.startswith("$argon2"):
            return argon2_hasher.verify(hashed_password, plain_password)
        return bcrypt_context.verify(plain_password, hashed_password)
    except VerifyMismatchError:
        return False
    except Exception as e:
        logger.error("[Security] Error verifying password: %s", e)
        return False


def get_password_hash(password: str) -> str:
    """Hash a password using Argon2id."""
    try:
        return argon2_hasher.hash(password)
    except Argon2Error as e:
        logger.error("[Security] Error hashing password: %s", e)
        raise


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def set_auth_cookie(response: Response, token: str) -> None:
    """Attach the JWT as an HttpOnly cookie for browser flows."""
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        max_age=JWT_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    """Clear the auth cookie during logout."""
    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/", samesite="lax", secure=AUTH_COOKIE_SECURE)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[Security] Token expired.")
        return None
    except jwt.PyJWTError as e:
        logger.warning("[Security] Token validation error: %s", e)
        return None


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
) -> UserInDB:
    """FastAPI dependency to authenticate and return the current active user."""
    token = credentials.credentials if credentials and credentials.credentials else request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập để truy cập tính năng này.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập hết hạn hoặc không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên đăng nhập không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Avoid circular import at top level
    from backend.core.db import get_user_by_id

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị vô hiệu hóa.",
        )

    return user


async def require_admin(
    current_user: UserInDB = Depends(get_current_user),
) -> UserInDB:
    """FastAPI dependency requiring admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập.",
        )
    return current_user

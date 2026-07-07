"""Authentication router."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.core.security import (
    clear_auth_cookie,
    create_access_token,
    get_password_hash,
    set_auth_cookie,
    verify_password,
)
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.cache import cache

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
def register(
    user_in: UserCreate, response: Response, db: Session = Depends(get_db)
) -> Any:
    """Register a new user, store in database, and return JWT access token with HttpOnly cookie."""
    existing_user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email đã được sử dụng. Vui lòng chọn email khác.",
        )

    db_user = User(
        email=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role="user",
        is_active=True,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    access_token = create_access_token({"sub": db_user.id, "role": db_user.role})
    set_auth_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": db_user,
    }


@router.post("/login", response_model=TokenResponse)
def login(
    user_in: UserLogin, response: Response, db: Session = Depends(get_db)
) -> Any:
    """Authenticate user credentials and set HttpOnly JWT cookie."""
    user = db.query(User).filter(User.email == user_in.email.lower()).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị vô hiệu hóa.",
        )

    access_token = create_access_token({"sub": user.id, "role": user.role})
    set_auth_cookie(response, access_token)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Invalidate current JWT token by adding to blacklist and clearing HttpOnly cookie."""
    # Get token from header or cookie
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    else:
        token = request.cookies.get(settings.AUTH_COOKIE_NAME)

    if token:
        # Blacklist token in memory cache for remaining TTL (default 7 days = 604800s)
        cache.set(
            f"blacklist:{token}", "revoked", ttl_seconds=settings.JWT_EXPIRE_MINUTES * 60
        )

    clear_auth_cookie(response)
    return {"detail": "Đăng xuất thành công."}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)) -> Any:
    """Get current authenticated user information."""
    return current_user

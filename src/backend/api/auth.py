"""Authentication API router."""

import re
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response, status

from backend.core.config import logger
from backend.core.db import create_user, get_user_by_email, update_last_login, update_learning_profile
from backend.core.security import (
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    get_password_hash,
    set_auth_cookie,
    verify_password,
)
from backend.models.learning_profile import LearningProfileUpdateRequest, resolve_profile_for_role
from backend.models.user import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserInDB,
    UserPublic,
)

router = APIRouter(tags=["Authentication"])

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


def _to_public(user: UserInDB) -> UserPublic:
    return UserPublic(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        learning_profile=user.learning_profile,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, response: Response):
    """Register a new user account."""
    email = req.email.strip().lower()
    if not email or not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Email không hợp lệ.")

    if not req.password or len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 8 ký tự.")

    existing = get_user_by_email(email)
    if existing:
        raise HTTPException(status_code=409, detail="Email đã được đăng ký.")

    try:
        now = datetime.utcnow()
        user_id = str(uuid.uuid4())
        hashed = get_password_hash(req.password)

        new_user = UserInDB(
            id=user_id,
            email=email,
            password_hash=hashed,
            full_name=req.full_name.strip() if req.full_name else None,
            role="user",
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login_at=now,
        )
        created = create_user(new_user)
        access_token = create_access_token(data={"sub": created.id, "email": created.email, "role": created.role})
        set_auth_cookie(response, access_token)

        logger.info("[Auth] User registered successfully: %s (%s)", created.email, created.id)
        return TokenResponse(access_token=access_token, token_type="bearer", user=_to_public(created))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("[Auth] Registration error: %s", e)
        raise HTTPException(status_code=500, detail="Không thể tạo tài khoản, vui lòng thử lại.")


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response):
    """Login with email and password."""
    email = req.email.strip().lower()
    user = get_user_by_email(email)

    if not user or not verify_password(req.password, user.password_hash):
        logger.warning("[Auth] Login failed for email: %s", email)
        raise HTTPException(status_code=400, detail="Email hoặc mật khẩu không đúng.")

    if not user.is_active:
        logger.warning("[Auth] Login attempt for disabled user: %s", email)
        raise HTTPException(status_code=403, detail="Tài khoản đã bị vô hiệu hóa.")

    update_last_login(user.id)

    access_token = create_access_token(data={"sub": user.id, "email": user.email, "role": user.role})
    set_auth_cookie(response, access_token)
    logger.info("[Auth] User logged in successfully: %s", user.email)
    return TokenResponse(access_token=access_token, token_type="bearer", user=_to_public(user))


@router.post("/logout")
async def logout(response: Response):
    """Logout current user."""
    clear_auth_cookie(response)
    return {"detail": "Đăng xuất thành công"}


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return _to_public(current_user)


@router.put("/me/learning-profile", response_model=UserPublic)
async def update_my_learning_profile(
    req: LearningProfileUpdateRequest, current_user: UserInDB = Depends(get_current_user)
):
    """Set or change the current user's Learning Profile (onboarding or settings).

    Only `role_mode` is required — any other field left unset falls back to that
    role's curated default (see ROLE_MODE_DEFAULTS) rather than a generic one.
    Changing mode never deletes previously generated outputs (Book/Slides/Mindmap/
    Quiz/Flashcards/Summary/Video) — it only affects what's generated on the next
    (re)generate call for this course.
    """
    resolved = resolve_profile_for_role(req.role_mode, req.model_dump(exclude={"role_mode"}))
    profile_dict = resolved.model_dump()
    update_learning_profile(current_user.id, profile_dict)
    current_user.learning_profile = profile_dict
    return _to_public(current_user)

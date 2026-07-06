"""Admin API router for user management."""

import re
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from backend.core.config import logger
from backend.core.db import (
    count_active_admins,
    delete_user,
    get_all_users,
    get_user_by_email,
    get_user_by_id,
    update_user_fields,
)
from backend.core.security import get_password_hash, require_admin
from backend.models.user import UserInDB, UserPublic


router = APIRouter(tags=["Admin"], dependencies=[Depends(require_admin)])
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


class AdminUpdateUserRequest(BaseModel):
    """Payload for PATCH /admin/users/{user_id}."""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: Optional[str]) -> Optional[str]:
        if not isinstance(v, str):
            return v
        normalized = v.strip().lower()
        if normalized and not EMAIL_REGEX.match(normalized):
            raise ValueError("Email khong hop le.")
        return normalized or None

    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in {"user", "admin"}:
            raise ValueError("Role phải là 'user' hoặc 'admin'.")
        return v


class AdminResetPasswordRequest(BaseModel):
    """Payload for POST /admin/users/{user_id}/reset-password."""
    new_password: str = Field(..., min_length=8, description="Mật khẩu mới tối thiểu 8 ký tự.")


@router.get("/users", response_model=list[UserPublic])
async def list_users():
    """List all users in the system."""
    users = get_all_users()
    return [_to_public(u) for u in users]


@router.get("/users/{user_id}", response_model=UserPublic)
async def get_user(user_id: str):
    """Get a specific user by ID."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")
    return _to_public(user)


@router.patch("/users/{user_id}", response_model=UserPublic)
async def update_user(user_id: str, req: AdminUpdateUserRequest):
    """Update user details."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    # Check email uniqueness if email is changing
    if req.email and req.email != user.email:
        existing = get_user_by_email(req.email)
        if existing and existing.id != user_id:
            raise HTTPException(status_code=409, detail="Email này đã được sử dụng bởi tài khoản khác.")

    # Safety check: prevent demoting or disabling the last active admin
    if user.role == "admin" and user.is_active:
        is_demoting = req.role is not None and req.role != "admin"
        is_disabling = req.is_active is not None and req.is_active is False
        if (is_demoting or is_disabling) and count_active_admins() <= 1:
            raise HTTPException(
                status_code=400,
                detail="Không thể vô hiệu hóa hoặc giáng chức quản trị viên duy nhất của hệ thống.",
            )

    updates = req.model_dump(exclude_unset=True)
    updated = update_user_fields(user_id, updates)
    if not updated:
        raise HTTPException(status_code=500, detail="Cập nhật người dùng thất bại.")
    logger.info("[Admin] Updated user %s (%s): %s", updated.email, updated.id, updates)
    return _to_public(updated)


@router.post("/users/{user_id}/disable", response_model=UserPublic)
async def disable_user(user_id: str):
    """Disable a user account."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    if user.role == "admin" and user.is_active and count_active_admins() <= 1:
        raise HTTPException(
            status_code=400,
            detail="Không thể vô hiệu hóa quản trị viên duy nhất của hệ thống.",
        )

    updated = update_user_fields(user_id, {"is_active": False})
    if not updated:
        raise HTTPException(status_code=500, detail="Vô hiệu hóa tài khoản thất bại.")
    logger.info("[Admin] Disabled user %s (%s)", updated.email, updated.id)
    return _to_public(updated)


@router.post("/users/{user_id}/enable", response_model=UserPublic)
async def enable_user(user_id: str):
    """Enable a user account."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    updated = update_user_fields(user_id, {"is_active": True})
    if not updated:
        raise HTTPException(status_code=500, detail="Kích hoạt tài khoản thất bại.")
    logger.info("[Admin] Enabled user %s (%s)", updated.email, updated.id)
    return _to_public(updated)


@router.post("/users/{user_id}/make-admin", response_model=UserPublic)
async def make_admin(user_id: str):
    """Promote user to admin role."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    updated = update_user_fields(user_id, {"role": "admin"})
    if not updated:
        raise HTTPException(status_code=500, detail="Thăng cấp tài khoản thất bại.")
    logger.info("[Admin] Promoted user %s (%s) to admin", updated.email, updated.id)
    return _to_public(updated)


@router.post("/users/{user_id}/make-user", response_model=UserPublic)
async def make_user(user_id: str):
    """Demote admin to user role."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    if user.role == "admin" and user.is_active and count_active_admins() <= 1:
        raise HTTPException(
            status_code=400,
            detail="Không thể giáng chức quản trị viên duy nhất của hệ thống.",
        )

    updated = update_user_fields(user_id, {"role": "user"})
    if not updated:
        raise HTTPException(status_code=500, detail="Giáng chức tài khoản thất bại.")
    logger.info("[Admin] Demoted user %s (%s) to regular user", updated.email, updated.id)
    return _to_public(updated)


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user_account(user_id: str):
    """Delete a user account."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    if user.role == "admin" and user.is_active and count_active_admins() <= 1:
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa quản trị viên duy nhất của hệ thống.",
        )

    success = delete_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Xóa tài khoản thất bại.")
    logger.info("[Admin] Deleted user %s (%s)", user.email, user.id)
    return {"detail": "Đã xóa người dùng thành công."}


@router.post("/users/{user_id}/reset-password", response_model=UserPublic)
async def reset_user_password(user_id: str, req: AdminResetPasswordRequest):
    """Reset a user's password."""
    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy người dùng.")

    hashed = get_password_hash(req.new_password)
    updated = update_user_fields(user_id, {"password_hash": hashed})
    if not updated:
        raise HTTPException(status_code=500, detail="Đặt lại mật khẩu thất bại.")
    logger.info("[Admin] Reset password for user %s (%s)", updated.email, updated.id)
    return _to_public(updated)

"""User models and schemas."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class UserInDB(BaseModel):
    """User entity stored in database."""

    id: str
    email: str
    password_hash: str
    full_name: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login_at: Optional[datetime] = None
    # Personalization profile (see models/learning_profile.py). None until the user
    # completes onboarding or explicitly sets a mode in settings.
    learning_profile: Optional[dict[str, Any]] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class UserPublic(BaseModel):
    """Public user profile returned to client (never contains password_hash)."""

    id: str
    email: str
    full_name: Optional[str] = None
    role: str = "user"
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    learning_profile: Optional[dict[str, Any]] = None


class RegisterRequest(BaseModel):
    """Payload for POST /auth/register."""

    email: str
    password: str
    full_name: Optional[str] = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class LoginRequest(BaseModel):
    """Payload for POST /auth/login."""

    email: str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower() if isinstance(v, str) else v


class TokenResponse(BaseModel):
    """Payload returned upon successful login or registration."""

    access_token: str
    token_type: str = "bearer"
    user: UserPublic

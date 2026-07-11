"""SQLAlchemy model for one-time email verification/reset codes."""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.services.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class EmailOtpCode(Base):
    """Shared OTP table for both email-verification and password-reset codes,
    disambiguated by `purpose`."""

    __tablename__ = "email_otp_codes"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    # ondelete="CASCADE" is metadata only — see the identical note on Course.user_id
    # in app/models/course.py. Cascade cleanup for this table is done by hand in
    # app/routers/auth.py::delete_account.
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    purpose = Column(String, nullable=False)  # "verify_email" | "reset_password"
    code_hash = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    consumed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

"""SQLAlchemy Course model."""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text
from app.services.database import Base


def generate_uuid_12() -> str:
    """Generate a 12-character hex string ID."""
    return uuid.uuid4().hex[:12]


class Course(Base):
    __tablename__ = "courses"

    id = Column(String, primary_key=True, default=generate_uuid_12, index=True)
    user_id = Column(
        String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filenames = Column(JSON, nullable=True)  # List of uploaded filenames
    name = Column(String, nullable=True)  # AI-generated (or user-renamed) short course title
    status = Column(String, default="processing", nullable=False)
    stage = Column(String, default="extracting", nullable=False)
    progress = Column(Integer, default=30, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON encoded metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    chunk_count = Column(Integer, default=0, nullable=False)
    embedding_status = Column(String, default="pending", nullable=False)
    quality_score = Column(Integer, default=0, nullable=False)

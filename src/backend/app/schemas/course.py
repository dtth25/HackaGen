"""Pydantic schemas for Course models and Upload service."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    filenames: Optional[List[str]] = None
    metadata_json: Optional[str] = None


class CourseResponse(BaseModel):
    id: str
    user_id: str
    name: Optional[str] = None
    filenames: Optional[List[str]] = None
    status: str
    stage: str
    progress: int
    chunk_count: int = 0
    embedding_status: str = "pending"
    quality_score: int = 0
    created_at: Optional[datetime] = None
    metadata_json: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CourseListItem(BaseModel):
    course_id: str
    name: Optional[str] = None
    status: str
    filenames: List[str] = []
    file_count: int = 0
    created_at: Optional[datetime] = None
    error: Optional[str] = None
    name_pending: bool = False


class CourseListResponse(BaseModel):
    courses: List[CourseListItem]
    total: int


class CourseStatusResponse(BaseModel):
    course_id: str
    name: Optional[str] = None
    status: str
    stage: str = "completed"
    progress: int = 100
    chunk_count: int = 0
    embedding_status: str = "pending"
    quality_score: int = 0
    message: str = "Tài liệu đã sẵn sàng."
    filenames: List[str] = []
    file_count: int = 0
    error: Optional[str] = None
    name_pending: bool = False
    document_quality_report: Optional[Dict[str, Any]] = None


class CourseRenameRequest(BaseModel):
    name: str


class UploadResponse(BaseModel):
    course_id: str
    document_id: str
    filenames: List[str] = []
    file_count: int = 0
    status: str
    message: str

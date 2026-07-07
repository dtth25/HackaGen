"""Shared pytest fixtures and configuration for backend tests."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.models.course import Course  # noqa: F401
from app.models.user import User  # noqa: F401
from app.services.cache import cache
from app.services.database import Base, get_db
from main import app

import app.services.database as db_service

# Setup in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db_service.engine = engine
db_service.SessionLocal = TestingSessionLocal


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
_test_client = TestClient(app)

TEST_UPLOAD_DIR = "test_uploads_tmp"
settings.UPLOAD_DIR = TEST_UPLOAD_DIR


def _clean_upload_dir():
    os.makedirs(TEST_UPLOAD_DIR, exist_ok=True)
    for root, dirs, files in os.walk(TEST_UPLOAD_DIR, topdown=False):
        for name in files:
            try:
                os.remove(os.path.join(root, name))
            except Exception:
                pass
        for name in dirs:
            try:
                os.rmdir(os.path.join(root, name))
            except Exception:
                pass


@pytest.fixture(autouse=True)
def setup_database_and_storage():
    """Create tables before each test and drop them after, clean upload dir."""
    Base.metadata.create_all(bind=engine)
    cache._store.clear()
    _clean_upload_dir()
    yield
    Base.metadata.drop_all(bind=engine)
    _clean_upload_dir()



@pytest.fixture
def client():
    """Provide shared TestClient instance to test functions without importing conftest."""
    return _test_client


@pytest.fixture
def test_upload_dir():
    """Provide test upload directory path."""
    return TEST_UPLOAD_DIR

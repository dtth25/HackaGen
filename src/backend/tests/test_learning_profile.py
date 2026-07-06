"""
Test suite for the User Mode / Learning Profile system: model defaults, directive
builder, DB persistence, auth endpoints, and a regression guard against the
"silently dropped parameter" trap found with the old `learning_mode` field (it was
accepted by several generators but never actually reached the LLM prompt).
"""
import inspect

import pytest
from fastapi.testclient import TestClient

from backend import main
from backend.core import db as db_module
from backend.models.learning_profile import (
    ROLE_MODE_DEFAULTS,
    ROLE_MODE_LABELS_VI,
    ROLE_MODES,
    LearningProfile,
    resolve_profile_for_role,
)
from backend.models.user import UserInDB
from backend.services.learning_profile import build_profile_directives
from backend.services.resource_gen import ResourceGenerator


def test_role_modes_have_labels_and_defaults():
    for role in ROLE_MODES:
        assert role in ROLE_MODE_LABELS_VI
        assert ROLE_MODE_LABELS_VI[role].strip()
        assert role in ROLE_MODE_DEFAULTS


def test_resolve_profile_for_role_applies_curated_defaults():
    exam_prep = resolve_profile_for_role("exam_prep")
    assert exam_prep.role_mode == "exam_prep"
    assert exam_prep.learning_goal == "exam"
    assert exam_prep.preferred_output_style == "high_yield"

    researcher = resolve_profile_for_role("researcher")
    assert researcher.difficulty_level == "advanced"
    assert researcher.include_examples is False


def test_resolve_profile_for_role_overrides_only_set_fields():
    # Only difficulty_level is overridden; other exam_prep defaults must remain.
    profile = resolve_profile_for_role("exam_prep", {"difficulty_level": "advanced"})
    assert profile.difficulty_level == "advanced"
    assert profile.learning_goal == "exam"
    assert profile.preferred_output_style == "high_yield"


def test_learning_profile_model_defaults():
    profile = LearningProfile()
    assert profile.role_mode == "student"
    assert profile.include_examples is True
    assert profile.include_quiz is True


def test_build_profile_directives_empty_for_none():
    assert build_profile_directives(None) == ""
    assert build_profile_directives({}) == ""


@pytest.mark.parametrize("role", ROLE_MODES)
def test_build_profile_directives_includes_role_behavior(role):
    profile = resolve_profile_for_role(role).model_dump()
    directives = build_profile_directives(profile)
    assert directives  # non-empty
    assert "HỒ SƠ HỌC TẬP" in directives
    # Role-specific behavior keyword sanity checks (spot-check a distinctive phrase per role).
    role_markers = {
        "student": "SINH VIÊN",
        "exam_prep": "ÔN THI",
        "teacher": "GIẢNG VIÊN",
        "self_learner": "NGƯỜI TỰ HỌC",
        "developer": "LẬP TRÌNH",
        "enterprise_trainer": "ĐÀO TẠO NỘI BỘ",
        "researcher": "NGHIÊN CỨU",
    }
    assert role_markers[role] in directives


def test_build_profile_directives_respects_include_flags():
    profile = resolve_profile_for_role("student", {"include_examples": False, "include_common_mistakes": False}).model_dump()
    directives = build_profile_directives(profile)
    assert "KHÔNG cần thêm ví dụ" in directives
    assert "KHÔNG cần phần" in directives


# --- Regression guard: every generator must actually thread profile_directives into
# its prompt payload, not just accept-and-drop the parameter (the exact bug found
# with the old `learning_mode` field in 3 of 6 generators before this feature). ---

@pytest.mark.parametrize(
    "method_name",
    [
        "generate_book",
        "_generate_course_blueprint",
        "_generate_chapter_from_unit",
        "generate_slides_v2",
        "generate_quiz_v2",
        "generate_flashcards_v2",
        "generate_vid",
        "regenerate_mindmap",
    ],
)
def test_generator_source_references_profile_directives(method_name):
    source = inspect.getsource(getattr(ResourceGenerator, method_name))
    assert "profile_directives" in source, (
        f"{method_name} must build/forward profile_directives into its prompt payload, "
        "not just accept a `profile` param and silently drop it."
    )


def test_summary_fallbacks_accept_profile_and_scale_with_time_budget():
    gen = object.__new__(ResourceGenerator)
    gen.course_id = "profiletest"

    class FakeDoc:
        def __init__(self, text, cid):
            self.page_content = text
            self.metadata = {"chunk_id": cid}

    docs = [FakeDoc(f"Nội dung số {i} về học sâu và mạng nơ-ron nhân tạo trong xử lý dữ liệu.", f"chunk_{i}") for i in range(12)]

    short_profile = {"time_budget": "10_min"}
    long_profile = {"time_budget": "multi_day"}

    short_summary = gen.generate_fallback_summary("Tóm tắt", docs, profile=short_profile)
    long_summary = gen.generate_fallback_summary("Tóm tắt", docs, profile=long_profile)
    assert len(short_summary["main_points"]) < len(long_summary["main_points"])

    short_hy = gen.generate_fallback_high_yield("Trọng tâm", docs, profile=short_profile)
    long_hy = gen.generate_fallback_high_yield("Trọng tâm", docs, profile=long_profile)
    assert len(short_hy["core_ideas"]) < len(long_hy["core_ideas"])


# --- DB persistence ---

def test_db_learning_profile_round_trip(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_users.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db()

    from datetime import datetime
    import uuid
    from backend.core.security import get_password_hash

    user = UserInDB(
        id=str(uuid.uuid4()),
        email="profiletest@example.com",
        password_hash=get_password_hash("Password123"),
        full_name="Test User",
        role="user",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    created = db_module.create_user(user)
    assert created.learning_profile is None

    profile = resolve_profile_for_role("developer").model_dump()
    db_module.update_learning_profile(created.id, profile)

    fetched = db_module.get_user_by_id(created.id)
    assert fetched.learning_profile == profile
    assert fetched.learning_profile["role_mode"] == "developer"


# --- Auth endpoint ---

def test_learning_profile_endpoint_persists_and_reflects_in_me(monkeypatch, tmp_path):
    db_path = str(tmp_path / "test_users_api.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    db_module.init_db()

    client = TestClient(main.app)
    register_res = client.post(
        "/api/auth/register",
        json={"email": "profileapi@example.com", "password": "Password123", "full_name": "API Test"},
    )
    assert register_res.status_code == 201
    data = register_res.json()
    assert data["user"]["learning_profile"] is None
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    put_res = client.put(
        "/api/auth/me/learning-profile",
        json={"role_mode": "exam_prep"},
        headers=headers,
    )
    assert put_res.status_code == 200
    updated = put_res.json()
    assert updated["learning_profile"]["role_mode"] == "exam_prep"
    assert updated["learning_profile"]["learning_goal"] == "exam"
    assert updated["learning_profile"]["preferred_output_style"] == "high_yield"

    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["learning_profile"]["role_mode"] == "exam_prep"

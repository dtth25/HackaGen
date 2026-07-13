import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.models.course import Course
from app.services.database import SessionLocal
from app.services.generator import Generator
from app.services.versioning import (
    AtomicArtifactDirectory,
    GenerationInFlightError,
    VERSION_CAPS,
    VersionCapReachedError,
    artifact_file_path,
    migrate_legacy_artifact_metadata,
    remove_artifact_version,
    version_label,
    version_slug,
)


@pytest.mark.parametrize(
    ("artifact_type", "options", "expected_slug", "expected_label"),
    [
        ("book", {"detail_level": "Tóm tắt"}, "tom-tat", "Tóm tắt"),
        ("book", {"detail_level": "Tiêu chuẩn"}, "tieu-chuan", "Tiêu chuẩn"),
        ("book", {"detail_level": "Chuyên sâu"}, "chuyen-sau", "Chuyên sâu"),
        ("quiz", {"quantity": 10, "difficulty": "hard"}, "q10-hard", "10 câu - Khó"),
        ("vid", {"format": "shorts", "voice": "male"}, "shorts-male", "Shorts - Giọng nam"),
        ("slides", {}, "default", "Bản trình chiếu"),
    ],
)
def test_version_identity_and_label(artifact_type, options, expected_slug, expected_label):
    assert version_slug(artifact_type, options) == expected_slug
    assert version_label(artifact_type, options) == expected_label


def test_version_caps_match_product_contract():
    assert VERSION_CAPS == {"book": 3, "slides": 1, "quiz": 3, "vid": 3}


def test_legacy_path_uses_flat_artifact_directory(tmp_path):
    path = artifact_file_path(str(tmp_path), "course-1", "book", "legacy", "book.pdf")
    assert Path(path) == tmp_path / "course-1" / "artifacts" / "book.pdf"


def test_version_path_rejects_directory_traversal(tmp_path):
    with pytest.raises(ValueError):
        artifact_file_path(str(tmp_path), "course-1", "book", "../other", "book.pdf")
    with pytest.raises(ValueError):
        artifact_file_path(str(tmp_path), "course-1", "book", "tom-tat", "../book.pdf")


def test_remove_versioned_artifact_directory(tmp_path):
    artifact_dir = tmp_path / "course-1" / "artifacts" / "quiz" / "q10-hard"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "quiz.json").write_text("{}", encoding="utf-8")

    remove_artifact_version(str(tmp_path), "course-1", "quiz", "q10-hard")

    assert not artifact_dir.exists()


def test_remove_legacy_artifact_keeps_other_artifact_files(tmp_path):
    artifact_dir = tmp_path / "course-1" / "artifacts"
    artifact_dir.mkdir(parents=True)
    (artifact_dir / "book.json").write_text("{}", encoding="utf-8")
    (artifact_dir / "book.pdf").write_text("pdf", encoding="utf-8")
    (artifact_dir / "quiz.json").write_text("{}", encoding="utf-8")

    remove_artifact_version(str(tmp_path), "course-1", "book", "legacy")

    assert not (artifact_dir / "book.json").exists()
    assert not (artifact_dir / "book.pdf").exists()
    assert (artifact_dir / "quiz.json").exists()


def test_atomic_artifact_replace_preserves_old_version_until_commit(tmp_path):
    target = tmp_path / "book" / "tom-tat"
    target.mkdir(parents=True)
    (target / "book.json").write_text("old", encoding="utf-8")

    transaction = AtomicArtifactDirectory(str(target))
    staging = Path(transaction.prepare())
    (staging / "book.json").write_text("new", encoding="utf-8")

    transaction.abort()
    assert (target / "book.json").read_text(encoding="utf-8") == "old"

    staging = Path(transaction.prepare())
    (staging / "book.json").write_text("new", encoding="utf-8")
    transaction.commit()
    assert (target / "book.json").read_text(encoding="utf-8") == "new"
    assert not Path(f"{target}.tmp").exists()
    assert not Path(f"{target}.backup").exists()


def test_legacy_metadata_is_wrapped_without_losing_status_fields():
    metadata = {
        "study_pack": {
            "artifacts": {
                "book": {"status": "ready", "progress": 100, "quality_score": 92},
                "quiz": {"status": "error", "error": "timeout"},
            }
        }
    }

    migrated, changed = migrate_legacy_artifact_metadata(metadata)

    assert changed is True
    book = migrated["study_pack"]["artifacts"]["book"]
    assert book["active"] == "legacy"
    assert book["versions"]["legacy"]["path"] == "flat"
    assert book["versions"]["legacy"]["status"] == "ready"
    assert book["versions"]["legacy"]["quality_score"] == 92
    assert migrated["study_pack"]["artifacts"]["quiz"]["versions"]["legacy"]["error"] == "timeout"
    assert json.dumps(migrated, ensure_ascii=False)


def test_alembic_upgrade_wraps_legacy_artifact_metadata(tmp_path, monkeypatch):
    """Exercise the revision through Alembic, matching the container startup path."""
    database_url = f"sqlite:///{tmp_path / 'legacy.db'}"
    monkeypatch.setattr(settings, "DATABASE_URL", database_url)
    backend_dir = Path(__file__).resolve().parents[1]
    alembic_config = Config(str(backend_dir / "alembic.ini"))

    command.upgrade(alembic_config, "e5f6a7b8c9d0")
    engine = create_engine(database_url)
    legacy_metadata = {
        "study_pack": {
            "artifacts": {"vid": {"status": "ready", "progress": 100, "error": None}}
        }
    }
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO courses (
                    id, user_id, filenames, status, stage, progress, metadata_json,
                    created_at, is_deleted, chunk_count, embedding_status, quality_score,
                    embedding_provider
                ) VALUES (
                    'legacy-course', 'legacy-user', '[]', 'ready', 'completed', 100, :metadata,
                    '2026-07-13 00:00:00', 0, 1, 'completed', 88, 'gemini'
                )
                """
            ),
            {"metadata": json.dumps(legacy_metadata, ensure_ascii=False)},
        )

    command.upgrade(alembic_config, "head")
    with engine.connect() as connection:
        metadata = json.loads(
            connection.execute(
                text("SELECT metadata_json FROM courses WHERE id = 'legacy-course'")
            ).scalar_one()
        )

    vid = metadata["study_pack"]["artifacts"]["vid"]
    assert vid["active"] == "legacy"
    assert vid["versions"]["legacy"] == {
        "status": "ready",
        "progress": 100,
        "error": None,
        "options": {},
        "label": "Bản gốc",
        "topic": None,
        "user_prompt": "",
        "path": "flat",
    }


def test_version_cap_replace_and_in_flight_gate(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    course_id = "version-gate"
    db = SessionLocal()
    try:
        db.add(Course(id=course_id, user_id="version-user", status="ready"))
        db.commit()
    finally:
        db.close()

    generator = Generator(vector_store=None, llm=None)
    first = generator.prepare_artifact_version(course_id, "quiz", {"quantity": 5, "difficulty": "easy"})
    with pytest.raises(GenerationInFlightError):
        generator.prepare_artifact_version(course_id, "quiz", {"quantity": 10, "difficulty": "easy"})
    generator._set_artifact_status(course_id, "quiz", "ready", version_id=first)

    for quantity, difficulty in ((5, "medium"), (5, "hard")):
        version_id = generator.prepare_artifact_version(course_id, "quiz", {"quantity": quantity, "difficulty": difficulty})
        generator._set_artifact_status(course_id, "quiz", "ready", version_id=version_id)

    with pytest.raises(VersionCapReachedError) as cap_error:
        generator.prepare_artifact_version(course_id, "quiz", {"quantity": 10, "difficulty": "easy"})
    assert len(cap_error.value.versions) == 3

    replacement = generator.prepare_artifact_version(
        course_id,
        "quiz",
        {"quantity": 10, "difficulty": "easy"},
        replace_version_id=first,
    )
    victim_dir = tmp_path / course_id / "artifacts" / "quiz" / first
    victim_dir.mkdir(parents=True)
    (victim_dir / "quiz.json").write_text("{}", encoding="utf-8")
    generator._set_artifact_status(course_id, "quiz", "ready", version_id=replacement)
    active, versions = generator.artifact_versions(course_id, "quiz")
    assert active == "q10-easy"
    assert {version["version_id"] for version in versions} == {"q5-medium", "q5-hard", "q10-easy"}
    assert not victim_dir.exists()

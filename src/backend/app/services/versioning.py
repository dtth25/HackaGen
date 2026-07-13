"""Versioned artifact storage and metadata helpers.

The generator and API both use these helpers so a version id means the same thing in
metadata and on disk. Legacy artifacts remain in the original flat directory and are
represented by the reserved ``legacy`` version id.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, Mapping

LEGACY_VERSION_ID = "legacy"

VERSION_CAPS = {
    "book": 3,
    "slides": 1,
    "quiz": 3,
    "vid": 3,
}

_BOOK_SLUGS = {
    "Tóm tắt": "tom-tat",
    "Tiêu chuẩn": "tieu-chuan",
    "Chuyên sâu": "chuyen-sau",
}
_QUIZ_DIFFICULTY_LABELS = {
    "easy": "Dễ",
    "medium": "Vừa",
    "hard": "Khó",
    "mixed": "Trộn",
}
_VID_FORMAT_LABELS = {
    "shorts": "Shorts",
    "overview": "Tổng quan",
    "standard": "Tiêu chuẩn",
}
_VID_VOICE_LABELS = {"female": "Giọng nữ", "male": "Giọng nam"}


class VersioningError(Exception):
    """Base exception for generation version selection."""


class GenerationInFlightError(VersioningError):
    """Another version of this artifact is already generating."""


class VersionCapReachedError(VersioningError):
    """A new option combination needs an explicit victim version."""

    def __init__(self, versions: list[Dict[str, Any]]):
        super().__init__("version_cap_reached")
        self.versions = versions


def _require_artifact_type(artifact_type: str) -> None:
    if artifact_type not in VERSION_CAPS:
        raise ValueError(f"Unsupported artifact type: {artifact_type}")


def _safe_version_id(version_id: str) -> str:
    if not version_id or Path(version_id).name != version_id or version_id in {".", ".."}:
        raise ValueError("Invalid artifact version id")
    return version_id


def version_slug(artifact_type: str, options: Mapping[str, Any]) -> str:
    """Return the stable identity for an artifact option combination."""
    _require_artifact_type(artifact_type)

    if artifact_type == "book":
        detail_level = str(options.get("detail_level", ""))
        try:
            return _BOOK_SLUGS[detail_level]
        except KeyError as exc:
            raise ValueError(f"Unsupported book detail level: {detail_level}") from exc

    if artifact_type == "slides":
        return "default"

    if artifact_type == "quiz":
        quantity = options.get("quantity")
        difficulty = str(options.get("difficulty", "")).lower()
        if not isinstance(quantity, int) or quantity <= 0:
            raise ValueError("Quiz quantity must be a positive integer")
        if difficulty not in _QUIZ_DIFFICULTY_LABELS:
            raise ValueError(f"Unsupported quiz difficulty: {difficulty}")
        return f"q{quantity}-{difficulty}"

    fmt = str(options.get("format", "")).lower()
    voice = str(options.get("voice", "")).lower()
    if fmt not in _VID_FORMAT_LABELS or voice not in _VID_VOICE_LABELS:
        raise ValueError("Unsupported video format or voice")
    return f"{fmt}-{voice}"


def version_label(artifact_type: str, options: Mapping[str, Any]) -> str:
    """Return the short label shown in the version switcher."""
    _require_artifact_type(artifact_type)
    if artifact_type == "book":
        detail_level = str(options.get("detail_level", ""))
        if detail_level not in _BOOK_SLUGS:
            raise ValueError(f"Unsupported book detail level: {detail_level}")
        return detail_level
    if artifact_type == "slides":
        return "Bản trình chiếu"
    if artifact_type == "quiz":
        quantity = options.get("quantity")
        difficulty = str(options.get("difficulty", "")).lower()
        version_slug(artifact_type, options)
        return f"{quantity} câu - {_QUIZ_DIFFICULTY_LABELS[difficulty]}"

    fmt = str(options.get("format", "")).lower()
    voice = str(options.get("voice", "")).lower()
    version_slug(artifact_type, options)
    return f"{_VID_FORMAT_LABELS[fmt]} - {_VID_VOICE_LABELS[voice]}"


def artifact_directory_path(
    upload_dir: str, course_id: str, artifact_type: str, version_id: str
) -> str:
    """Resolve the on-disk directory for a version without creating it."""
    _require_artifact_type(artifact_type)
    version_id = _safe_version_id(version_id)
    root = Path(upload_dir) / course_id / "artifacts"
    if version_id == LEGACY_VERSION_ID:
        return str(root)
    return str(root / artifact_type / version_id)


def artifact_file_path(
    upload_dir: str,
    course_id: str,
    artifact_type: str,
    version_id: str,
    filename: str,
) -> str:
    """Resolve a file inside a selected artifact version safely."""
    if Path(filename).name != filename:
        raise ValueError("Artifact filename must not contain a directory")
    return str(Path(artifact_directory_path(upload_dir, course_id, artifact_type, version_id)) / filename)


class AtomicArtifactDirectory:
    """Stage an artifact version in ``.tmp`` and atomically promote it when complete.

    Failed generation only removes the staging directory, so the currently served
    version remains intact. Windows cannot replace a non-empty directory directly;
    a short-lived backup allows rollback if the final rename itself fails.
    """

    def __init__(self, target_dir: str):
        self.target_dir = Path(target_dir)
        self.temp_dir = Path(f"{target_dir}.tmp")
        self.backup_dir = Path(f"{target_dir}.backup")

    def prepare(self) -> str:
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return str(self.temp_dir)

    def abort(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def commit(self) -> str:
        if not self.temp_dir.is_dir():
            raise FileNotFoundError(f"Artifact staging directory is missing: {self.temp_dir}")

        self.target_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(self.backup_dir, ignore_errors=True)
        moved_old = False
        try:
            if self.target_dir.exists():
                os.replace(self.target_dir, self.backup_dir)
                moved_old = True
            os.replace(self.temp_dir, self.target_dir)
        except Exception:
            if moved_old and not self.target_dir.exists() and self.backup_dir.exists():
                os.replace(self.backup_dir, self.target_dir)
            raise
        finally:
            if self.target_dir.exists():
                shutil.rmtree(self.backup_dir, ignore_errors=True)
        return str(self.target_dir)


def legacy_version_entry(entry: Mapping[str, Any]) -> Dict[str, Any]:
    """Preserve an old flat metadata entry as a version without changing its fields."""
    version = dict(entry)
    version.update(
        {
            "options": {},
            "label": "Bản gốc",
            "topic": version.get("topic"),
            "user_prompt": version.get("user_prompt", ""),
            "path": "flat",
        }
    )
    return version


def migrate_legacy_artifact_metadata(metadata: Mapping[str, Any]) -> tuple[Dict[str, Any], bool]:
    """Wrap legacy flat artifact entries in the version metadata shape.

    This intentionally does not create entries for never-generated artifacts and does
    not move files; the migration must be safe for the shared legacy artifact directory.
    """
    result = dict(metadata)
    study_pack = result.get("study_pack")
    if not isinstance(study_pack, Mapping):
        return result, False
    study_pack = dict(study_pack)
    artifacts = study_pack.get("artifacts")
    if not isinstance(artifacts, Mapping):
        return result, False

    changed = False
    migrated_artifacts = dict(artifacts)
    for artifact_type in VERSION_CAPS:
        entry = migrated_artifacts.get(artifact_type)
        if not isinstance(entry, Mapping) or "versions" in entry:
            continue
        migrated_artifacts[artifact_type] = {
            "active": LEGACY_VERSION_ID,
            "versions": {LEGACY_VERSION_ID: legacy_version_entry(entry)},
        }
        changed = True

    if changed:
        study_pack["artifacts"] = migrated_artifacts
        result["study_pack"] = study_pack
    return result, changed

"""wrap legacy artifact metadata in version entries

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-13 14:00:00.000000

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ARTIFACT_TYPES = ("book", "slides", "quiz", "vid")


def _migrate_metadata(metadata: object) -> tuple[object, bool]:
    if not isinstance(metadata, dict):
        return metadata, False
    study_pack = metadata.get("study_pack")
    if not isinstance(study_pack, dict):
        return metadata, False
    artifacts = study_pack.get("artifacts")
    if not isinstance(artifacts, dict):
        return metadata, False

    changed = False
    for artifact_type in _ARTIFACT_TYPES:
        entry = artifacts.get(artifact_type)
        if not isinstance(entry, dict) or "versions" in entry:
            continue
        legacy = dict(entry)
        legacy.update(
            {
                "options": {},
                "label": "Bản gốc",
                "topic": legacy.get("topic"),
                "user_prompt": legacy.get("user_prompt", ""),
                "path": "flat",
            }
        )
        artifacts[artifact_type] = {"active": "legacy", "versions": {"legacy": legacy}}
        changed = True
    return metadata, changed


def upgrade() -> None:
    """Migrate metadata only; old files remain in their shared flat directory."""
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, metadata_json FROM courses")).mappings()
    for row in rows:
        raw_metadata = row["metadata_json"]
        if not raw_metadata:
            continue
        try:
            metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
        except (TypeError, json.JSONDecodeError):
            continue
        migrated, changed = _migrate_metadata(metadata)
        if changed:
            bind.execute(
                sa.text("UPDATE courses SET metadata_json = :metadata WHERE id = :id"),
                {"metadata": json.dumps(migrated, ensure_ascii=False), "id": row["id"]},
            )


def downgrade() -> None:
    """Metadata shape is backward compatible enough to leave in place on downgrade."""

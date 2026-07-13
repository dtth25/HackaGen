"""remove deprecated regeneration metadata

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, metadata_json FROM courses")).mappings()
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        study_pack = metadata.get("study_pack")
        if not isinstance(study_pack, dict) or "regen_counts" not in study_pack:
            continue
        study_pack.pop("regen_counts", None)
        bind.execute(
            sa.text("UPDATE courses SET metadata_json = :metadata WHERE id = :id"),
            {"metadata": json.dumps(metadata, ensure_ascii=False), "id": row["id"]},
        )


def downgrade() -> None:
    pass

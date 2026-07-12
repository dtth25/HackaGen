"""add course embedding_provider field

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-12 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('embedding_provider', sa.String(), nullable=False, server_default='gemini')
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('embedding_provider')

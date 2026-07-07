"""add vector and processing fields

Revision ID: a1b2c3d4e5f6
Revises: 928f14bcd08c
Create Date: 2026-07-07 21:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '928f14bcd08c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('chunk_count', sa.Integer(), nullable=False, server_default='0'))
        batch_op.add_column(sa.Column('embedding_status', sa.String(length=50), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('quality_score', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('quality_score')
        batch_op.drop_column('embedding_status')
        batch_op.drop_column('chunk_count')

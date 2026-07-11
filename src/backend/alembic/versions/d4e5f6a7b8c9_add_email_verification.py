"""add email verification (is_verified + email_otp_codes)

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-11 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        # server_default backfills existing (pre-verification-era) accounts as
        # verified so this migration doesn't lock anyone out; new inserts
        # always pass is_verified explicitly (register=False, admin seed=True).
        batch_op.add_column(sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.true()))

    op.create_table(
        'email_otp_codes',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('code_hash', sa.String(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('consumed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_email_otp_codes_id'), 'email_otp_codes', ['id'], unique=False)
    op.create_index(op.f('ix_email_otp_codes_user_id'), 'email_otp_codes', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_email_otp_codes_user_id'), table_name='email_otp_codes')
    op.drop_index(op.f('ix_email_otp_codes_id'), table_name='email_otp_codes')
    op.drop_table('email_otp_codes')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_verified')

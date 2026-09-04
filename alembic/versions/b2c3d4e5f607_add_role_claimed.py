"""add_role_claimed

Adds a `role_claimed` flag to users so the first session can self-declare
teacher/parent/student exactly once (Clerk sign-ups default to student).

Revision ID: b2c3d4e5f607
Revises: a1b2c3d4e5f6
Create Date: 2026-09-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f607'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('users')}
    if 'role_claimed' not in columns:
        op.add_column(
            'users', sa.Column('role_claimed', sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('users')}
    if 'role_claimed' in columns:
        op.drop_column('users', 'role_claimed')

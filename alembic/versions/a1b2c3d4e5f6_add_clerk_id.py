"""add_clerk_id

Adds a nullable unique `clerk_id` column to the users table so Clerk
session subjects can be mapped onto existing local user rows (with an
email-match fallback for pre-Clerk accounts).

Revision ID: a1b2c3d4e5f6
Revises: 8f9a0b1c2d3e
Create Date: 2026-09-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '8f9a0b1c2d3e'


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('users')}
    if 'clerk_id' not in columns:
        op.add_column('users', sa.Column('clerk_id', sa.String(255), nullable=True))
        op.create_unique_constraint('uq_users_clerk_id', 'users', ['clerk_id'])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('users')}
    if 'clerk_id' in columns:
        op.drop_constraint('uq_users_clerk_id', 'users', type_='unique')
        op.drop_column('users', 'clerk_id')

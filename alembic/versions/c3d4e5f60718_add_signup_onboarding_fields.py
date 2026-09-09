"""add_signup_onboarding_fields

Adds role-first signup + onboarding fields to users (ADR-0013):
- date_of_birth: learner DOB collected before account creation (Khan-style flow)
- tos_accepted_at: Terms of Service acceptance timestamp
- parent_email: consent contact for under-13 learners
- onboarding_completed_at: profile completion (grade/subject) timestamp

Revision ID: c3d4e5f60718
Revises: b2c3d4e5f607
Create Date: 2026-09-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f60718'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f607'


_NEW_COLUMNS = ('date_of_birth', 'tos_accepted_at', 'parent_email', 'onboarding_completed_at')


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('users')}
    if 'date_of_birth' not in columns:
        op.add_column('users', sa.Column('date_of_birth', sa.Date(), nullable=True))
    if 'tos_accepted_at' not in columns:
        op.add_column('users', sa.Column('tos_accepted_at', sa.DateTime(timezone=True), nullable=True))
    if 'parent_email' not in columns:
        op.add_column('users', sa.Column('parent_email', sa.String(255), nullable=True))
    if 'onboarding_completed_at' not in columns:
        op.add_column('users', sa.Column('onboarding_completed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = {c['name'] for c in inspector.get_columns('users')}
    for name in _NEW_COLUMNS:
        if name in columns:
            op.drop_column('users', name)

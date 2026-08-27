"""add_subject_columns

Adds a nullable `subject` column to the user, profile, mastery, progress,
ability and quiz tables so the multi-subject (biology/chemistry/physics/
mathematics) feature can scope content and learning analytics per subject.

Revision ID: 8f9a0b1c2d3e
Revises: 7e8f9a0b1c2d
Create Date: 2026-08-27

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = '8f9a0b1c2d3e'
down_revision: Union[str, Sequence[str], None] = '7e8f9a0b1c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SUBJECT_COLUMNS = {
    "users": "subject",
    "student_profiles": "subject",
    "student_mastery": "subject",
    "progress_records": "subject",
    "student_abilities": "subject",
    "quizzes": "subject",
}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {
        table: {c["name"] for c in inspector.get_columns(table)}
        for table in _SUBJECT_COLUMNS
    }
    for table, column in _SUBJECT_COLUMNS.items():
        if column not in existing.get(table, set()):
            op.add_column(table, sa.Column(column, sa.String(length=20), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    for table, column in _SUBJECT_COLUMNS.items():
        op.drop_column(table, column)

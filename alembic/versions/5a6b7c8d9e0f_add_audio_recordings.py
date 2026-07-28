"""add_audio_recordings

Revision ID: 5a6b7c8d9e0f
Revises: 4f5a6b7c8d9e
Create Date: 2026-07-28 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "5a6b7c8d9e0f"
down_revision: Union[str, Sequence[str], None] = "4f5a6b7c8d9e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audio_recordings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True, index=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("memory_sessions.session_id"), nullable=True),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("transcript", sa.Text, nullable=False, server_default=sa.text("''")),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default=sa.text("0.0")),
        sa.Column("mime_type", sa.String(50), nullable=False, server_default=sa.text("'audio/ogg'")),
        sa.Column("file_size_bytes", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("language", sa.String(10), nullable=False, server_default=sa.text("'am'")),
        sa.Column("direction", sa.String(10), nullable=False, server_default=sa.text("'user'")),
        sa.Column("modality", sa.String(20), nullable=False, server_default=sa.text("'voice'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"), index=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audio_recordings")

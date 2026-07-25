"""add_memory_entities

Revision ID: 4f5a6b7c8d9e
Revises: 3a1b2c3d4e5f
Create Date: 2026-07-25 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "4f5a6b7c8d9e"
down_revision: Union[str, Sequence[str], None] = "3a1b2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "memory_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("entity_text", sa.String(300), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("mention_count", sa.Integer, nullable=False, server_default=sa.text("1")),
        sa.Column("first_mentioned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_mentioned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("sessions_seen", postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=True),
        sa.Column("extra_data", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("idx_memory_entities_user_text", "memory_entities", ["user_id", "entity_text"])
    op.create_index("idx_memory_entities_type", "memory_entities", ["entity_type"])
    op.create_index("idx_memory_entities_user_type", "memory_entities", ["user_id", "entity_type"])


def downgrade() -> None:
    op.drop_index("idx_memory_entities_user_type", table_name="memory_entities")
    op.drop_index("idx_memory_entities_type", table_name="memory_entities")
    op.drop_index("idx_memory_entities_user_text", table_name="memory_entities")
    op.drop_table("memory_entities")

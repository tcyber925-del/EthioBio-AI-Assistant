"""add_knowledge_embeddings

Revision ID: 20b5775ced9f
Revises: 4caa1c152f1c
Create Date: 2026-07-11 20:47:24.747798

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20b5775ced9f'
down_revision: Union[str, Sequence[str], None] = '4caa1c152f1c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('knowledge_embeddings',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('knowledge_object_id', sa.Uuid(), nullable=True),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', sa.ARRAY(sa.Float()), nullable=True),
    sa.Column('metadata', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['knowledge_object_id'], ['knowledge_objects.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('knowledge_embeddings')

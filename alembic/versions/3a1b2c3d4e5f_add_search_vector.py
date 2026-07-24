"""add_search_vector

Revision ID: 3a1b2c3d4e5f
Revises: 20b5775ced9f
Create Date: 2026-07-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '20b5775ced9f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'conversation_turns',
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR,
            sa.Computed(
                "to_tsvector('english', coalesce(content, ''))",
                persisted=False,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        'idx_conversation_turns_search',
        'conversation_turns',
        ['search_vector'],
        postgresql_using='gin',
    )

    op.add_column(
        'memory_educational_summaries',
        sa.Column(
            'search_vector',
            postgresql.TSVECTOR,
            sa.Computed(
                "to_tsvector('english', "
                "coalesce(next_learning_goal, '') || ' ' || coalesce(topic, '')"
                ")",
                persisted=False,
            ),
            nullable=True,
        ),
    )
    op.create_index(
        'idx_memory_summaries_search',
        'memory_educational_summaries',
        ['search_vector'],
        postgresql_using='gin',
    )


def downgrade() -> None:
    op.drop_index('idx_memory_summaries_search', table_name='memory_educational_summaries')
    op.drop_column('memory_educational_summaries', 'search_vector')
    op.drop_index('idx_conversation_turns_search', table_name='conversation_turns')
    op.drop_column('conversation_turns', 'search_vector')

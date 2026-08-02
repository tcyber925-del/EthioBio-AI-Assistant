"""ensure_search_vector_columns

Adds the generated `search_vector` columns and GIN indexes that the
`3a1b2c3d4e5f` migration was supposed to create but never actually applied
to some databases (alembic_version was stamped past it without the DDL
running). Safe to run even when the columns already exist.

Revision ID: 6a1b2c3d4e5f
Revises: 5a6b7c8d9e0f
Create Date: 2026-08-02

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6a1b2c3d4e5f'
down_revision: Union[str, Sequence[str], None] = '5a6b7c8d9e0f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'conversation_turns' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE conversation_turns
                    ADD COLUMN search_vector tsvector
                    GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_conversation_turns_search
        ON conversation_turns USING gin (search_vector)
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'memory_educational_summaries' AND column_name = 'search_vector'
            ) THEN
                ALTER TABLE memory_educational_summaries
                    ADD COLUMN search_vector tsvector
                    GENERATED ALWAYS AS (
                        to_tsvector('english', coalesce(next_learning_goal, '') || ' ' || coalesce(topic, ''))
                    ) STORED;
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_memory_summaries_search
        ON memory_educational_summaries USING gin (search_vector)
        """
    )


def downgrade() -> None:
    op.drop_index('idx_memory_summaries_search', table_name='memory_educational_summaries')
    op.drop_column('memory_educational_summaries', 'search_vector')
    op.drop_index('idx_conversation_turns_search', table_name='conversation_turns')
    op.drop_column('conversation_turns', 'search_vector')

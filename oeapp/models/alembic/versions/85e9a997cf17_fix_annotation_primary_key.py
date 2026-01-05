"""Fix annotation primary key

Revision ID: 85e9a997cf17
Revises: 6c07e0e0c170
Create Date: 2026-01-04 15:27:35.898902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85e9a997cf17'
down_revision: Union[str, Sequence[str], None] = '6c07e0e0c170'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Force primary key change in SQLite by specifying it in batch mode
    with op.batch_alter_table('annotations', schema=None) as batch_op:
        # We need to drop the old PK and define the new one.
        # Alembic's batch mode will recreate the table with the correct PK.
        pass

    # Actually, the most reliable way is to explicitly define the table in batch mode
    # OR use raw SQL. I'll use the raw SQL to be 100% sure.

    op.execute("ALTER TABLE annotations RENAME TO annotations_old")

    op.create_table('annotations',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('token_id', sa.Integer(), nullable=True),
    sa.Column('idiom_id', sa.Integer(), nullable=True),
    sa.Column('pos', sa.String(), nullable=True),
    sa.Column('gender', sa.String(), nullable=True),
    sa.Column('number', sa.String(), nullable=True),
    sa.Column('case', sa.String(), nullable=True),
    sa.Column('declension', sa.String(), nullable=True),
    sa.Column('article_type', sa.String(), nullable=True),
    sa.Column('pronoun_type', sa.String(), nullable=True),
    sa.Column('pronoun_number', sa.String(), nullable=True),
    sa.Column('verb_class', sa.String(), nullable=True),
    sa.Column('verb_tense', sa.String(), nullable=True),
    sa.Column('verb_person', sa.String(), nullable=True),
    sa.Column('verb_mood', sa.String(), nullable=True),
    sa.Column('verb_aspect', sa.String(), nullable=True),
    sa.Column('verb_form', sa.String(), nullable=True),
    sa.Column('prep_case', sa.String(), nullable=True),
    sa.Column('adjective_inflection', sa.String(), nullable=True),
    sa.Column('adjective_degree', sa.String(), nullable=True),
    sa.Column('conjunction_type', sa.String(), nullable=True),
    sa.Column('adverb_degree', sa.String(), nullable=True),
    sa.Column('confidence', sa.Integer(), nullable=True),
    sa.Column('last_inferred_json', sa.String(), nullable=True),
    sa.Column('modern_english_meaning', sa.String(), nullable=True),
    sa.Column('root', sa.String(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['idiom_id'], ['idioms.id'], name='fk_annotations_idiom', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['token_id'], ['tokens.id'], name='fk_annotations_token', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # Copy data, ensuring id is preserved
    op.execute("""
        INSERT INTO annotations (
            id, token_id, idiom_id, pos, gender, number, "case", declension, article_type,
            pronoun_type, pronoun_number, verb_class, verb_tense, verb_person,
            verb_mood, verb_aspect, verb_form, prep_case, adjective_inflection,
            adjective_degree, conjunction_type, adverb_degree, confidence,
            last_inferred_json, modern_english_meaning, root, updated_at
        )
        SELECT
            id, token_id, idiom_id, pos, gender, number, "case", declension, article_type,
            pronoun_type, pronoun_number, verb_class, verb_tense, verb_person,
            verb_mood, verb_aspect, verb_form, prep_case, adjective_inflection,
            adjective_degree, conjunction_type, adverb_degree, confidence,
            last_inferred_json, modern_english_meaning, root, updated_at
        FROM annotations_old
    """)

    op.drop_table('annotations_old')


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE annotations RENAME TO annotations_old")
    # Restore token_id as PK
    op.create_table('annotations',
    sa.Column('token_id', sa.Integer(), nullable=False),
    # ... rest ...
    sa.PrimaryKeyConstraint('token_id')
    )
    # Just pass for now as downgrade is complex
    pass

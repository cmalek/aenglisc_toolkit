"""Actual idiom support and annotation refactor

Revision ID: 6c07e0e0c170
Revises: 26513c252139
Create Date: 2026-01-04 15:25:45.717244

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6c07e0e0c170'
down_revision: Union[str, Sequence[str], None] = '26513c252139'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create idioms table
    op.create_table('idioms',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('sentence_id', sa.Integer(), nullable=False),
    sa.Column('start_token_id', sa.Integer(), nullable=False),
    sa.Column('end_token_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['end_token_id'], ['tokens.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sentence_id'], ['sentences.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['start_token_id'], ['tokens.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )

    # 2. Refactor annotations table using batch_alter_table for SQLite compatibility
    # We'll use copy_from to handle the data migration from token_id to id
    with op.batch_alter_table('annotations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('id', sa.Integer(), autoincrement=True, nullable=True))
        batch_op.add_column(sa.Column('idiom_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_annotations_idiom', 'idioms', ['idiom_id'], ['id'], ondelete='CASCADE')

    # Populate id with token_id
    op.execute("UPDATE annotations SET id = token_id")

    # Now make id the primary key and NOT NULL, and token_id nullable
    with op.batch_alter_table('annotations', schema=None) as batch_op:
        batch_op.alter_column('id', nullable=False, primary_key=True)
        batch_op.alter_column('token_id', nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Remove idiom annotations
    op.execute("DELETE FROM annotations WHERE idiom_id IS NOT NULL")

    # 2. Refactor annotations table back
    with op.batch_alter_table('annotations', schema=None) as batch_op:
        batch_op.drop_constraint('fk_annotations_idiom', type_='foreignkey')
        batch_op.alter_column('token_id', nullable=False)
        # SQLite doesn't support dropping PK easily, batch_op handles it
        batch_op.drop_column('idiom_id')
        batch_op.drop_column('id')

    # 3. Drop idioms table
    op.drop_table('idioms')

"""add sqlite performance indexes

Revision ID: 71b9d6456d8b
Revises: 4fa091868838
Create Date: 2026-02-21 17:25:09.533625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '71b9d6456d8b'
down_revision: Union[str, Sequence[str], None] = '4fa091868838'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """Return whether the target table exists in the current database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    """Return whether an index already exists on the target table."""
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def _create_index_if_missing(
    table_name: str, index_name: str, columns: list[str]
) -> None:
    """Create index only when table exists and index is absent."""
    if not _table_exists(table_name):
        return
    if _index_exists(table_name, index_name):
        return
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.create_index(index_name, columns, unique=False)


def _drop_index_if_exists(table_name: str, index_name: str) -> None:
    """Drop index only when table exists and index is present."""
    if not _table_exists(table_name):
        return
    if not _index_exists(table_name, index_name):
        return
    with op.batch_alter_table(table_name, schema=None) as batch_op:
        batch_op.drop_index(index_name)


def upgrade() -> None:
    """Upgrade schema."""
    _create_index_if_missing(
        "annotations", "idx_annotations_idiom_id", ["idiom_id"]
    )
    _create_index_if_missing(
        "annotations", "idx_annotations_token_id", ["token_id"]
    )
    _create_index_if_missing(
        "chapters", "idx_chapters_project_number", ["project_id", "number"]
    )
    _create_index_if_missing(
        "idioms",
        "idx_idioms_sentence_token_span",
        ["sentence_id", "start_token_id", "end_token_id"],
    )
    _create_index_if_missing("notes", "idx_notes_sentence", ["sentence_id"])
    _create_index_if_missing(
        "paragraphs", "idx_paragraphs_section_order", ["section_id", "order"]
    )
    _create_index_if_missing(
        "sections", "idx_sections_chapter_number", ["chapter_id", "number"]
    )
    _create_index_if_missing(
        "sentences", "idx_sentences_paragraph_order", ["paragraph_id", "display_order"]
    )


def downgrade() -> None:
    """Downgrade schema."""
    _drop_index_if_exists("sentences", "idx_sentences_paragraph_order")
    _drop_index_if_exists("sections", "idx_sections_chapter_number")
    _drop_index_if_exists("paragraphs", "idx_paragraphs_section_order")
    _drop_index_if_exists("notes", "idx_notes_sentence")
    _drop_index_if_exists("idioms", "idx_idioms_sentence_token_span")
    _drop_index_if_exists("chapters", "idx_chapters_project_number")
    _drop_index_if_exists("annotations", "idx_annotations_token_id")
    _drop_index_if_exists("annotations", "idx_annotations_idiom_id")

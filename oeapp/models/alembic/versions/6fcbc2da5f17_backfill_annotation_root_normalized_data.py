"""backfill annotation root_normalized data

Revision ID: 6fcbc2da5f17
Revises: d6d8b613bc53
Create Date: 2026-02-26 13:15:46.562494

"""
from typing import Sequence, Union
import re
import unicodedata

from alembic import op
import sqlalchemy as sa


#: revision identifiers, used by Alembic.
revision: str = '6fcbc2da5f17'
#: Down revision.
down_revision: Union[str, Sequence[str], None] = 'd6d8b613bc53'
#: Branch labels.
branch_labels: Union[str, Sequence[str], None] = None
#: Depends on.
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(table_name: str) -> bool:
    """
    Return whether the target table exists in the current database.

    Args:
        table_name: Table name.

    Returns:
        The computed value.
    """
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    """
    Return whether the target column exists on the given table.

    Args:
        table_name: Table name.
        column_name: Column name.

    Returns:
        The computed value.
    """
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def _normalize_old_english(text: str | None) -> str | None:
    """
    Normalize root text for stable grouping and lookup.

    Args:
        text: Raw root text.

    Returns:
        Normalized text.

    """
    if text is None:
        return None
    lowered = text.strip().lower().replace("ð", "þ")
    decomposed = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    )
    stripped_hyphen = re.sub(r"(?<=\S)[-–—](?=\S)", "", without_marks)
    return unicodedata.normalize("NFC", stripped_hyphen)


def _backfill_annotation_roots() -> None:
    """
    Populate annotations.root_normalized for all existing annotation rows.
    """
    if not _table_exists("annotations"):
        return
    if not _column_exists("annotations", "root"):
        return
    if not _column_exists("annotations", "root_normalized"):
        return
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, root FROM annotations")).fetchall()
    for row in rows:
        bind.execute(
            sa.text(
                "UPDATE annotations "
                "SET root_normalized = :root_normalized "
                "WHERE id = :annotation_id"
            ),
            {
                "annotation_id": row.id,
                "root_normalized": _normalize_old_english(row.root),
            },
        )


def upgrade() -> None:
    """Backfill normalized root values for existing annotations."""
    _backfill_annotation_roots()


def downgrade() -> None:
    """No-op downgrade for data backfill migration."""

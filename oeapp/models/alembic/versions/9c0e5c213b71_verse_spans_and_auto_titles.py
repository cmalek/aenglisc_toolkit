"""
add verse spans and auto-title flags

Revision ID: 9c0e5c213b71
Revises: 6fcbc2da5f17
Create Date: 2026-03-02 14:25:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c0e5c213b71"
down_revision: str | Sequence[str] | None = "6fcbc2da5f17"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    """Return whether the target table exists in the current database."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    """Return whether the target column exists on the given table."""
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    """Upgrade schema."""
    if _table_exists("sentences"):
        with op.batch_alter_table("sentences", schema=None) as batch_op:
            if not _column_exists("sentences", "verse_line_start"):
                batch_op.add_column(
                    sa.Column("verse_line_start", sa.Integer(), nullable=True)
                )
            if not _column_exists("sentences", "verse_line_end"):
                batch_op.add_column(
                    sa.Column("verse_line_end", sa.Integer(), nullable=True)
                )

    if _table_exists("chapters") and not _column_exists("chapters", "title_auto"):
        with op.batch_alter_table("chapters", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "title_auto",
                    sa.Boolean(),
                    server_default=sa.text("0"),
                    nullable=False,
                )
            )

    if _table_exists("sections") and not _column_exists("sections", "title_auto"):
        with op.batch_alter_table("sections", schema=None) as batch_op:
            batch_op.add_column(
                sa.Column(
                    "title_auto",
                    sa.Boolean(),
                    server_default=sa.text("0"),
                    nullable=False,
                )
            )


def downgrade() -> None:
    """Downgrade schema."""
    if _table_exists("sections") and _column_exists("sections", "title_auto"):
        with op.batch_alter_table("sections", schema=None) as batch_op:
            batch_op.drop_column("title_auto")

    if _table_exists("chapters") and _column_exists("chapters", "title_auto"):
        with op.batch_alter_table("chapters", schema=None) as batch_op:
            batch_op.drop_column("title_auto")

    if _table_exists("sentences"):
        with op.batch_alter_table("sentences", schema=None) as batch_op:
            if _column_exists("sentences", "verse_line_end"):
                batch_op.drop_column("verse_line_end")
            if _column_exists("sentences", "verse_line_start"):
                batch_op.drop_column("verse_line_start")

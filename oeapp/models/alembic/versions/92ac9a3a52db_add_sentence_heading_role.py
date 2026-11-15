"""
Add sentence heading role

Revision ID: 92ac9a3a52db
Revises: 7cd945e38aff
Create Date: 2026-11-14 17:15:53.226726

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
#: The Alembic revision identifier.
revision: str = "92ac9a3a52db"
#: The revision this one follows.
down_revision: str | Sequence[str] | None = "7cd945e38aff"
#: Alembic branch labels.
branch_labels: str | Sequence[str] | None = None
#: Alembic revision dependencies.
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("heading_role", sa.String(length=16), nullable=True)
        )
        batch_op.create_check_constraint(
            "ck_sentences_heading_role",
            "heading_role IS NULL OR heading_role IN ('chapter','section','subsection')",  # noqa: E501
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.drop_constraint("ck_sentences_heading_role", type_="check")
        batch_op.drop_column("heading_role")

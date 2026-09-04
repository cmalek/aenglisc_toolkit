"""Add annotation sense field."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

#: revision identifiers, used by Alembic.
revision: str = "82eb5c3ae099"
#: Down revision.
down_revision: str | Sequence[str] | None = "9c0e5c213b71"
#: Branch labels.
branch_labels: str | Sequence[str] | None = None
#: Depends on.
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("annotations", schema=None) as batch_op:
        batch_op.add_column(sa.Column("sense", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("annotations", schema=None) as batch_op:
        batch_op.drop_column("sense")

"""
Add sentence heading role

Revision ID: 92ac9a3a52db
Revises: 7cd945e38aff
Create Date: 2026-11-14 17:15:53.226726

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.orm import Session

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
    _promote_official_chapter_titles()


def _promote_official_chapter_titles() -> None:
    """
    Give every chapter with an official title a chapter heading sentence.

    The model layer saves tokens and annotations through the runtime session,
    so the migration's session is registered as the runtime session while the
    promotion runs. The previous registration is put back afterwards.

    Side Effects:
        May insert sentences and set ``heading_role`` on them inside the
        migration's transaction. Alembic owns the commit. Temporarily replaces
        the runtime session.

    """
    from oeapp.db import (  # noqa: PLC0415
        clear_runtime_session,
        get_runtime_session,
        set_runtime_session,
    )
    from oeapp.models.chapter import Chapter  # noqa: PLC0415
    from oeapp.models.headings import (  # noqa: PLC0415
        promote_official_chapter_title,
    )

    try:
        previous = get_runtime_session(create=False)
    except RuntimeError:
        previous = None
    with Session(bind=op.get_bind()) as session:
        set_runtime_session(session)
        try:
            chapter_ids = session.scalars(
                sa.select(Chapter.id).order_by(Chapter.project_id, Chapter.number)
            ).all()
            for chapter_id in chapter_ids:
                chapter = session.get(Chapter, chapter_id)
                if chapter is not None:
                    promote_official_chapter_title(chapter, session=session)
        finally:
            if previous is None:
                clear_runtime_session(close=False)
            else:
                set_runtime_session(previous)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("sentences", schema=None) as batch_op:
        batch_op.drop_constraint("ck_sentences_heading_role", type_="check")
        batch_op.drop_column("heading_role")

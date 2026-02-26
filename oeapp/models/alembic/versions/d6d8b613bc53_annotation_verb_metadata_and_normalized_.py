"""annotation verb metadata and normalized fields

Revision ID: d6d8b613bc53
Revises: 71b9d6456d8b
Create Date: 2026-02-26 12:37:33.678505

"""
from typing import Sequence, Union
import re
import unicodedata

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd6d8b613bc53'
down_revision: Union[str, Sequence[str], None] = '71b9d6456d8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_old_english(text: str | None) -> str | None:
    """Normalize token/root text for stable lookup and grouping."""
    if text is None:
        return None
    lowered = text.strip().lower().replace("ð", "þ")
    decomposed = unicodedata.normalize("NFD", lowered)
    without_marks = "".join(
        ch for ch in decomposed if unicodedata.category(ch) != "Mn"
    )
    stripped_internal_hyphen = re.sub(r"(?<=\S)[-–—](?=\S)", "", without_marks)
    return unicodedata.normalize("NFC", stripped_internal_hyphen)


def _backfill_annotations() -> None:
    """Backfill normalized root values for existing annotations."""
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, root FROM annotations")).fetchall()
    for row in rows:
        root_normalized = _normalize_old_english(row.root)
        bind.execute(
            sa.text(
                "UPDATE annotations SET root_normalized = :root_normalized WHERE id = :id"
            ),
            {"id": row.id, "root_normalized": root_normalized},
        )


def _backfill_tokens() -> None:
    """Backfill normalized surface values for existing tokens."""
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, surface FROM tokens")).fetchall()
    for row in rows:
        surface_normalized = _normalize_old_english(row.surface) or ""
        bind.execute(
            sa.text(
                "UPDATE tokens SET surface_normalized = :surface_normalized WHERE id = :id"
            ),
            {"id": row.id, "surface_normalized": surface_normalized},
        )


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table('annotation_presets', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'verb_requires_infinitive',
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                'verb_impersonal',
                sa.Boolean(),
                server_default=sa.text("0"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                'verb_transitivity',
                sa.String(),
                server_default='transitive',
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "ck_annotation_presets_verb_transitivity",
            "verb_transitivity IN ('transitive','intransitive')",
        )

    with op.batch_alter_table('annotations', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'verb_requires_infinitive',
                sa.Boolean(),
                server_default=sa.text('0'),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                'verb_impersonal',
                sa.Boolean(),
                server_default=sa.text('0'),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                'verb_transitivity',
                sa.String(),
                server_default='transitive',
                nullable=False,
            )
        )
        batch_op.add_column(sa.Column('root_normalized', sa.String(), nullable=True))
        batch_op.create_check_constraint(
            "ck_annotations_verb_transitivity",
            "verb_transitivity IN ('transitive','intransitive')",
        )

    with op.batch_alter_table('tokens', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('surface_normalized', sa.String(), server_default='', nullable=False)
        )

    _backfill_annotations()
    _backfill_tokens()


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('tokens', schema=None) as batch_op:
        batch_op.drop_column('surface_normalized')

    with op.batch_alter_table('annotations', schema=None) as batch_op:
        batch_op.drop_constraint("ck_annotations_verb_transitivity", type_="check")
        batch_op.drop_column('root_normalized')
        batch_op.drop_column('verb_transitivity')
        batch_op.drop_column('verb_impersonal')
        batch_op.drop_column('verb_requires_infinitive')

    with op.batch_alter_table('annotation_presets', schema=None) as batch_op:
        batch_op.drop_constraint(
            "ck_annotation_presets_verb_transitivity",
            type_="check",
        )
        batch_op.drop_column('verb_transitivity')
        batch_op.drop_column('verb_impersonal')
        batch_op.drop_column('verb_requires_infinitive')

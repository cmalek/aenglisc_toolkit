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


#: revision identifiers, used by Alembic.
revision: str = 'd6d8b613bc53'
#: Down revision.
down_revision: Union[str, Sequence[str], None] = '71b9d6456d8b'
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


def _check_constraint_exists(table_name: str, constraint_name: str) -> bool:
    """
    Return whether a check constraint exists on the given table.

    Args:
        table_name: Table name.
        constraint_name: Constraint name.

    Returns:
        The computed value.
    """
    if not _table_exists(table_name):
        return False
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = inspector.get_check_constraints(table_name)
    return any(
        constraint.get("name") == constraint_name for constraint in constraints
    )


def _normalize_old_english(text: str | None) -> str | None:
    """
    Normalize token/root text for stable lookup and grouping.

    Args:
        text: Text.

    Returns:
        The computed value.
    """
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
    if not _table_exists("annotations"):
        return
    if not _column_exists("annotations", "root"):
        return
    if not _column_exists("annotations", "root_normalized"):
        return
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
    if not _table_exists("tokens"):
        return
    if not _column_exists("tokens", "surface"):
        return
    if not _column_exists("tokens", "surface_normalized"):
        return
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
    if _table_exists("annotation_presets"):
        with op.batch_alter_table('annotation_presets', schema=None) as batch_op:
            if not _column_exists("annotation_presets", "verb_requires_infinitive"):
                batch_op.add_column(
                    sa.Column(
                        'verb_requires_infinitive',
                        sa.Boolean(),
                        server_default=sa.text("0"),
                        nullable=False,
                    )
                )
            if not _column_exists("annotation_presets", "verb_impersonal"):
                batch_op.add_column(
                    sa.Column(
                        'verb_impersonal',
                        sa.Boolean(),
                        server_default=sa.text("0"),
                        nullable=False,
                    )
                )
            if not _column_exists("annotation_presets", "verb_transitivity"):
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

    if _table_exists("annotations"):
        with op.batch_alter_table('annotations', schema=None) as batch_op:
            if not _column_exists("annotations", "verb_requires_infinitive"):
                batch_op.add_column(
                    sa.Column(
                        'verb_requires_infinitive',
                        sa.Boolean(),
                        server_default=sa.text('0'),
                        nullable=False,
                    )
                )
            if not _column_exists("annotations", "verb_impersonal"):
                batch_op.add_column(
                    sa.Column(
                        'verb_impersonal',
                        sa.Boolean(),
                        server_default=sa.text('0'),
                        nullable=False,
                    )
                )
            if not _column_exists("annotations", "verb_transitivity"):
                batch_op.add_column(
                    sa.Column(
                        'verb_transitivity',
                        sa.String(),
                        server_default='transitive',
                        nullable=False,
                    )
                )
                batch_op.create_check_constraint(
                    "ck_annotations_verb_transitivity",
                    "verb_transitivity IN ('transitive','intransitive')",
                )
            if not _column_exists("annotations", "root_normalized"):
                batch_op.add_column(sa.Column('root_normalized', sa.String(), nullable=True))

    if _table_exists("tokens") and not _column_exists("tokens", "surface_normalized"):
        with op.batch_alter_table('tokens', schema=None) as batch_op:
            batch_op.add_column(
                sa.Column('surface_normalized', sa.String(), server_default='', nullable=False)
            )

    _backfill_annotations()
    _backfill_tokens()


def downgrade() -> None:
    """Downgrade schema."""
    if _table_exists("tokens") and _column_exists("tokens", "surface_normalized"):
        with op.batch_alter_table('tokens', schema=None) as batch_op:
            batch_op.drop_column('surface_normalized')

    if _table_exists("annotations"):
        with op.batch_alter_table('annotations', schema=None) as batch_op:
            if _check_constraint_exists(
                "annotations", "ck_annotations_verb_transitivity"
            ):
                batch_op.drop_constraint("ck_annotations_verb_transitivity", type_="check")
            if _column_exists("annotations", "root_normalized"):
                batch_op.drop_column('root_normalized')
            if _column_exists("annotations", "verb_transitivity"):
                batch_op.drop_column('verb_transitivity')
            if _column_exists("annotations", "verb_impersonal"):
                batch_op.drop_column('verb_impersonal')
            if _column_exists("annotations", "verb_requires_infinitive"):
                batch_op.drop_column('verb_requires_infinitive')

    if _table_exists("annotation_presets"):
        with op.batch_alter_table('annotation_presets', schema=None) as batch_op:
            if _check_constraint_exists(
                "annotation_presets", "ck_annotation_presets_verb_transitivity"
            ):
                batch_op.drop_constraint(
                    "ck_annotation_presets_verb_transitivity",
                    type_="check",
                )
            if _column_exists("annotation_presets", "verb_transitivity"):
                batch_op.drop_column('verb_transitivity')
            if _column_exists("annotation_presets", "verb_impersonal"):
                batch_op.drop_column('verb_impersonal')
            if _column_exists("annotation_presets", "verb_requires_infinitive"):
                batch_op.drop_column('verb_requires_infinitive')

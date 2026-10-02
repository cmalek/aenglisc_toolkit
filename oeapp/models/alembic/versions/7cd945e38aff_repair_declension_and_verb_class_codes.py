"""repair declension and verb class codes

Revision ID: 7cd945e38aff
Revises: f38623b35077
Create Date: 2026-10-02 13:50:49.425028

"""

import logging
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7cd945e38aff"
down_revision: Union[str, Sequence[str], None] = "f38623b35077"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)

#: Tables repaired by this revision.
_TABLES = ("annotation_presets", "annotations")

#: Valid codes, frozen at the time of this revision.
_VALID_CODES = {
    "declension": frozenset(
        {
            "s",
            "w",
            "o",
            "i",
            "u",
            "ja",
            "jo",
            "wa",
            "wo",
            "pu",
            "r",
            "i-mut",
            "er",
            "nd",
            "th",
        }
    ),
    "verb_class": frozenset(
        {"a", "w1", "w2", "w3", "pp", "s1", "s2", "s3", "s4", "s5", "s6", "s7"}
    ),
}

#: Display labels the combos have shown, mapped to codes. Frozen.
_LABELS = {
    "declension": {
        "Strong (s)": "s",
        "Weak (w)": "w",
        "Other (o)": "o",
        "i-stem (i)": "i",
        "u-stem (u)": "u",
        "ja-stem (ja)": "ja",
        "jo-stem (jo)": "jo",
        "wa-stem (wa)": "wa",
        "wo-stem (wo)": "wo",
        "abstract -pu/-po (pu)": "pu",
        "r-stem (r)": "r",
        "i-mutation (i-mut)": "i-mut",
        "er nouns (children) (er)": "er",
        "-nd nouns(nd)": "nd",
        "-þ endings (th)": "th",
    },
    "verb_class": {
        "Anomolous (a)": "a",
        "Weak Class I (w1)": "w1",
        "Weak Class II (w2)": "w2",
        "Weak Class III (w3)": "w3",
        "Preterite-Present (pp)": "pp",
        "Strong Class 1 (s1)": "s1",
        "Strong Class 2 (s2)": "s2",
        "Strong Class 3 (s3)": "s3",
        "Strong Class 4 (s4)": "s4",
        "Strong Class 5 (s5)": "s5",
        "Strong Class 6 (s6)": "s6",
        "Strong Class 7 (s7)": "s7",
    },
}

#: A trailing parenthesised code, as every label ends.
_SUFFIX = re.compile(r"\(([^()]+)\)\s*$")


def _normalise(text: str) -> str:
    """Collapse whitespace and case-fold ``text``."""
    return " ".join(text.split()).casefold()


_LABEL_LOOKUP = {
    column: {_normalise(label): code for label, code in labels.items()}
    for column, labels in _LABELS.items()
}


def _repair(column: str, value: str) -> str | None:
    """
    Return the code for a stored value, ``None`` for blank, or ``value`` itself.

    Tiers, first match wins: already a code; trailing ``(code)``; normalised
    label. There is deliberately no fuzzy matching.
    """
    codes = _VALID_CODES[column]
    if value in codes:
        return value
    if not value.strip():
        return None
    match = _SUFFIX.search(value)
    if match and match.group(1).strip() in codes:
        return match.group(1).strip()
    return _LABEL_LOOKUP[column].get(_normalise(value), value)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _table_exists(table: str) -> bool:
    return table in _inspector().get_table_names()


def _column_exists(table: str, column: str) -> bool:
    return _table_exists(table) and any(
        c["name"] == column for c in _inspector().get_columns(table)
    )


def _check_constraint_exists(table: str, name: str) -> bool:
    return _table_exists(table) and any(
        c.get("name") == name for c in _inspector().get_check_constraints(table)
    )


def _repair_column(table: str, column: str) -> bool:
    """
    Repair one column in place.

    Returns:
        ``True`` if any value remains that no tier could resolve.

    """
    bind = op.get_bind()
    select = sa.text(
        f"SELECT DISTINCT {column} FROM {table} WHERE {column} IS NOT NULL"  # noqa: S608
    )
    update = sa.text(f"UPDATE {table} SET {column} = :new WHERE {column} = :old")  # noqa: S608
    unresolved = False
    for value in bind.execute(select).scalars().all():
        repaired = _repair(column, value)
        if repaired == value:
            if value not in _VALID_CODES[column]:
                logger.warning(
                    "pos-code-repair.unmatched table=%s column=%s value=%r",
                    table,
                    column,
                    value,
                )
                unresolved = True
            continue
        bind.execute(update, {"new": repaired, "old": value})
    return unresolved


def _in_list(column: str) -> str:
    codes = ", ".join(repr(code) for code in sorted(_VALID_CODES[column]))
    return f"{column} IN ({codes})"


def _add_preset_checks() -> None:
    with op.batch_alter_table("annotation_presets", schema=None) as batch_op:
        for column in _VALID_CODES:
            name = f"ck_annotation_presets_{column}"
            if not _check_constraint_exists("annotation_presets", name):
                batch_op.create_check_constraint(name, _in_list(column))


def upgrade() -> None:
    """Repair label-form values, then constrain presets if everything resolved."""
    preset_unresolved = False
    for table in _TABLES:
        for column in _VALID_CODES:
            if not _column_exists(table, column):
                continue
            unresolved = _repair_column(table, column)
            preset_unresolved = preset_unresolved or (
                unresolved and table == "annotation_presets"
            )
    if not _table_exists("annotation_presets"):
        return
    if preset_unresolved:
        logger.warning("pos-code-repair.checks-skipped table=annotation_presets")
        return
    _add_preset_checks()


def downgrade() -> None:
    """Downgrade schema.

    Intentionally a no-op: the earlier state was corrupt data.
    """

"""Helpers for the committed 1.0.0 release-baseline database (ADR 0007 D7)."""

import sqlite3
from pathlib import Path

from oeapp.db import Base
from sqlalchemy import create_engine

#: Schema of a database as release 1.0.0 created it, stamped ``BASELINE_REVISION``.
BASELINE_SQL = Path(__file__).parent / "fixtures" / "schema_1_0_0.sql"
#: Alembic revision the baseline schema is stamped with.
BASELINE_REVISION = "f38623b35077"
#: Row counts produced by ``_SEED``.
SEED_COUNTS = {"projects": 1, "sentences": 1, "tokens": 1, "annotations": 1}

_SEED = """
insert into projects (id, name, created_at, updated_at)
  values (1, 'Beowulf', '2026-01-01', '2026-01-01');
insert into sentences (id, project_id, display_order, text_oe, created_at, updated_at)
  values (1, 1, 1, 'Hwæt we Gardena', '2026-01-01', '2026-01-01');
insert into tokens (id, sentence_id, order_index, surface, surface_normalized,
                    created_at, updated_at)
  values (1, 1, 0, 'Gardena', 'gardena', '2026-01-01', '2026-01-01');
insert into annotations (id, token_id, pos, declension, updated_at,
                         verb_requires_infinitive, verb_impersonal, verb_transitivity)
  values (1, 1, 'N', 's', '2026-01-01', 0, 0, 'transitive');
"""


def build_baseline_db(path: Path) -> None:
    """Create a 1.0.0-schema database at ``path`` with the seed rows."""
    connection = sqlite3.connect(path)
    try:
        connection.executescript(BASELINE_SQL.read_text(encoding="utf-8"))
        connection.executescript(_SEED)
        connection.commit()
    finally:
        connection.close()


def build_create_all_db(path: Path) -> None:
    """Create a database at ``path`` straight from the current models."""
    import oeapp.models  # noqa: F401, PLC0415  (registers every table)

    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()


def schema_snapshot(path: Path) -> dict[str, object]:
    """Return table columns and index SQL for ``path``, ignoring ``alembic_version``."""
    connection = sqlite3.connect(path)
    try:
        tables = [
            name
            for (name,) in connection.execute(
                "select name from sqlite_master where type='table' "
                "and name not like 'sqlite_%' and name != 'alembic_version' "
                "order by name"
            )
        ]
        columns = {
            table: [
                (c[1], c[2].upper().split("(")[0], c[3], c[5])
                for c in connection.execute(f"pragma table_info({table})")
            ]
            for table in tables
        }
        indexes = {
            name: " ".join((sql or "").split())
            for name, sql in connection.execute(
                "select name, sql from sqlite_master "
                "where type='index' and sql is not null order by name"
            )
        }
    finally:
        connection.close()
    return {"columns": columns, "indexes": indexes}

"""The 1.0.0 baseline must upgrade to the same schema ``create_all`` builds."""

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from oeapp.services.migration import MigrationService

from tests.migration_baseline import (
    SEED_COUNTS,
    build_baseline_db,
    build_create_all_db,
    schema_snapshot,
)


def _config() -> Config:
    return Config(str(MigrationService.ALEMBIC_INI_PATH))


def _upgrade(db_path: Path, monkeypatch) -> None:
    # env.py falls back to AENGLISC_TOOLKIT_DB_PATH when no connection is injected
    monkeypatch.setenv("AENGLISC_TOOLKIT_DB_PATH", str(db_path))
    command.upgrade(_config(), "head")


def test_baseline_upgrades_to_the_create_all_schema(tmp_path, monkeypatch):
    upgraded, fresh = tmp_path / "upgraded.db", tmp_path / "fresh.db"
    build_baseline_db(upgraded)
    build_create_all_db(fresh)

    _upgrade(upgraded, monkeypatch)

    assert schema_snapshot(upgraded) == schema_snapshot(fresh)


def test_baseline_upgrade_keeps_rows_and_stamps_head(tmp_path, monkeypatch):
    db_path = tmp_path / "upgraded.db"
    build_baseline_db(db_path)

    _upgrade(db_path, monkeypatch)

    connection = sqlite3.connect(db_path)
    try:
        counts = {
            table: connection.execute(f"select count(*) from {table}").fetchone()[0]
            for table in SEED_COUNTS
        }
        revision = connection.execute("select version_num from alembic_version").fetchone()[0]
    finally:
        connection.close()
    assert counts == SEED_COUNTS
    assert revision == ScriptDirectory.from_config(_config()).get_current_head()


def test_schema_snapshot_detects_drift(tmp_path):
    first, second = tmp_path / "a.db", tmp_path / "b.db"
    for path, extra in ((first, ""), (second, ", extra text")):
        connection = sqlite3.connect(path)
        connection.execute(f"create table t (id integer{extra})")
        connection.commit()
        connection.close()

    assert schema_snapshot(first) != schema_snapshot(second)

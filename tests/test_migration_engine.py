"""Migrations act on the injected engine's database, with foreign keys OFF."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from alembic import op
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext

from oeapp.db import create_engine_with_path, read_alembic_revision
from oeapp.services.migration import MigrationService
from tests.migration_baseline import SEED_COUNTS, build_baseline_db


def _service(engine) -> MigrationService:
    return MigrationService(
        backup_service=MagicMock(),
        engine=engine,
        migration_metadata_service=MagicMock(),
    )


def test_upgrade_targets_the_injected_engine_not_the_env_path(tmp_path, monkeypatch):
    real, decoy = tmp_path / "real.db", tmp_path / "decoy.db"
    build_baseline_db(real)
    monkeypatch.setenv("AENGLISC_TOOLKIT_DB_PATH", str(decoy))
    engine = create_engine_with_path(real)
    service = _service(engine)

    service.apply_migrations()

    assert read_alembic_revision(engine) == service.code_migration_version()
    assert not decoy.exists() or decoy.stat().st_size == 0


def test_upgrade_runs_with_foreign_keys_off_then_restores_them(tmp_path):
    db_path = tmp_path / "live.db"
    build_baseline_db(db_path)
    engine = create_engine_with_path(db_path)
    seen: list[int] = []

    def fake_upgrade(config, revision):
        connection = config.attributes["connection"]
        seen.append(connection.exec_driver_sql("PRAGMA foreign_keys").scalar())

    with patch("oeapp.services.migration.command.upgrade", side_effect=fake_upgrade):
        _service(engine).apply_migrations()

    assert seen == [0]
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_upgrade_with_the_app_engine_keeps_every_row(tmp_path):
    db_path = tmp_path / "live.db"
    build_baseline_db(db_path)
    engine = create_engine_with_path(db_path)  # foreign_keys=ON listener, like the app

    _service(engine).apply_migrations()

    connection = sqlite3.connect(db_path)
    try:
        counts = {
            table: connection.execute(f"select count(*) from {table}").fetchone()[0]
            for table in SEED_COUNTS
        }
    finally:
        connection.close()
    assert counts == SEED_COUNTS


def test_failed_upgrade_rolls_back_and_restores_foreign_keys(tmp_path):
    db_path = tmp_path / "live.db"
    build_baseline_db(db_path)
    engine = create_engine_with_path(db_path)

    def failing_upgrade(config, revision):
        config.attributes["connection"].exec_driver_sql(
            "CREATE TABLE scratch (id integer)"
        )
        config.attributes["connection"].exec_driver_sql(
            "INSERT INTO scratch VALUES (1)"
        )
        msg = "boom"
        raise RuntimeError(msg)

    with (
        patch("oeapp.services.migration.command.upgrade", side_effect=failing_upgrade),
        pytest.raises(RuntimeError, match="boom"),
    ):
        _service(engine).apply_migrations()

    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_batch_recreation_does_not_cascade_delete_children(tmp_path):
    db_path = tmp_path / "cascade.db"
    setup = sqlite3.connect(db_path)
    setup.executescript(
        """
        CREATE TABLE parent (id integer PRIMARY KEY, name text);
        CREATE TABLE child (
            id integer PRIMARY KEY,
            parent_id integer REFERENCES parent(id) ON DELETE CASCADE
        );
        INSERT INTO parent VALUES (1, 'a'), (2, 'b');
        INSERT INTO child VALUES (1, 1), (2, 1), (3, 2);
        """
    )
    setup.commit()
    setup.close()
    engine = create_engine_with_path(db_path)

    def batch_upgrade(config, revision):
        context = MigrationContext.configure(config.attributes["connection"])
        with Operations.context(context):
            with op.batch_alter_table("parent", recreate="always") as batch:
                batch.add_column(sa.Column("extra", sa.Text()))

    with patch("oeapp.services.migration.command.upgrade", side_effect=batch_upgrade):
        _service(engine)._upgrade_to_head()

    connection = sqlite3.connect(db_path)
    try:
        assert connection.execute("select count(*) from child").fetchone()[0] == 3
    finally:
        connection.close()

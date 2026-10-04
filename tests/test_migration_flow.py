"""migrate(): backups before and after, rollback, and no backup for a fresh database."""

import json
import sqlite3
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from PySide6.QtCore import QSettings

from oeapp import __version__
from oeapp.db import create_engine_with_path
from oeapp.exc import BackupFailed, MigrationFailed
from oeapp.services.backup import LAST_APP_VERSION_KEY, BackupService
from oeapp.services.migration import MigrationResult, MigrationService
from tests.test_migration_backup_restore import InMemoryMigrationMetadataService

#: A real, older revision from the chain.
OLD_REV = "f38623b35077"


def _value(db_path) -> str:
    connection = sqlite3.connect(db_path)
    try:
        return connection.execute("select v from t").fetchone()[0]
    finally:
        connection.close()


def _set(service: MigrationService, statement: str) -> None:
    with service.engine.begin() as conn:
        conn.exec_driver_sql(statement)


@pytest.fixture
def flow(tmp_path):
    QSettings().clear()
    db_path = tmp_path / "live.db"
    engine = create_engine_with_path(db_path)
    with engine.begin() as conn:
        conn.exec_driver_sql("create table t (v text)")
        conn.exec_driver_sql("insert into t values ('original')")
        conn.exec_driver_sql(
            "create table alembic_version (version_num varchar(32) not null primary key)"
        )
        conn.exec_driver_sql(f"insert into alembic_version values ('{OLD_REV}')")
    service = MigrationService(
        backup_service=BackupService(db_path=db_path),
        engine=engine,
        migration_metadata_service=InMemoryMigrationMetadataService(),
    )
    yield service
    engine.dispose()


def _succeeding_apply(service: MigrationService):
    head = service.code_migration_version()

    def apply() -> MigrationResult:
        _set(service, f"update alembic_version set version_num='{head}'")
        return MigrationResult(app_version=__version__, migration_version=head)

    return apply


def _failing_apply(service: MigrationService):
    def apply() -> MigrationResult:
        _set(service, "update t set v='half-migrated'")
        msg = "boom"
        raise RuntimeError(msg)

    return apply


def _backups(service: MigrationService) -> list[dict]:
    return sorted(
        service.backup_service.get_backup_list(), key=lambda b: b["backup_timestamp"]
    )


class TestPending:
    def test_pending_ignores_the_catalog(self, flow):
        head = flow.code_migration_version()
        _set(flow, f"update alembic_version set version_num='{head}'")
        flow.migration_metadata_service.versions = {head: "0.0.1", OLD_REV: __version__}

        assert flow.has_pending_migrations() is False

    def test_pending_when_the_database_is_behind(self, flow):
        assert flow.has_pending_migrations() is True

    def test_not_pending_without_any_migration_files(self, flow):
        with patch.object(flow, "code_migration_version", return_value=None):
            assert flow.has_pending_migrations() is False


class TestMigrate:
    def test_no_pending_takes_no_backup(self, flow):
        with patch.object(flow, "has_pending_migrations", return_value=False):
            flow.migrate()
        assert _backups(flow) == []

    def test_success_takes_pre_and_post_backups(self, flow):
        QSettings().setValue(LAST_APP_VERSION_KEY, "1.0.0")
        head = flow.code_migration_version()
        with patch.object(
            flow, "apply_migrations", side_effect=_succeeding_apply(flow)
        ):
            flow.migrate()

        pairs = [
            (b["migration_version"], b["application_version"]) for b in _backups(flow)
        ]
        assert pairs == [(OLD_REV, "1.0.0"), (head, __version__)]

    def test_success_with_one_retained_backup_keeps_the_post_migration_one(self, flow):
        QSettings().setValue("backup/num_backups", 1)
        head = flow.code_migration_version()
        with patch.object(
            flow, "apply_migrations", side_effect=_succeeding_apply(flow)
        ):
            flow.migrate()

        remaining = _backups(flow)
        assert [b["migration_version"] for b in remaining] == [head]

    def test_a_failed_post_migration_backup_does_not_fail_the_migration(self, flow):
        real = flow.backup_service.create_backup
        calls: list[dict] = []

        def flaky(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise BackupFailed(OSError("disk full"), flow.db_path)
            return real(**kwargs)

        head = flow.code_migration_version()
        with (
            patch.object(flow.backup_service, "create_backup", side_effect=flaky),
            patch.object(flow, "apply_migrations", side_effect=_succeeding_apply(flow)),
        ):
            result = flow.migrate()

        assert result.migration_version == head
        assert flow.db_migration_version() == head

    def test_a_failed_pre_migration_backup_stops_before_upgrading(self, flow):
        with (
            patch.object(
                flow.backup_service,
                "create_backup",
                side_effect=BackupFailed(OSError("no"), flow.db_path),
            ),
            patch.object(flow, "apply_migrations") as apply,
            pytest.raises(MigrationFailed),
        ):
            flow.migrate()
        apply.assert_not_called()

    def test_failure_within_one_second_restores_the_original_data(self, flow):
        QSettings().setValue(LAST_APP_VERSION_KEY, "1.0.0")
        fixed = datetime(2026, 10, 3, 12, 0, 0, 5, tzinfo=UTC)
        with (
            patch("oeapp.services.backup.datetime") as clock,
            patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)),
        ):
            clock.now.return_value = fixed
            with pytest.raises(MigrationFailed) as failure:
                flow.migrate()

        assert _value(flow.db_path) == "original"
        assert failure.value.backup_app_version == "1.0.0"
        assert failure.value.backup_migration_version == OLD_REV
        assert (
            len(_backups(flow)) == 2
        )  # pre-migration copy and failed-state safety copy

    def test_failure_with_one_retained_backup_still_restores(self, flow):
        QSettings().setValue("backup/num_backups", 1)
        with patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)):
            with pytest.raises(MigrationFailed):
                flow.migrate()
        assert _value(flow.db_path) == "original"

    def test_failure_never_names_the_running_version(self, flow):
        # LAST_APP_VERSION_KEY is unset: the previous build is unknown
        with patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)):
            with pytest.raises(MigrationFailed) as failure:
                flow.migrate()
        assert failure.value.backup_app_version is None

    def test_pre_migration_sidecar_does_not_carry_the_running_version(self, flow):
        QSettings().setValue(LAST_APP_VERSION_KEY, "1.0.0")
        with patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)):
            with pytest.raises(MigrationFailed):
                flow.migrate()
        first = _backups(flow)[0]
        sidecar = json.loads(first["metadata_path"].read_text())
        assert sidecar["application_version"] == "1.0.0"
        assert sidecar["created_by_version"] == __version__

    def test_fresh_database_takes_no_backup(self, tmp_path):
        QSettings().clear()
        engine = create_engine_with_path(tmp_path / "fresh.db")
        service = MigrationService(
            backup_service=BackupService(db_path=tmp_path / "fresh.db"),
            engine=engine,
            migration_metadata_service=InMemoryMigrationMetadataService(),
        )

        result = service.migrate()

        assert service.backup_service.get_backup_list() == []
        assert result.migration_version == service.code_migration_version()
        engine.dispose()

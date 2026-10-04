"""MainWindow startup: an unknown database revision shows a dialog, then exits."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from oeapp.exc import MigrationFailed, UnknownDatabaseRevision
from oeapp.ui.main_window import MainWindow


def test_unknown_revision_shows_the_dialog_then_exits():
    window = MagicMock()
    error = UnknownDatabaseRevision("zzz", "1.9.0")
    with (
        patch("oeapp.ui.main_window.MigrationService") as service_cls,
        patch("oeapp.ui.main_window.UnknownRevisionDialog") as dialog_cls,
    ):
        service_cls.return_value.migrate.side_effect = error
        with pytest.raises(SystemExit) as exit_info:
            MainWindow._handle_migrations(window)

    dialog_cls.assert_called_once_with(window, error)
    dialog_cls.return_value.execute.assert_called_once_with()
    assert exit_info.value.code == 1  # noqa: S101


@pytest.mark.parametrize("restored", [True, False])
def test_migration_failure_writes_last_working_version_only_when_restored(restored):
    window = MagicMock()
    error = MigrationFailed(
        RuntimeError("x"),
        "1.0.0",
        "rev1",
        restored=restored,
        backup_path=Path("/b/pre.db"),
        database_path=Path("/d/live.db"),
    )
    with (
        patch("oeapp.ui.main_window.MigrationService") as service_cls,
        patch("oeapp.ui.main_window.MigrationFailureDialog") as dialog_cls,
        patch("oeapp.ui.main_window.QSettings") as settings_cls,
    ):
        service_cls.return_value.migrate.side_effect = error
        with pytest.raises(SystemExit):
            MainWindow._handle_migrations(window)

    dialog_cls.assert_called_once_with(
        window,
        error.error,
        "1.0.0",
        restored=restored,
        backup_path=Path("/b/pre.db"),
        database_path=Path("/d/live.db"),
    )
    set_value = settings_cls.return_value.setValue
    if restored:
        set_value.assert_called_once_with("migration/last_working_version", "rev1")
    else:
        set_value.assert_not_called()

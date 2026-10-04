"""MainWindow startup: an unknown database revision shows a dialog, then exits."""

from unittest.mock import MagicMock, patch

import pytest
from oeapp.exc import UnknownDatabaseRevision
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

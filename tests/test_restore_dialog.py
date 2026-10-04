"""Unit tests for RestoreDialog."""

from datetime import UTC, datetime

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.restore import RestoreDialog

from tests.conftest import MockMainWindow

class TestRestoreDialog:
    """Test cases for RestoreDialog."""

    def test_restore_dialog_initializes(self, mock_main_window, qapp):
        """Test RestoreDialog initializes correctly."""

        dialog = RestoreDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_restore_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test RestoreDialog builds correctly."""

        dialog = RestoreDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert "Restore" in dialog.dialog.windowTitle()



def _dialog(mock_main_window, backup_path):
    backups = [
        {
            "backup_path": backup_path,
            "backup_timestamp": datetime.now(UTC),
            "file_size": 10,
            "migration_version": "zzz",
            "application_version": "1.9.0",
        }
    ]
    with patch("oeapp.ui.dialogs.restore.BackupService") as service_cls:
        service_cls.return_value.get_backup_list.return_value = backups
        dialog = RestoreDialog(mock_main_window)
        dialog.build()
    dialog.backup_table.setCurrentCell(0, 0)
    return dialog


class TestRestoreRefusalAndExit:
    def test_refuses_a_backup_with_an_unknown_revision(self, mock_main_window, qapp, tmp_path):
        dialog = _dialog(mock_main_window, tmp_path / "b.db")
        with (
            patch("oeapp.ui.dialogs.restore.BackupService") as service_cls,
            patch("oeapp.ui.dialogs.restore.MigrationService") as migration_cls,
            patch("oeapp.ui.dialogs.restore.QMessageBox") as box,
        ):
            service_cls.return_value.read_backup_metadata.return_value = {
                "migration_version": "zzz",
                "application_version": "1.9.0",
            }
            migration_cls.return_value.is_known_revision.return_value = False

            dialog.restore_backup()

        service_cls.return_value.restore_backup.assert_not_called()
        box.assert_not_called()  # refused before asking for confirmation
        warning = mock_main_window.messages.show_warning.call_args
        assert "1.9.0" in warning.args[0]

    def test_a_backup_without_a_revision_is_not_refused(self, mock_main_window, qapp, tmp_path):
        dialog = _dialog(mock_main_window, tmp_path / "b.db")
        with (
            patch("oeapp.ui.dialogs.restore.BackupService") as service_cls,
            patch("oeapp.ui.dialogs.restore.MigrationService"),
            patch("oeapp.ui.dialogs.restore.QMessageBox") as box,
            patch("oeapp.ui.dialogs.restore.QApplication") as app,
        ):
            service_cls.return_value.read_backup_metadata.return_value = {}
            service_cls.return_value.restore_backup.return_value = {}
            box.return_value.exec.return_value = box.StandardButton.Yes

            dialog.restore_backup()

        service_cls.return_value.restore_backup.assert_called_once()
        app.quit.assert_called_once_with()

    def test_exits_after_a_successful_restore(self, mock_main_window, qapp, tmp_path):
        dialog = _dialog(mock_main_window, tmp_path / "b.db")
        with (
            patch("oeapp.ui.dialogs.restore.BackupService") as service_cls,
            patch("oeapp.ui.dialogs.restore.MigrationService") as migration_cls,
            patch("oeapp.ui.dialogs.restore.QMessageBox") as box,
            patch("oeapp.ui.dialogs.restore.QApplication") as app,
            patch("oeapp.ui.dialogs.restore.QSettings"),
        ):
            service_cls.return_value.read_backup_metadata.return_value = {
                "migration_version": "f38623b35077"
            }
            migration_cls.return_value.is_known_revision.return_value = True
            service_cls.return_value.restore_backup.return_value = {
                "migration_version": "f38623b35077"
            }
            box.return_value.exec.return_value = box.StandardButton.Yes

            dialog.restore_backup()

        app.quit.assert_called_once_with()
        mock_main_window.messages.show_information.assert_called_once()

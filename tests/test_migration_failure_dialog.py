"""Unit tests for MigrationFailureDialog."""

from pathlib import Path

from PySide6.QtWidgets import QLabel

from oeapp.ui.dialogs.migration_failure import MigrationFailureDialog

from tests.conftest import MockMainWindow

class TestMigrationFailureDialog:
    """Test cases for MigrationFailureDialog."""

    def test_migration_failure_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test MigrationFailureDialog initializes correctly."""
        error = Exception("Test migration error")
        backup_app_version = "1.0.0"

        dialog = MigrationFailureDialog(mock_main_window, error, backup_app_version)

        assert dialog.main_window == mock_main_window
        assert dialog.error == error
        assert dialog.backup_app_version == backup_app_version

    def test_migration_failure_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test MigrationFailureDialog builds correctly."""
        error = Exception("Test migration error")
        backup_app_version = "1.0.0"

        dialog = MigrationFailureDialog(mock_main_window, error, backup_app_version)
        dialog.build()

        assert dialog.dialog is not None
        assert "Migration" in dialog.dialog.windowTitle()

    def test_migration_failure_dialog_handles_no_backup_version(self, db_session, mock_main_window, qapp):
        """Test MigrationFailureDialog handles None backup version."""
        error = Exception("Test migration error")

        dialog = MigrationFailureDialog(mock_main_window, error, None)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.backup_app_version is None



class TestHonestRestoreText:
    def _text(self, window, **kwargs):
        dialog = MigrationFailureDialog(window, Exception("boom"), "1.0.0", **kwargs)
        dialog.build()
        return dialog.dialog.findChildren(QLabel)[0].text()

    def test_restored_text_unchanged(self, db_session, mock_main_window, qapp):
        text = self._text(mock_main_window)
        assert "has been automatically restored" in text
        assert "please downgrade to application version 1.0.0" in text

    def test_not_restored_text_is_honest(self, db_session, mock_main_window, qapp):
        text = self._text(
            mock_main_window,
            restored=False,
            backup_path=Path("/x/backups/pre.db"),
            database_path=Path("/x/live.db"),
        )
        assert "/x/backups/pre.db" in text
        assert "/x/live.db" in text
        assert "has been automatically restored" not in text
        assert "please downgrade" not in text
        assert "restore also failed" in text
        assert "1.0.0" in text

    def test_not_restored_steps_cover_wal_files_and_moving(
        self, db_session, mock_main_window, qapp, tmp_path
    ):
        backup = tmp_path / "pre.db"
        backup.write_text("x")
        text = self._text(
            mock_main_window,
            restored=False,
            backup_path=backup,
            database_path=tmp_path / "live.db",
        )
        assert "-wal" in text
        assert "-shm" in text
        assert "Move" in text
        assert ".broken" in text
        assert "Restore dialog" not in text
        assert "is safe" in text

    def test_not_restored_missing_backup_is_not_called_safe(
        self, db_session, mock_main_window, qapp, tmp_path
    ):
        text = self._text(
            mock_main_window,
            restored=False,
            backup_path=tmp_path / "gone.db",
            database_path=tmp_path / "live.db",
        )
        assert "is safe" not in text
        assert "could not be found" in text

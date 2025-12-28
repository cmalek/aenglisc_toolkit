"""Unit tests for MigrationFailureDialog."""

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


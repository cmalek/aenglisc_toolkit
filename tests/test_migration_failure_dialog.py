"""Unit tests for MigrationFailureDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.migration_failure import MigrationFailureDialog


class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self):
        super().__init__()
        self.show_error = MagicMock()


class TestMigrationFailureDialog:
    """Test cases for MigrationFailureDialog."""

    def test_migration_failure_dialog_initializes(self, qapp):
        """Test MigrationFailureDialog initializes correctly."""
        mock_main_window = MockMainWindow()
        error = Exception("Test migration error")
        backup_app_version = "1.0.0"

        dialog = MigrationFailureDialog(mock_main_window, error, backup_app_version)

        assert dialog.main_window == mock_main_window
        assert dialog.error == error
        assert dialog.backup_app_version == backup_app_version

    def test_migration_failure_dialog_builds(self, qapp):
        """Test MigrationFailureDialog builds correctly."""
        mock_main_window = MockMainWindow()
        error = Exception("Test migration error")
        backup_app_version = "1.0.0"

        dialog = MigrationFailureDialog(mock_main_window, error, backup_app_version)
        dialog.build()

        assert dialog.dialog is not None
        assert "Migration" in dialog.dialog.windowTitle()

    def test_migration_failure_dialog_handles_no_backup_version(self, qapp):
        """Test MigrationFailureDialog handles None backup version."""
        mock_main_window = MockMainWindow()
        error = Exception("Test migration error")

        dialog = MigrationFailureDialog(mock_main_window, error, None)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.backup_app_version is None


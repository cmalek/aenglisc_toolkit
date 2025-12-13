"""Unit tests for RestoreDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.restore import RestoreDialog


class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self):
        super().__init__()
        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()
        self.backup_service = MagicMock()
        self.migration_service = MagicMock()


class TestRestoreDialog:
    """Test cases for RestoreDialog."""

    def test_restore_dialog_initializes(self, qapp):
        """Test RestoreDialog initializes correctly."""
        mock_main_window = MockMainWindow()

        dialog = RestoreDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_restore_dialog_builds(self, qapp):
        """Test RestoreDialog builds correctly."""
        mock_main_window = MockMainWindow()

        dialog = RestoreDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert "Restore" in dialog.dialog.windowTitle()


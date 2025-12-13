"""Unit tests for BackupsViewDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.backups_view import BackupsViewDialog


class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self):
        super().__init__()
        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()
        self.backup_service = MagicMock()


class TestBackupsViewDialog:
    """Test cases for BackupsViewDialog."""

    def test_backups_view_dialog_initializes(self, qapp):
        """Test BackupsViewDialog initializes correctly."""
        mock_main_window = MockMainWindow()

        dialog = BackupsViewDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_backups_view_dialog_builds(self, qapp):
        """Test BackupsViewDialog builds correctly."""
        mock_main_window = MockMainWindow()

        dialog = BackupsViewDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert "Backup" in dialog.dialog.windowTitle()


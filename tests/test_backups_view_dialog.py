"""Unit tests for BackupsViewDialog."""

from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.backups_view import BackupsViewDialog

from .conftest import MockMainWindow


class TestBackupsViewDialog:
    """Test cases for BackupsViewDialog."""

    def test_backups_view_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test BackupsViewDialog initializes correctly."""

        dialog = BackupsViewDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_backups_view_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test BackupsViewDialog builds correctly."""

        dialog = BackupsViewDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert "Backup" in dialog.dialog.windowTitle()


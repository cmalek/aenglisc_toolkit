"""Unit tests for RestoreDialog."""

import pytest
from unittest.mock import MagicMock
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


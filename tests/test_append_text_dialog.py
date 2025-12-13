"""Unit tests for AppendTextDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.append_text import AppendTextDialog


class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()
        self.current_project_id = None


class TestAppendTextDialog:
    """Test cases for AppendTextDialog."""

    def test_append_text_dialog_initializes(self, db_session, qapp):
        """Test AppendTextDialog initializes correctly."""
        mock_main_window = MockMainWindow(db_session)

        dialog = AppendTextDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_append_text_dialog_builds(self, db_session, qapp):
        """Test AppendTextDialog builds correctly."""
        mock_main_window = MockMainWindow(db_session)

        dialog = AppendTextDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Append OE Text"


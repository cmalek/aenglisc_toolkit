"""Unit tests for NewProjectDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.new_project import NewProjectDialog


class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()


class TestNewProjectDialog:
    """Test cases for NewProjectDialog."""

    def test_new_project_dialog_initializes(self, db_session, qapp):
        """Test NewProjectDialog initializes correctly."""
        mock_main_window = MockMainWindow(db_session)

        dialog = NewProjectDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_new_project_dialog_builds(self, db_session, qapp):
        """Test NewProjectDialog builds correctly."""
        mock_main_window = MockMainWindow(db_session)

        dialog = NewProjectDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "New Project"
        assert dialog.title_edit is not None


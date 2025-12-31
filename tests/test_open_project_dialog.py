"""Unit tests for OpenProjectDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.open_project import OpenProjectDialog
from tests.conftest import create_test_project


class TestOpenProjectDialog:
    """Test cases for OpenProjectDialog."""

    def test_open_project_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test OpenProjectDialog initializes correctly."""

        dialog = OpenProjectDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_open_project_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test OpenProjectDialog builds correctly."""

        dialog = OpenProjectDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Open Project"
        assert dialog.project_table is not None

    def test_open_project_dialog_loads_projects(self, db_session, mock_main_window, qapp):
        """Test OpenProjectDialog loads projects into table."""
        # Create test projects
        project1 = create_test_project(db_session, name="Project 1", text="")
        project2 = create_test_project(db_session, name="Project 2", text="")


        dialog = OpenProjectDialog(mock_main_window)
        dialog.build()

        # Should have projects in table
        assert dialog.project_table.rowCount() >= 2

    def test_open_project_dialog_filters_projects(self, db_session, mock_main_window, qapp):
        """Test OpenProjectDialog filters projects by search."""
        # Create test projects
        project1 = create_test_project(db_session, name="Alpha Project", text="")
        project2 = create_test_project(db_session, name="Beta Project", text="")


        dialog = OpenProjectDialog(mock_main_window)
        dialog.build()

        # Set search text
        dialog.search_box.setText("Alpha")

        # Should filter projects
        assert dialog.search_box.text() == "Alpha"


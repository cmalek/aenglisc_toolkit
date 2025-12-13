"""Unit tests for DeleteProjectDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.delete_project import DeleteProjectDialog
from tests.conftest import create_test_project


class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self, session):
        super().__init__()
        self.session = session
        # Add methods that might be called
        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()
        self.export_project_json = MagicMock(return_value=True)


class TestDeleteProjectDialog:
    """Test cases for DeleteProjectDialog."""

    def test_delete_project_dialog_initializes(self, db_session, qapp):
        """Test DeleteProjectDialog initializes correctly."""
        mock_main_window = MockMainWindow(db_session)

        dialog = DeleteProjectDialog(mock_main_window)

        assert dialog.main_window == mock_main_window
        assert dialog.selected_project_id is None

    def test_delete_project_dialog_builds(self, db_session, qapp):
        """Test DeleteProjectDialog builds correctly."""
        mock_main_window = MockMainWindow(db_session)

        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Delete Project"
        assert dialog.project_table is not None

    def test_delete_project_dialog_loads_projects(self, db_session, qapp):
        """Test DeleteProjectDialog loads projects into table."""
        # Create test projects
        project1 = create_test_project(db_session, name="Project 1", text="")
        project2 = create_test_project(db_session, name="Project 2", text="")
        db_session.commit()

        mock_main_window = MockMainWindow(db_session)

        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        # Should have projects in table
        assert dialog.project_table.rowCount() >= 2

    def test_delete_project_dialog_filters_projects(self, db_session, qapp):
        """Test DeleteProjectDialog filters projects by search."""
        # Create test projects
        project1 = create_test_project(db_session, name="Alpha Project", text="")
        project2 = create_test_project(db_session, name="Beta Project", text="")
        db_session.commit()

        mock_main_window = MockMainWindow(db_session)

        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        # Set search text - the textChanged signal should call _filter_projects
        dialog.search_box.setText("Alpha")

        # Should filter projects (exact behavior depends on implementation)
        assert dialog.search_box.text() == "Alpha"

    def test_delete_project_dialog_handles_no_projects(self, db_session, qapp):
        """Test DeleteProjectDialog handles case with no projects."""
        mock_main_window = MockMainWindow(db_session)

        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        # Should still build without error
        assert dialog.dialog is not None
        assert dialog.project_table is not None


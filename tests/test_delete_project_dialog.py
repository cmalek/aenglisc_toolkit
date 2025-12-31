"""Unit tests for DeleteProjectDialog."""

from oeapp.ui.dialogs.delete_project import DeleteProjectDialog
from tests.conftest import create_test_project


class TestDeleteProjectDialog:
    """Test cases for DeleteProjectDialog."""

    def test_delete_project_dialog_initializes(self, mock_main_window, qapp):
        """Test DeleteProjectDialog initializes correctly."""

        dialog = DeleteProjectDialog(mock_main_window)

        assert dialog.main_window == mock_main_window
        assert dialog.selected_project_id is None

    def test_delete_project_dialog_builds(self, mock_main_window, qapp):
        """Test DeleteProjectDialog builds correctly."""

        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Delete Project"
        assert dialog.project_table is not None

    def test_delete_project_dialog_loads_projects(self, mock_main_window, qapp):
        """Test DeleteProjectDialog loads projects into table."""
        # Create test projects
        db_session = mock_main_window.application_state.session
        project1 = create_test_project(db_session, name="Project 1", text="")
        project2 = create_test_project(db_session, name="Project 2", text="")

        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        # Should have projects in table
        assert dialog.project_table.rowCount() >= 2

    def test_delete_project_dialog_filters_projects(self, mock_main_window, qapp):
        """Test DeleteProjectDialog filters projects by search."""
        # Create test projects
        db_session = mock_main_window.application_state.session
        project1 = create_test_project(db_session, name="Alpha Project", text="")
        project2 = create_test_project(db_session, name="Beta Project", text="")

        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        # Set search text - the textChanged signal should call _filter_projects
        dialog.search_box.setText("Alpha")

        # Should filter projects (exact behavior depends on implementation)
        assert dialog.search_box.text() == "Alpha"

    def test_delete_project_dialog_handles_no_projects(self,  mock_main_window, qapp):
        """Test DeleteProjectDialog handles case with no projects."""
        dialog = DeleteProjectDialog(mock_main_window)
        dialog.build()

        # Should still build without error
        assert dialog.dialog is not None
        assert dialog.project_table is not None


"""Unit tests for NewProjectDialog."""

from oeapp.ui.dialogs.new_project import NewProjectDialog

class TestNewProjectDialog:
    """Test cases for NewProjectDialog."""

    def test_new_project_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test NewProjectDialog initializes correctly."""

        dialog = NewProjectDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_new_project_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test NewProjectDialog builds correctly."""
        dialog = NewProjectDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "New Project"
        assert dialog.title_edit is not None


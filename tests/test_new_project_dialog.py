"""Unit tests for NewProjectDialog."""

from oeapp.models.project import Project
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
        assert dialog.source_edit is not None
        assert dialog.translator_edit is not None
        assert dialog.notes_edit is not None

    def test_new_project_dialog_creates_project_with_metadata(self, db_session, mock_main_window, qapp, qtbot):
        """Test NewProjectDialog creates project with metadata."""
        dialog = NewProjectDialog(mock_main_window)
        dialog.build()

        dialog.title_edit.setText("Metadata Project")
        dialog.source_edit.setPlainText("Custom Source")
        dialog.translator_edit.setText("Custom Translator")
        dialog.notes_edit.setPlainText("Custom Notes")
        dialog.text_edit.setPlainText("Se cyning.")

        # Call new_project directly (this is what happens after exec() returns)
        dialog.new_project()

        project = Project.get(1)
        assert project is not None
        assert project.name == "Metadata Project"
        assert project.source == "Custom Source"
        assert project.translator == "Custom Translator"
        assert project.notes == "Custom Notes"


"""Unit tests for EditProjectDialog."""

import pytest
from oeapp.ui.dialogs.edit_project import EditProjectDialog
from oeapp.models.project import Project
from tests.conftest import create_test_project

class TestEditProjectDialog:
    """Test cases for EditProjectDialog."""

    def test_edit_project_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test EditProjectDialog initializes correctly."""
        project = create_test_project(db_session, name="Test Project")
        dialog = EditProjectDialog(mock_main_window, project)

        assert dialog.main_window == mock_main_window
        assert dialog.project == project

    def test_edit_project_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test EditProjectDialog builds correctly."""
        project = create_test_project(db_session, name="Test Project")
        dialog = EditProjectDialog(mock_main_window, project)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Edit Project"
        assert dialog.title_edit is not None
        assert dialog.source_edit is not None
        assert dialog.translator_edit is not None
        assert dialog.notes_edit is not None

        # Verify initial values
        assert dialog.title_edit.text() == "Test Project"
        assert dialog.source_edit.toPlainText() == ""
        assert dialog.translator_edit.text() == ""
        assert dialog.notes_edit.toPlainText() == ""

    def test_edit_project_dialog_saves_changes(self, db_session, mock_main_window, qapp, qtbot):
        """Test EditProjectDialog saves changes correctly."""
        project = create_test_project(
            db_session,
            name="Original Title",
            source="Original Source",
            translator="Original Translator",
            notes="Original Notes"
        )
        dialog = EditProjectDialog(mock_main_window, project)
        dialog.build()

        # Update fields
        dialog.title_edit.setText("Updated Title")
        dialog.source_edit.setPlainText("Updated Source")
        dialog.translator_edit.setText("Updated Translator")
        dialog.notes_edit.setPlainText("Updated Notes")

        # Save the project
        with qtbot.waitSignal(dialog.dialog.finished):
            dialog.save_project()

        # Verify changes in database
        db_session.refresh(project)
        assert project.name == "Updated Title"
        assert project.source == "Updated Source"
        assert project.translator == "Updated Translator"
        assert project.notes == "Updated Notes"

    def test_edit_project_dialog_prevents_empty_title(self, db_session, mock_main_window, qapp, qtbot):
        """Test EditProjectDialog prevents saving an empty title."""
        project = create_test_project(db_session, name="Valid Title")
        dialog = EditProjectDialog(mock_main_window, project)
        dialog.build()

        dialog.title_edit.setText("")

        # Save the project (should fail and not close)
        dialog.save_project()

        db_session.refresh(project)
        assert project.name == "Valid Title"

    def test_edit_project_dialog_prevents_duplicate_title(self, db_session, mock_main_window, qapp, qtbot):
        """Test EditProjectDialog prevents saving a duplicate title."""
        create_test_project(db_session, name="Existing Project")
        project = create_test_project(db_session, name="New Project")
        dialog = EditProjectDialog(mock_main_window, project)
        dialog.build()

        dialog.title_edit.setText("Existing Project")

        # Save the project (should fail and not close)
        dialog.save_project()

        db_session.refresh(project)
        assert project.name == "New Project"


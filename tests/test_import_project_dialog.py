"""Unit tests for ImportProjectDialog."""
# ruff: noqa: S101, ARG002, E501

from oeapp.ui.dialogs.import_project import ImportProjectDialog
from PySide6.QtWidgets import QLabel

from tests.conftest import create_test_project


class TestImportProjectDialog:
    """Test cases for ImportProjectDialog."""

    def test_import_project_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test ImportProjectDialog initializes correctly."""
        project = create_test_project(db_session, name="Imported Project", text="")

        dialog = ImportProjectDialog(mock_main_window, project, was_renamed=False)

        assert dialog.main_window == mock_main_window
        assert dialog.project == project
        assert dialog.was_renamed is False

    def test_import_project_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test ImportProjectDialog builds correctly."""
        project = create_test_project(db_session, name="Imported Project", text="")

        dialog = ImportProjectDialog(mock_main_window, project, was_renamed=False)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Import Successful"

    def test_import_project_dialog_shows_rename_message(self, db_session, mock_main_window, qapp):
        """Test ImportProjectDialog shows rename message when project was renamed."""
        project = create_test_project(db_session, name="Imported Project", text="")

        dialog = ImportProjectDialog(mock_main_window, project, was_renamed=True)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.was_renamed is True

    def test_import_project_dialog_names_ambiguous_spellings(
        self, db_session, mock_main_window, qapp
    ):
        """Import tells the user which remembered spellings conflict."""
        project = create_test_project(db_session, name="Imported Project", text="")

        dialog = ImportProjectDialog(
            mock_main_window,
            project,
            was_renamed=False,
            ambiguous_spellings=["ðæt / þæt"],
        )
        dialog.build()

        labels = [child.text() for child in dialog.dialog.findChildren(QLabel)]
        body = "\n".join(labels)
        assert "ðæt / þæt" in body
        assert "were kept as separate entries" in body
        assert "Apply Remembered Annotations" in body
        assert "will not use that spelling" in body


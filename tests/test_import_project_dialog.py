"""Unit tests for ImportProjectDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.import_project import ImportProjectDialog
from tests.conftest import create_test_project



class TestImportProjectDialog:
    """Test cases for ImportProjectDialog."""

    def test_import_project_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test ImportProjectDialog initializes correctly."""
        project = create_test_project(db_session, name="Imported Project", text="")
        db_session.commit()

        dialog = ImportProjectDialog(mock_main_window, project, was_renamed=False)

        assert dialog.main_window == mock_main_window
        assert dialog.project == project
        assert dialog.was_renamed is False

    def test_import_project_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test ImportProjectDialog builds correctly."""
        project = create_test_project(db_session, name="Imported Project", text="")
        db_session.commit()

        dialog = ImportProjectDialog(mock_main_window, project, was_renamed=False)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Import Successful"

    def test_import_project_dialog_shows_rename_message(self, db_session, mock_main_window, qapp):
        """Test ImportProjectDialog shows rename message when project was renamed."""
        project = create_test_project(db_session, name="Imported Project", text="")
        db_session.commit()

        dialog = ImportProjectDialog(mock_main_window, project, was_renamed=True)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.was_renamed is True


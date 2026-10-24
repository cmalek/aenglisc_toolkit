"""Unit tests for AppendTextDialog."""

from unittest.mock import MagicMock, patch

from oeapp.commands import Command, push_command
from oeapp.ui.dialogs.append_text import AppendTextDialog
from oeapp.ui.dialogs.edit_project import EditProjectDialog

from tests.conftest import create_test_project


class OkCommand(Command):
    """Command whose ``execute`` and ``undo`` always succeed."""

    def execute(self) -> bool:
        """Succeed."""
        return True

    def undo(self) -> bool:
        """Succeed."""
        return True

    def menu_text(self) -> str:
        """Describe the command."""
        return "Ok"


def test_append_clears_history(db_session, mock_main_window, qapp):
    project = create_test_project(db_session, name="Append Project")
    context = mock_main_window.app_context
    context.current_project_id = project.id
    push_command(context.undo_stack, OkCommand())
    mock_main_window.reload_project = MagicMock()
    dialog = AppendTextDialog(mock_main_window)
    dialog.build()
    dialog.get_ingest_input = MagicMock(return_value=("Se cyning", None))
    with patch(
        "oeapp.ui.dialogs.append_text.WyrdcraeftIngestService"
    ) as ingest_cls:
        dialog.append_text()
    ingest_cls.return_value.append_to_project.assert_called_once()
    assert context.undo_stack.canUndo() is False
    mock_main_window.reload_project.assert_called_once()


def test_edit_project_leaves_history(db_session, mock_main_window, qapp):
    project = create_test_project(db_session, name="Edit Project")
    context = mock_main_window.app_context
    context.current_project_id = project.id
    push_command(context.undo_stack, OkCommand())
    dialog = EditProjectDialog(mock_main_window, project)
    dialog.build()
    dialog.title_edit.setText("Edited Title")
    dialog.save_project()
    assert context.current_project_id == project.id
    assert context.undo_stack.canUndo() is True


class TestAppendTextDialog:
    """Test cases for AppendTextDialog."""

    def test_append_text_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test AppendTextDialog initializes correctly."""
        dialog = AppendTextDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_append_text_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test AppendTextDialog builds correctly."""
        dialog = AppendTextDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Append OE Text"


# ruff: noqa: ARG002, E501, PLR2004, S101
from unittest.mock import MagicMock, patch

import pytest
from oeapp.commands import Command, push_command
from oeapp.db import clear_runtime_session, set_runtime_session
from oeapp.models import AnnotationJson
from oeapp.state import AppContext
from PySide6.QtCore import QSettings
from PySide6.QtGui import QUndoStack
from sqlalchemy.orm import Session


class OkCommand(Command):
    """Command whose ``execute`` and ``undo`` always succeed."""

    def __init__(self, needs_full_reload: bool = False) -> None:
        """Store whether the command needs a full reload."""
        self._needs_full_reload = needs_full_reload

    def execute(self) -> bool:
        """Succeed."""
        return True

    def undo(self) -> bool:
        """Succeed."""
        return True

    def get_description(self) -> str:
        """Describe the command."""
        return "Ok"

    @property
    def needs_full_reload(self) -> bool:
        """Report the configured reload flag."""
        return self._needs_full_reload


@pytest.fixture
def context(db_session):
    """Build an AppContext on the test session."""
    return AppContext(session=db_session)


def test_same_project_id_keeps_history(context):
    push_command(context.undo_stack, OkCommand())
    context.current_project_id = 7
    context.current_project_id = 7
    assert context.undo_stack.canUndo() is True


def test_project_change_and_close_clear_history(context):
    context.current_project_id = 7
    push_command(context.undo_stack, OkCommand())
    context.current_project_id = 8
    assert context.undo_stack.canUndo() is False
    push_command(context.undo_stack, OkCommand())
    context.current_project_id = None
    assert context.undo_stack.canUndo() is False


def test_undo_limit_is_50(context):
    for _ in range(51):
        push_command(context.undo_stack, OkCommand())
    assert context.undo_stack.count() == 50


class TestAppContext:
    """Test cases for the Qt-native application context."""

    def test_initialization(self, db_session):
        """Test initial state after construction."""
        context = AppContext(session=db_session)

        assert isinstance(context.session, Session)
        assert isinstance(context.undo_stack, QUndoStack)
        assert context.undo_stack.undoLimit() == 50
        assert context.main_window is None
        assert isinstance(context.settings, QSettings)
        assert context.current_project_id is None
        assert context.current_chapter_id is None
        assert context.current_section_id is None
        assert context.copied_annotation is None

    def test_session_setter(self, db_session):
        """Test setting a custom session."""
        context = AppContext(session=db_session)
        new_session = MagicMock(spec=Session)

        context.session = new_session

        assert context.session is new_session

    def test_reset(self, db_session):
        """Test reset functionality."""
        context = AppContext(session=db_session)
        context.current_project_id = 123
        context.current_chapter_id = 7
        context.current_section_id = 3
        context.copied_annotation = AnnotationJson(pos="N")
        mock_window = MagicMock()
        context.set_main_window(mock_window)
        old_stack = context.undo_stack
        push_command(old_stack, OkCommand())

        context.reset()

        assert context.main_window is None
        assert context.current_project_id is None
        assert context.current_chapter_id is None
        assert context.current_section_id is None
        assert context.copied_annotation is None
        assert context.undo_stack is not old_stack
        assert context.undo_stack.count() == 0
        assert context.undo_stack.undoLimit() == 50
        assert context.session is not None

    def test_close_session(self, db_session):
        """Test that closing the context closes runtime session."""
        context = AppContext(session=db_session)
        mock_session = MagicMock()
        context.session = mock_session

        context.close_session()

        mock_session.close.assert_called_once()
        clear_runtime_session()

    def test_set_main_window(self, db_session):
        """Test setting the main window."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        context.set_main_window(mock_window)
        assert context.main_window is mock_window

    def test_property_signals(self, db_session, qtbot):
        """Stable state properties should emit changed signals."""
        context = AppContext(session=db_session)

        with qtbot.waitSignal(context.current_project_id_changed, timeout=1000):
            context.current_project_id = 42
        with qtbot.waitSignal(context.current_chapter_id_changed, timeout=1000):
            context.current_chapter_id = 7
        with qtbot.waitSignal(context.current_section_id_changed, timeout=1000):
            context.current_section_id = 3
        with qtbot.waitSignal(context.copied_annotation_changed, timeout=1000):
            context.copied_annotation = AnnotationJson(pos="N", root="cyning")

        assert context.current_project_id == 42
        assert context.current_chapter_id == 7
        assert context.current_section_id == 3
        assert context.copied_annotation == AnnotationJson(pos="N", root="cyning")

    def test_copied_annotation_signal_emits_plain_dict(self, db_session, qtbot):
        """Signal payload is a plain JSON dict."""
        context = AppContext(session=db_session)
        with qtbot.waitSignal(
            context.copied_annotation_changed, timeout=1000
        ) as blocker:
            context.copied_annotation = AnnotationJson(pos="N", root="cyning")
        payload = blocker.args[0]
        assert isinstance(payload, dict)
        assert payload["pos"] == "N"
        assert payload["root"] == "cyning"

    def test_reset_clears_copied_annotation_and_emits_none(self, db_session, qtbot):
        """Reset clears the copied annotation and emits None."""
        context = AppContext(session=db_session)
        context.copied_annotation = AnnotationJson(pos="N")
        with qtbot.waitSignal(
            context.copied_annotation_changed, timeout=1000
        ) as blocker:
            context.reset()
        assert blocker.args == [None]
        assert context.copied_annotation is None

    def test_copy_replaces_previous_and_emits_only_on_change(self, db_session, qtbot):
        """Setting an equal annotation does not re-emit."""
        context = AppContext(session=db_session)
        context.copied_annotation = AnnotationJson(pos="N")
        with qtbot.waitSignal(context.copied_annotation_changed, timeout=1000):
            context.copied_annotation = AnnotationJson(pos="V")
        assert context.copied_annotation == AnnotationJson(pos="V")
        with qtbot.assertNotEmitted(context.copied_annotation_changed):
            context.copied_annotation = AnnotationJson(pos="V")

    def test_runtime_session_provider_syncs(self, db_session):
        """AppContext session should stay in sync with runtime session provider."""
        context = AppContext(session=db_session)
        replacement = MagicMock(spec=Session)

        context.session = replacement

        assert context.session is replacement
        set_runtime_session(db_session)

    def test_show_message_with_window(self, db_session):
        """Test showing a message through the main window."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.messages = MagicMock()
        mock_window.messages.show_message = MagicMock()
        context.set_main_window(mock_window)

        context.show_message("Test message")
        mock_window.messages.show_message.assert_called_once_with(
            "Test message", duration=2000
        )

    def test_show_message_without_window(self, db_session):
        """Test showing a message via stderr when window is not set."""
        context = AppContext(session=db_session)

        with patch("sys.stderr.write") as mock_stderr:
            context.show_message("Error message")
            mock_stderr.assert_called_once_with("Error message\n")

    def _context_with_window(self, db_session):
        """Build a context with a mock main window."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        context.set_main_window(mock_window)
        return context, mock_window

    def test_undo_with_empty_stack_does_nothing(self, db_session):
        """Undo with nothing to undo leaves the window alone."""
        context, mock_window = self._context_with_window(db_session)

        context.undo()

        mock_window.refresh_project.assert_not_called()
        mock_window.reload_project.assert_not_called()

    def test_undo_success_no_reload(self, db_session):
        """Undo of a non-structural command refreshes the window."""
        context, mock_window = self._context_with_window(db_session)
        push_command(context.undo_stack, OkCommand(needs_full_reload=False))

        context.undo()

        assert context.undo_stack.canUndo() is False
        assert context.undo_stack.canRedo() is True
        mock_window.refresh_project.assert_called_once()
        mock_window.reload_project.assert_not_called()
        mock_window.messages.show_message.assert_called_with(
            "Undone", duration=2000
        )

    def test_undo_success_with_reload(self, db_session):
        """Undo of a structural command reloads the window."""
        context, mock_window = self._context_with_window(db_session)
        push_command(context.undo_stack, OkCommand(needs_full_reload=False))
        push_command(context.undo_stack, OkCommand(needs_full_reload=True))

        context.undo()

        mock_window.reload_project.assert_called_once()
        mock_window.refresh_project.assert_not_called()

    def test_redo_with_empty_stack_does_nothing(self, db_session):
        """Redo with nothing to redo leaves the window alone."""
        context, mock_window = self._context_with_window(db_session)
        push_command(context.undo_stack, OkCommand())

        context.redo()

        mock_window.refresh_project.assert_not_called()
        mock_window.reload_project.assert_not_called()

    def test_redo_success_no_reload(self, db_session):
        """Redo of a non-structural command refreshes the window."""
        context, mock_window = self._context_with_window(db_session)
        push_command(context.undo_stack, OkCommand(needs_full_reload=False))
        context.undo_stack.undo()

        context.redo()

        assert context.undo_stack.canUndo() is True
        mock_window.refresh_project.assert_called_once()
        mock_window.reload_project.assert_not_called()
        mock_window.messages.show_message.assert_called_with(
            "Redone", duration=2000
        )

    def test_redo_success_with_reload(self, db_session):
        """Redo of a structural command reloads the window."""
        context, mock_window = self._context_with_window(db_session)
        push_command(context.undo_stack, OkCommand(needs_full_reload=True))
        push_command(context.undo_stack, OkCommand(needs_full_reload=False))
        context.undo_stack.undo()
        context.undo_stack.undo()

        context.redo()

        mock_window.reload_project.assert_called_once()
        mock_window.refresh_project.assert_not_called()

# ruff: noqa: ARG002, E501, PLR2004, S101
from unittest.mock import MagicMock, patch

from oeapp.commands import CommandManager
from oeapp.db import clear_runtime_session, set_runtime_session
from oeapp.state import AppContext
from PySide6.QtCore import QSettings
from sqlalchemy.orm import Session


class TestAppContext:
    """Test cases for the Qt-native application context."""

    def test_initialization(self, db_session):
        """Test initial state after construction."""
        context = AppContext(session=db_session)

        assert isinstance(context.session, Session)
        assert isinstance(context.command_manager, CommandManager)
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
        assert context.command_manager.session is new_session

    def test_reset(self, db_session):
        """Test reset functionality."""
        context = AppContext(session=db_session)
        context.current_project_id = 123
        context.current_chapter_id = 7
        context.current_section_id = 3
        context.copied_annotation = {"pos": "N"}
        mock_window = MagicMock()
        context.set_main_window(mock_window)

        context.reset()

        assert context.main_window is None
        assert context.current_project_id is None
        assert context.current_chapter_id is None
        assert context.current_section_id is None
        assert context.copied_annotation is None
        assert isinstance(context.command_manager, CommandManager)
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
            context.copied_annotation = {"pos": "N", "root": "cyning"}

        assert context.current_project_id == 42
        assert context.current_chapter_id == 7
        assert context.current_section_id == 3
        assert context.copied_annotation == {"pos": "N", "root": "cyning"}

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

    def test_undo_can_undo_false(self, db_session):
        """Test undo when can_undo is False."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        context.set_main_window(mock_window)

        context.command_manager = MagicMock()
        context.command_manager.can_undo.return_value = False

        context.undo()
        context.command_manager.undo.assert_not_called()

    def test_undo_success_no_reload(self, db_session):
        """Test successful undo without structural reload."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        mock_window.messages = MagicMock()
        mock_window.messages.show_message = MagicMock()
        context.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = False

        context.command_manager = MagicMock()
        context.command_manager.can_undo.return_value = True
        context.command_manager.undo_stack = [mock_command]
        context.command_manager.undo.return_value = True
        context.command_manager.redo_stack = [mock_command]

        context.undo()

        mock_window.refresh_project.assert_called_once()
        mock_window.reload_project.assert_not_called()
        mock_window.messages.show_message.assert_called_with(
            "Undone", duration=2000
        )

    def test_undo_success_with_reload(self, db_session):
        """Test successful undo with structural reload."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        mock_window.messages = MagicMock()
        mock_window.messages.show_message = MagicMock()
        context.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = True

        context.command_manager = MagicMock()
        context.command_manager.can_undo.return_value = True
        context.command_manager.undo_stack = [mock_command]
        context.command_manager.undo.return_value = True
        context.command_manager.redo_stack = [mock_command]

        context.undo()

        mock_window.reload_project.assert_called_once()
        mock_window.messages.show_message.assert_called_with(
            "Undone", duration=2000
        )

    def test_undo_success_reload_from_redo_stack(self, db_session):
        """Test undo where reload is determined by the command now in redo stack."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        context.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = False
        mock_undone_command = MagicMock()
        mock_undone_command.needs_full_reload = True

        context.command_manager = MagicMock()
        context.command_manager.can_undo.return_value = True
        context.command_manager.undo_stack = [mock_command]
        context.command_manager.undo.return_value = True
        context.command_manager.redo_stack = [mock_undone_command]

        context.undo()

        mock_window.reload_project.assert_called_once()

    def test_undo_failed(self, db_session):
        """Test failed undo."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        mock_window.messages = MagicMock()
        mock_window.messages.show_message = MagicMock()
        context.set_main_window(mock_window)

        context.command_manager = MagicMock()
        context.command_manager.can_undo.return_value = True
        context.command_manager.undo_stack = [MagicMock()]
        context.command_manager.undo.return_value = False

        context.undo()

        mock_window.messages.show_message.assert_called_with(
            "Undo failed", duration=2000
        )

    def test_redo_can_redo_false(self, db_session):
        """Test redo when can_redo is False."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        context.set_main_window(mock_window)

        context.command_manager = MagicMock()
        context.command_manager.can_redo.return_value = False

        context.redo()
        context.command_manager.redo.assert_not_called()

    def test_redo_success_no_reload(self, db_session):
        """Test successful redo without structural reload."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        mock_window.messages = MagicMock()
        mock_window.messages.show_message = MagicMock()
        context.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = False

        context.command_manager = MagicMock()
        context.command_manager.can_redo.return_value = True
        context.command_manager.redo_stack = [mock_command]
        context.command_manager.redo.return_value = True
        context.command_manager.undo_stack = [mock_command]

        context.redo()

        mock_window.refresh_project.assert_called_once()
        mock_window.reload_project.assert_not_called()
        mock_window.messages.show_message.assert_called_with(
            "Redone", duration=2000
        )

    def test_redo_success_with_reload(self, db_session):
        """Test successful redo with structural reload."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        mock_window.messages = MagicMock()
        mock_window.messages.show_message = MagicMock()
        context.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = True

        context.command_manager = MagicMock()
        context.command_manager.can_redo.return_value = True
        context.command_manager.redo_stack = [mock_command]
        context.command_manager.redo.return_value = True
        context.command_manager.undo_stack = [mock_command]

        context.redo()

        mock_window.reload_project.assert_called_once()
        mock_window.messages.show_message.assert_called_with(
            "Redone", duration=2000
        )

    def test_redo_success_reload_from_undo_stack(self, db_session):
        """Test redo where reload is determined by the command now in undo stack."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        context.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = False
        mock_redone_command = MagicMock()
        mock_redone_command.needs_full_reload = True

        context.command_manager = MagicMock()
        context.command_manager.can_redo.return_value = True
        context.command_manager.redo_stack = [mock_command]
        context.command_manager.redo.return_value = True
        context.command_manager.undo_stack = [mock_redone_command]

        context.redo()

        mock_window.reload_project.assert_called_once()

    def test_redo_failed(self, db_session):
        """Test failed redo."""
        context = AppContext(session=db_session)
        mock_window = MagicMock()
        mock_window.app_context = context
        mock_window.messages = MagicMock()
        mock_window.messages.show_message = MagicMock()
        context.set_main_window(mock_window)

        context.command_manager = MagicMock()
        context.command_manager.can_redo.return_value = True
        context.command_manager.redo_stack = [MagicMock()]
        context.command_manager.redo.return_value = False

        context.redo()

        mock_window.messages.show_message.assert_called_with(
            "Redo failed", duration=2000
        )

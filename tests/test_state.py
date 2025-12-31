import sys
from unittest.mock import MagicMock, patch
import pytest
from PySide6.QtCore import QSettings
from sqlalchemy.orm import Session

from oeapp.state import ApplicationState, CURRENT_PROJECT_ID
from oeapp.commands import CommandManager

class TestApplicationState:

    def test_singleton(self, db_session):
        """Test that ApplicationState is a singleton."""
        state1 = ApplicationState()
        state2 = ApplicationState()
        assert state1 is state2

    def test_initialization(self, db_session):
        """Test initial state after reset."""
        state = ApplicationState()
        # session is lazily initialized
        assert isinstance(state.session, Session)
        assert isinstance(state.command_manager, CommandManager)
        assert state.main_window is None
        assert isinstance(state.settings, QSettings)
        assert len(state) == 0

    def test_session_setter(self, db_session):
        """Test setting a custom session."""
        state = ApplicationState()
        new_session = MagicMock(spec=Session)
        state.session = new_session

        assert state._session is new_session
        assert state.session is new_session
        # Command manager should be re-initialized with new session
        assert state.command_manager.session is new_session

    def test_reset(self, db_session):
        """Test reset functionality."""
        state = ApplicationState()
        state[CURRENT_PROJECT_ID] = 123
        mock_window = MagicMock()
        state.set_main_window(mock_window)

        state.reset()

        assert len(state) == 0
        assert state.main_window is None
        # reset() re-initializes command_manager with self.session,
        # which lazily re-creates self._session if it was None.
        assert state._session is not None
        assert isinstance(state.command_manager, CommandManager)

    def test_del_closes_session(self, db_session):
        """Test that __del__ closes the session."""
        state = ApplicationState()
        mock_session = MagicMock()
        state.session = mock_session

        state.__del__()

        mock_session.close.assert_called_once()
        assert state._session is None

    def test_set_main_window(self, db_session):
        """Test setting the main window."""
        state = ApplicationState()
        mock_window = MagicMock()
        state.set_main_window(mock_window)
        assert state.main_window is mock_window

    def test_show_message_with_window(self, db_session):
        """Test showing a message through the main window."""
        state = ApplicationState()
        mock_window = MagicMock()
        state.set_main_window(mock_window)

        state.show_message("Test message")
        mock_window.show_message.assert_called_once_with("Test message", duration=2000)

    def test_show_message_without_window(self):
        """Test showing a message via stderr when window is not set."""
        state = ApplicationState()
        state.main_window = None

        with patch("sys.stderr.write") as mock_stderr:
            state.show_message("Error message")
            mock_stderr.assert_called_once_with("Error message\n")

    def test_undo_can_undo_false(self, db_session):
        """Test undo when can_undo is False."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        state.set_main_window(mock_window)

        state.command_manager = MagicMock()
        state.command_manager.can_undo.return_value = False

        state.undo()
        state.command_manager.undo.assert_not_called()

    def test_undo_success_no_reload(self, db_session):
        """Test successful undo without structural reload."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        mock_window.show_message = MagicMock()
        state.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = False

        state.command_manager = MagicMock()
        state.command_manager.can_undo.return_value = True
        state.command_manager.undo_stack = [mock_command]
        state.command_manager.undo.return_value = True
        # After undo, command is moved to redo_stack in some implementations,
        # but ApplicationState checks undo_stack before calling undo()
        state.command_manager.redo_stack = [mock_command]

        state.undo()

        mock_window.refresh_project.assert_called_once()
        mock_window.reload_project.assert_not_called()
        mock_window.show_message.assert_called_with("Undone", duration=2000)

    def test_undo_success_with_reload(self, db_session):
        """Test successful undo with structural reload."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        mock_window.show_message = MagicMock()
        state.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = True

        state.command_manager = MagicMock()
        state.command_manager.can_undo.return_value = True
        state.command_manager.undo_stack = [mock_command]
        state.command_manager.undo.return_value = True
        state.command_manager.redo_stack = [mock_command]

        state.undo()

        mock_window.reload_project.assert_called_once()
        mock_window.show_message.assert_called_with("Undone", duration=2000)

    def test_undo_success_reload_from_redo_stack(self, db_session):
        """Test undo where reload is determined by the command now in redo stack."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        state.set_main_window(mock_window)

        # Command on undo stack doesn't need reload initially
        mock_command = MagicMock()
        mock_command.needs_full_reload = False

        # Command moved to redo stack after undo DOES need reload
        mock_undone_command = MagicMock()
        mock_undone_command.needs_full_reload = True

        state.command_manager = MagicMock()
        state.command_manager.can_undo.return_value = True
        state.command_manager.undo_stack = [mock_command]
        state.command_manager.undo.return_value = True
        state.command_manager.redo_stack = [mock_undone_command]

        state.undo()

        mock_window.reload_project.assert_called_once()

    def test_undo_failed(self, db_session):
        """Test failed undo."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        mock_window.show_message = MagicMock()
        state.set_main_window(mock_window)

        state.command_manager = MagicMock()
        state.command_manager.can_undo.return_value = True
        state.command_manager.undo_stack = [MagicMock()]
        state.command_manager.undo.return_value = False

        state.undo()

        mock_window.show_message.assert_called_with("Undo failed", duration=2000)

    def test_redo_can_redo_false(self):
        """Test redo when can_redo is False."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        state.set_main_window(mock_window)

        state.command_manager = MagicMock()
        state.command_manager.can_redo.return_value = False

        state.redo()
        state.command_manager.redo.assert_not_called()

    def test_redo_success_no_reload(self, db_session):
        """Test successful redo without structural reload."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        mock_window.show_message = MagicMock()
        state.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = False

        state.command_manager = MagicMock()
        state.command_manager.can_redo.return_value = True
        state.command_manager.redo_stack = [mock_command]
        state.command_manager.redo.return_value = True
        state.command_manager.undo_stack = [mock_command]

        state.redo()

        mock_window.refresh_project.assert_called_once()
        mock_window.reload_project.assert_not_called()
        mock_window.show_message.assert_called_with("Redone", duration=2000)

    def test_redo_success_with_reload(self, db_session):
        """Test successful redo with structural reload."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        mock_window.show_message = MagicMock()
        state.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = True

        state.command_manager = MagicMock()
        state.command_manager.can_redo.return_value = True
        state.command_manager.redo_stack = [mock_command]
        state.command_manager.redo.return_value = True
        state.command_manager.undo_stack = [mock_command]

        state.redo()

        mock_window.reload_project.assert_called_once()
        mock_window.show_message.assert_called_with("Redone", duration=2000)

    def test_redo_success_reload_from_undo_stack(self, db_session):
        """Test redo where reload is determined by the command now in undo stack."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        state.set_main_window(mock_window)

        mock_command = MagicMock()
        mock_command.needs_full_reload = False

        mock_redone_command = MagicMock()
        mock_redone_command.needs_full_reload = True

        state.command_manager = MagicMock()
        state.command_manager.can_redo.return_value = True
        state.command_manager.redo_stack = [mock_command]
        state.command_manager.redo.return_value = True
        state.command_manager.undo_stack = [mock_redone_command]

        state.redo()

        mock_window.reload_project.assert_called_once()

    def test_redo_failed(self, db_session):
        """Test failed redo."""
        state = ApplicationState()
        mock_window = MagicMock()
        mock_window.application_state = state
        mock_window.show_message = MagicMock()
        state.set_main_window(mock_window)

        state.command_manager = MagicMock()
        state.command_manager.can_redo.return_value = True
        state.command_manager.redo_stack = [MagicMock()]
        state.command_manager.redo.return_value = False

        state.redo()

        mock_window.show_message.assert_called_with("Redo failed", duration=2000)


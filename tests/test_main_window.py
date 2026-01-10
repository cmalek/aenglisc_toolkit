"""Unit tests for MainWindow."""

import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QStatusBar
from PySide6.QtCore import Qt

from oeapp.ui.main_window import MainWindow, MainWindowActions, Messages
from oeapp.state import ApplicationState, CURRENT_PROJECT_ID, COPIED_ANNOTATION, SELECTED_SENTENCE_CARD
from oeapp.models.project import Project

@pytest.fixture
def mock_services():
    """Fixture to mock MigrationService and BackupService."""
    with patch("oeapp.ui.main_window.MigrationService") as mock_mig, \
         patch("oeapp.ui.main_window.BackupService") as mock_back:
        # Configure migration mock to return a default result
        mock_mig_instance = mock_mig.return_value
        mock_mig_instance.migrate.return_value = MagicMock(
            migration_version="abc",
            app_version="1.0.0"
        )
        yield mock_mig, mock_back

@pytest.fixture
def main_window(qapp, db_session, mock_services):
    """Fixture to create a MainWindow instance with mocked services."""
    # Reset application state before creating window
    state = ApplicationState()
    state.reset()
    state.session = db_session

    window = MainWindow()
    return window

class TestMainWindowInitialization:
    """Test cases for MainWindow initialization and basic layout."""

    def test_initialization(self, main_window):
        """Test MainWindow initializes with correct basic properties."""
        assert main_window.windowTitle() == "Ænglisc Toolkit"
        assert main_window.centralWidget() is not None
        assert main_window.token_details_sidebar is not None
        assert main_window.content_layout is not None
        assert isinstance(main_window.statusBar(), QStatusBar)

    def test_show_empty_state(self, main_window):
        """Test that the empty state is shown on startup."""
        # Find the welcome label in the content layout
        welcome_label = None
        for i in range(main_window.content_layout.count()):
            widget = main_window.content_layout.itemAt(i).widget()
            if isinstance(widget, QLabel) and "Welcome" in widget.text():
                welcome_label = widget
                break

        assert welcome_label is not None
        # In Qt, isVisible() is only true if the window is actually shown.
        # For unit tests, we check that it's not explicitly hidden.
        assert not welcome_label.isHidden()

class TestMainWindowActions:
    """Test cases for MainWindowActions logic."""

    def test_navigation_next_prev_sentence(self, main_window):
        """Test next_sentence and prev_sentence navigation logic."""
        actions = main_window.action_service

        # Create mock cards
        mock_card1 = MagicMock()
        mock_card2 = MagicMock()
        mock_card3 = MagicMock()

        # Manually populate sentence_cards
        actions.sentence_cards.extend([mock_card1, mock_card2, mock_card3])

        # Initially nothing focused
        for card in [mock_card1, mock_card2, mock_card3]:
            card.has_focus = False

        # next_sentence should focus first card if none focused
        actions.next_sentence()
        mock_card1.focus.assert_called_once()

        # Now mock card 1 has focus
        mock_card1.has_focus = True
        actions.next_sentence()
        mock_card2.focus.assert_called_once()

        mock_card1.has_focus = False
        mock_card2.has_focus = True
        actions.next_sentence()
        mock_card3.focus.assert_called_once()

        # prev_sentence when nothing focused should focus last card
        for card in [mock_card1, mock_card2, mock_card3]:
            card.has_focus = False
        actions.prev_sentence()
        mock_card3.focus.assert_called_with() # second time called now (once by next, once by prev)

        # prev_sentence from card 3 should focus card 2
        mock_card3.has_focus = True
        actions.prev_sentence()
        mock_card2.focus.assert_called_with() # second time called now total

    def test_copy_annotation_state(self, main_window):
        """Test that copy_annotation updates ApplicationState."""
        actions = main_window.action_service
        state = main_window.application_state

        # Mock a selected sentence card and token
        mock_token = MagicMock()
        mock_token.annotation = MagicMock(
            pos="N",
            gender="m",
            number="s",
            case="n",
            modern_english_meaning="king",
            root="cyning"
        )
        # Configure mock_token.annotation.to_json to return a dict
        mock_token.annotation.to_json.return_value = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "modern_english_meaning": "king",
            "root": "cyning"
        }

        mock_card = MagicMock()
        mock_card.oe_text_edit = MagicMock()
        mock_card.oe_text_edit.current_token_index.return_value = 0
        mock_card.oe_text_edit.get_token.return_value = mock_token

        state[SELECTED_SENTENCE_CARD] = mock_card

        # Trigger copy
        result = actions.copy_annotation()

        assert result is True
        assert COPIED_ANNOTATION in state
        assert state[COPIED_ANNOTATION]["pos"] == "N"
        assert state[COPIED_ANNOTATION]["modern_english_meaning"] == "king"

    @patch("oeapp.ui.main_window.AnnotateTokenCommand")
    def test_paste_annotation_state(self, mock_command, main_window):
        """Test that paste_annotation uses the copied state."""
        actions = main_window.action_service
        state = main_window.application_state

        # Setup copied annotation in state
        copied_data = {"pos": "V", "root": "gangan"}
        state[COPIED_ANNOTATION] = copied_data

        # Mock a selected token
        mock_token = MagicMock()
        mock_token.id = 123
        mock_token.annotation = None

        mock_card = MagicMock()
        mock_card.oe_text_edit = MagicMock()
        mock_card.oe_text_edit.current_token_index.return_value = 0
        mock_card.oe_text_edit.get_token.return_value = mock_token
        mock_card.sentence = MagicMock()

        state[SELECTED_SENTENCE_CARD] = mock_card
        state.command_manager = MagicMock()
        state.command_manager.execute.return_value = True
        state.session = MagicMock()

        # Trigger paste
        # We need to mock part_of_speech rendering to avoid KeyError in sidebar
        with patch.object(main_window.token_details_sidebar, 'render_token'):
            result = actions.paste_annotation()

        assert result is True
        mock_command.assert_called_once()
        # Verify that the 'after' state in the command matches our copied data
        kwargs = mock_command.call_args.kwargs
        assert kwargs["after"] == copied_data

    def test_status_bar_messages(self, main_window):
        """Test that Messages helper updates the status bar."""
        messages = main_window.messages
        messages.show_message("Test Message", duration=1000)

        # In PySide6, we can check the message directly
        assert main_window.statusBar().currentMessage() == "Test Message"

class TestMainWindowStartupDialogs:
    """Test cases for startup dialog logic."""

    @patch("oeapp.ui.main_window.Project.first")
    @patch("oeapp.ui.main_window.OpenProjectDialog")
    @patch("oeapp.ui.main_window.NewProjectDialog")
    def test_show_startup_dialog_with_projects(self, mock_new_dlg, mock_open_dlg, mock_project_first, main_window):
        """Test that OpenProjectDialog is shown if projects exist."""
        # Mock projects exist
        mock_project_first.return_value = MagicMock()

        # Trigger startup dialog logic
        main_window._show_startup_dialog()

        mock_open_dlg.assert_called_once_with(main_window)
        mock_open_dlg.return_value.execute.assert_called_once()
        mock_new_dlg.assert_not_called()

    @patch("oeapp.ui.main_window.Project.first")
    @patch("oeapp.ui.main_window.OpenProjectDialog")
    @patch("oeapp.ui.main_window.NewProjectDialog")
    def test_show_startup_dialog_no_projects(self, mock_new_dlg, mock_open_dlg, mock_project_first, main_window):
        """Test that NewProjectDialog is shown if no projects exist."""
        # Mock no projects exist
        mock_project_first.return_value = None

        # Trigger startup dialog logic
        main_window._show_startup_dialog()

        mock_new_dlg.assert_called_once_with(main_window)
        mock_new_dlg.return_value.execute.assert_called_once()
        mock_open_dlg.assert_not_called()

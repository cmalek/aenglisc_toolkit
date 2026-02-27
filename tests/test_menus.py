"""Unit tests for Menus."""

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu
import pytest

from oeapp.help.topics import HELP_TOPICS
from oeapp.ui.menus import (
    FileMenu,
    HelpMenu,
    MainMenu,
    PreferencesMenu,
    ProjectMenu,
    ToolsMenu,
)


@pytest.fixture(autouse=True)
def _cleanup_mock_window(mock_main_window):
    """Ensure menu test windows are cleaned up between tests."""
    yield
    mock_main_window.close()
    mock_main_window.deleteLater()


def _non_separator_action_texts(menu: QMenu) -> list[str]:
    """
    Return visible action text values, excluding separators.

    Args:
        menu: Menu instance under inspection.

    Returns:
        List of non-empty action text values.

    """
    return [action.text() for action in menu.actions() if not action.isSeparator()]


class TestMainMenu:
    """Test cases for MainMenu."""

    def test_main_menu_initializes(self, db_session, mock_main_window, qapp):
        """Test MainMenu initializes correctly."""
        menu = MainMenu(mock_main_window)

        assert menu.main_window == mock_main_window
        assert menu.menu is not None

    def test_main_menu_adds_menu(self, db_session, mock_main_window, qapp):
        """Test MainMenu adds menu to menu bar."""
        menu = MainMenu(mock_main_window)

        test_menu = menu.add_menu("Test Menu")

        assert isinstance(test_menu, QMenu)
        assert test_menu.title() == "Test Menu"

    def test_main_menu_builds(self, db_session, mock_main_window, qapp):
        """Test MainMenu builds all menus."""
        menu = MainMenu(mock_main_window)

        menu.build()

        # Should have file_menu reference
        assert menu.file_menu is not None


class TestFileMenu:
    """Test cases for FileMenu."""

    def test_file_menu_initializes(self, db_session, mock_main_window, qapp):
        """Test FileMenu initializes correctly."""
        main_menu = MainMenu(mock_main_window)

        file_menu = FileMenu(main_menu, mock_main_window)

        assert file_menu.main_window == mock_main_window
        assert file_menu.main_menu == main_menu
        assert file_menu.file_menu is not None

    def test_file_menu_has_actions(self, db_session, mock_main_window, qapp):
        """Test FileMenu has expected actions."""
        main_menu = MainMenu(mock_main_window)

        file_menu = FileMenu(main_menu, mock_main_window)

        # Check that menu has actions (exact count may vary)
        actions = file_menu.file_menu.actions()
        assert len(actions) > 0


class TestProjectMenu:
    """Test cases for ProjectMenu."""

    def test_project_menu_creates_menu(self, db_session, mock_main_window, qapp):
        """Test ProjectMenu creates menu."""
        main_menu = MainMenu(mock_main_window)

        # ProjectMenu creates menu when instantiated
        project_menu = ProjectMenu(main_menu, mock_main_window)

        # Should not raise error
        assert project_menu is not None

    def test_project_menu_has_edit_project_action(self, db_session, mock_main_window, qapp):
        """Test ProjectMenu has Edit Project action."""
        main_menu = MainMenu(mock_main_window)
        project_menu = ProjectMenu(main_menu, mock_main_window)

        actions = project_menu.project_menu.actions()
        texts = [a.text() for a in actions]
        assert "&Edit Project..." in texts


class TestToolsMenu:
    """Test cases for ToolsMenu."""

    def test_tools_menu_creates_menu(self, db_session, mock_main_window, qapp):
        """Test ToolsMenu creates menu."""
        main_menu = MainMenu(mock_main_window)

        # ToolsMenu creates menu when instantiated
        tools_menu = ToolsMenu(main_menu, mock_main_window)

        # Should not raise error
        assert tools_menu is not None


class TestHelpMenu:
    """Test cases for HelpMenu."""

    def test_help_menu_creates_menu(self, db_session, mock_main_window, qapp):
        """Test HelpMenu creates menu."""
        main_menu = MainMenu(mock_main_window)

        # HelpMenu creates menu when instantiated
        help_menu = HelpMenu(main_menu, mock_main_window)

        # Should not raise error
        assert help_menu is not None

    def test_help_menu_adds_topic_actions_on_macos(
        self, db_session, mock_main_window, qapp, monkeypatch
    ):
        """Help menu should include topic actions on macOS."""
        monkeypatch.setattr("oeapp.ui.menus.sys.platform", "darwin")
        main_menu = MainMenu(mock_main_window)
        help_menu = HelpMenu(main_menu, mock_main_window)
        action_texts = _non_separator_action_texts(help_menu.help_menu)

        assert "&Help" in action_texts
        for topic in HELP_TOPICS:
            assert topic.title in action_texts

    def test_help_menu_topic_action_opens_requested_topic(
        self, db_session, mock_main_window, qapp, monkeypatch
    ):
        """Selecting a macOS topic action should open that help topic."""
        monkeypatch.setattr("oeapp.ui.menus.sys.platform", "darwin")
        main_menu = MainMenu(mock_main_window)
        help_menu = HelpMenu(main_menu, mock_main_window)

        topic_action = next(
            action
            for action in help_menu.help_menu.actions()
            if action.text() == "Keybindings"
        )
        topic_action.trigger()

        mock_main_window.show_help.assert_any_call(topic="Keybindings")

    def test_help_menu_does_not_add_topic_actions_off_macos(
        self, db_session, mock_main_window, qapp, monkeypatch
    ):
        """Help menu should not include topic actions on non-macOS platforms."""
        monkeypatch.setattr("oeapp.ui.menus.sys.platform", "win32")
        main_menu = MainMenu(mock_main_window)
        help_menu = HelpMenu(main_menu, mock_main_window)
        action_texts = _non_separator_action_texts(help_menu.help_menu)
        topic_titles = {topic.title for topic in HELP_TOPICS}

        assert "&Help" in action_texts
        assert topic_titles.isdisjoint(action_texts)

    def test_help_topic_actions_use_no_role_on_macos(
        self, db_session, mock_main_window, qapp, monkeypatch
    ):
        """Help topic actions should avoid macOS text heuristics."""
        monkeypatch.setattr("oeapp.ui.menus.sys.platform", "darwin")
        monkeypatch.setattr("oeapp.ui.menus._is_offscreen_qt_platform", lambda: False)
        main_menu = MainMenu(mock_main_window)
        help_menu = HelpMenu(main_menu, mock_main_window)

        topic_action_texts = {topic.title for topic in HELP_TOPICS}
        for action in help_menu.help_menu.actions():
            if action.text() in topic_action_texts:
                assert action.menuRole() == QAction.MenuRole.NoRole

    def test_help_settings_topic_still_opens_help_topic_on_macos(
        self, db_session, mock_main_window, qapp, monkeypatch
    ):
        """The Settings help topic should still open help, not preferences."""
        monkeypatch.setattr("oeapp.ui.menus.sys.platform", "darwin")
        main_menu = MainMenu(mock_main_window)
        help_menu = HelpMenu(main_menu, mock_main_window)

        settings_topic_action = next(
            action
            for action in help_menu.help_menu.actions()
            if action.text() == "Settings"
        )
        settings_topic_action.trigger()

        mock_main_window.show_help.assert_any_call(topic="Settings")
        mock_main_window.show_settings_dialog.assert_not_called()


class TestPreferencesMenu:
    """Test cases for PreferencesMenu."""

    def test_preferences_menu_creates_menu(self, db_session, mock_main_window, qapp):
        """Test PreferencesMenu creates menu."""
        main_menu = MainMenu(mock_main_window)
        # FileMenu must be created first
        FileMenu(main_menu, mock_main_window)

        # PreferencesMenu creates menu when instantiated
        preferences_menu = PreferencesMenu(main_menu, mock_main_window)

        # Should not raise error
        assert preferences_menu is not None

    def test_preferences_action_uses_preferences_role_on_macos(
        self, db_session, mock_main_window, qapp, monkeypatch
    ):
        """macOS preferences action should use PreferencesRole and open settings."""
        monkeypatch.setattr("oeapp.ui.menus.sys.platform", "darwin")
        monkeypatch.setattr("oeapp.ui.menus._is_offscreen_qt_platform", lambda: False)
        main_menu = MainMenu(mock_main_window)
        FileMenu(main_menu, mock_main_window)
        PreferencesMenu(main_menu, mock_main_window)

        preferences_action = next(
            action
            for action in main_menu.file_menu.actions()
            if action.text() == "&Preferences..."
        )
        assert preferences_action.menuRole() == QAction.MenuRole.PreferencesRole

        preferences_action.trigger()
        mock_main_window.show_settings_dialog.assert_called_once()

    def test_preferences_menu_non_macos_branch_creates_settings_action(
        self, db_session, mock_main_window, qapp, monkeypatch
    ):
        """Windows/Linux preferences entry should exist and open settings."""
        monkeypatch.setattr("oeapp.ui.menus.sys.platform", "win32")
        main_menu = MainMenu(mock_main_window)
        FileMenu(main_menu, mock_main_window)
        PreferencesMenu(main_menu, mock_main_window)

        settings_action = next(
            action
            for action in main_menu.file_menu.actions()
            if action.text() == "&Settings..."
        )
        settings_action.trigger()
        mock_main_window.show_settings_dialog.assert_called_once()

"""Unit tests for Menus."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QMainWindow, QMenuBar, QMenu

from oeapp.ui.menus import MainMenu, FileMenu, ProjectMenu, ToolsMenu, HelpMenu, PreferencesMenu


class MockMainWindow(QMainWindow):
    """Mock main window for testing menus."""

    def __init__(self):
        super().__init__()
        self.session = None
        self.current_project_id = None
        self.action_service = MagicMock()
        self.backup_service = MagicMock()
        self.show_information = MagicMock()
        self.show_warning = MagicMock()
        self.show_error = MagicMock()
        self.save_project = MagicMock()
        self.export_project_docx = MagicMock()
        self.new_project = MagicMock()
        self.open_project = MagicMock()
        self.delete_project = MagicMock()
        self.append_text = MagicMock()
        self.backup_now = MagicMock()
        self.restore_backup = MagicMock()
        self.view_backups = MagicMock()
        self.show_settings = MagicMock()
        self.show_help = MagicMock()
        self.show_restore_dialog = MagicMock()
        self.show_backups_dialog = MagicMock()
        self.import_project_json = MagicMock()
        self.export_project_json = MagicMock()
        self.show_settings_dialog = MagicMock()


class TestMainMenu:
    """Test cases for MainMenu."""

    def test_main_menu_initializes(self, qapp):
        """Test MainMenu initializes correctly."""
        main_window = MockMainWindow()
        menu = MainMenu(main_window)

        assert menu.main_window == main_window
        assert menu.menu is not None

    def test_main_menu_adds_menu(self, qapp):
        """Test MainMenu adds menu to menu bar."""
        main_window = MockMainWindow()
        menu = MainMenu(main_window)

        test_menu = menu.add_menu("Test Menu")

        assert isinstance(test_menu, QMenu)
        assert test_menu.title() == "Test Menu"

    def test_main_menu_builds(self, qapp):
        """Test MainMenu builds all menus."""
        main_window = MockMainWindow()
        menu = MainMenu(main_window)

        menu.build()

        # Should have file_menu reference
        assert menu.file_menu is not None


class TestFileMenu:
    """Test cases for FileMenu."""

    def test_file_menu_initializes(self, qapp):
        """Test FileMenu initializes correctly."""
        main_window = MockMainWindow()
        main_menu = MainMenu(main_window)

        file_menu = FileMenu(main_menu, main_window)

        assert file_menu.main_window == main_window
        assert file_menu.main_menu == main_menu
        assert file_menu.file_menu is not None

    def test_file_menu_has_actions(self, qapp):
        """Test FileMenu has expected actions."""
        main_window = MockMainWindow()
        main_menu = MainMenu(main_window)

        file_menu = FileMenu(main_menu, main_window)

        # Check that menu has actions (exact count may vary)
        actions = file_menu.file_menu.actions()
        assert len(actions) > 0


class TestProjectMenu:
    """Test cases for ProjectMenu."""

    def test_project_menu_creates_menu(self, qapp):
        """Test ProjectMenu creates menu."""
        main_window = MockMainWindow()
        main_menu = MainMenu(main_window)

        # ProjectMenu creates menu when instantiated
        project_menu = ProjectMenu(main_menu, main_window)

        # Should not raise error
        assert project_menu is not None


class TestToolsMenu:
    """Test cases for ToolsMenu."""

    def test_tools_menu_creates_menu(self, qapp):
        """Test ToolsMenu creates menu."""
        main_window = MockMainWindow()
        main_menu = MainMenu(main_window)

        # ToolsMenu creates menu when instantiated
        tools_menu = ToolsMenu(main_menu, main_window)

        # Should not raise error
        assert tools_menu is not None


class TestHelpMenu:
    """Test cases for HelpMenu."""

    def test_help_menu_creates_menu(self, qapp):
        """Test HelpMenu creates menu."""
        main_window = MockMainWindow()
        main_menu = MainMenu(main_window)

        # HelpMenu creates menu when instantiated
        help_menu = HelpMenu(main_menu, main_window)

        # Should not raise error
        assert help_menu is not None


class TestPreferencesMenu:
    """Test cases for PreferencesMenu."""

    def test_preferences_menu_creates_menu(self, qapp):
        """Test PreferencesMenu creates menu."""
        main_window = MockMainWindow()
        main_menu = MainMenu(main_window)
        # FileMenu must be created first
        FileMenu(main_menu, main_window)

        # PreferencesMenu creates menu when instantiated
        preferences_menu = PreferencesMenu(main_menu, main_window)

        # Should not raise error
        assert preferences_menu is not None


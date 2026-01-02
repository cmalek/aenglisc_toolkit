"""Unit tests for Menus."""

from PySide6.QtWidgets import QMenu

from oeapp.ui.menus import MainMenu, FileMenu, ProjectMenu, ToolsMenu, HelpMenu, PreferencesMenu


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


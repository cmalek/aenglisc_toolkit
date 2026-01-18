import sys
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QMenuBar

from oeapp.models.project import Project
from oeapp.state import CURRENT_PROJECT_ID
from oeapp.ui.dialogs import (
    AnnotationPresetManagementDialog,
    AppendTextDialog,
    NewProjectDialog,
    OpenProjectDialog,
)
from oeapp.ui.dialogs.log_viewer import LogViewerDialog
from oeapp.ui.full_translation_window import FullTranslationWindow

# Import AnnotationPresetManagementDialog lazily when needed to avoid import-time issues

if TYPE_CHECKING:
    from oeapp.ui.main_window import MainWindow


class MainMenu:
    """Main application menu."""

    def __init__(self, main_window: "MainWindow") -> None:
        """
        Initialize main menu.

        Args:
            main_window: Main window instance

        """
        #: Main window instance
        self.main_window = main_window
        #: Menu bar
        self.menu = self.main_window.menuBar()
        #: File menu

    def add_menu(self, menu: str) -> QMenu:
        """
        Add a menu to the main menu bar.

        Args:
            menu: title of the menu

        Returns:
            The added menu instance

        """
        return self.menu.addMenu(menu)

    def build(self) -> None:
        """Build the main menu."""
        # Save a reference to the file menu so PreferencesMenu can find it,
        # if needed.
        self.file_menu_obj = FileMenu(self, self.main_window)
        self.file_menu = self.file_menu_obj.file_menu
        self.project_menu = ProjectMenu(self, self.main_window)
        self.tools_menu = ToolsMenu(self, self.main_window)
        self.window_menu_obj = WindowMenu(self, self.main_window)
        self.help_menu = HelpMenu(self, self.main_window)
        # This must come after the file menu so we can find the right place for
        # the menu entry based on OS; on macOS, it goes in the application menu,
        # on Windows/Linux, it goes in the File menu.
        self.preferences_menu = PreferencesMenu(self, self.main_window)


class WindowMenu:
    """
    A "Window" menu to be added to the main menu bar.
    """

    def __init__(self, main_menu: MainMenu, main_window: "MainWindow") -> None:
        self.main_window = main_window
        self.main_menu = main_menu
        self._full_window: FullTranslationWindow
        self.populate()

    def populate(self) -> None:
        """
        Populate the window menu with the following actions:

        - Full Translation
        """
        self.window_menu = self.main_menu.add_menu("&Window")

        full_translation_action = QAction("&Full Translation", self.window_menu)
        full_translation_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        full_translation_action.triggered.connect(self._show_full_translation)
        self.window_menu.addAction(full_translation_action)

    # ------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------

    def _show_full_translation(self) -> None:
        """
        Event handler for full translation menu item: Show the full translation window.
        """
        project_id = self.main_window.application_state.get(CURRENT_PROJECT_ID)
        if not project_id:
            self.main_window.messages.show_warning("No project open")
            return

        project = Project.get(project_id)
        if not project:
            self.main_window.messages.show_error("Could not load project")
            return

        if not hasattr(self, "_full_window") or not self._full_window.isVisible():
            self._full_window = FullTranslationWindow(project, self.main_window)
            self._full_window.show()
        else:
            self._full_window.raise_()
            self._full_window.activateWindow()


class FileMenu:
    """
    A "File" menu to be added to the main menu bar with the following actions:

    - New Project...
    - Open Project...
    - Save
    - Export...
    - Filter Annotations...

    Args:
        main_menu: Main menu instance
        main_window: Main window instance

    """

    def __init__(self, main_menu: MainMenu, main_window: "MainWindow") -> None:
        """
        Initialize file menu.
        """
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Populate the file menu with the following actions:

        This means adding a "File" menu to the main menu bar, with the following
        actions: with the following actions:

        - New Project...
        - Open Project...
        - Save
        - Export...
        - Filter Annotations...

        """
        # Store reference for preferences menu
        self.file_menu = self.main_menu.add_menu("&File")

        new_action = QAction("&New Project...", self.file_menu)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(
            lambda: NewProjectDialog(self.main_window).execute()
        )
        self.file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self.file_menu)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(
            lambda: OpenProjectDialog(self.main_window).execute()
        )
        self.file_menu.addAction(open_action)

        delete_action = QAction("&Delete Project...", self.file_menu)
        delete_action.triggered.connect(self.main_window.action_service.delete_project)
        self.file_menu.addAction(delete_action)

        self.file_menu.addSeparator()

        save_action = QAction("&Save", self.file_menu)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.main_window.save_project)
        self.file_menu.addAction(save_action)

        export_action = QAction("&DOCX Export...", self.file_menu)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(
            self.main_window.action_service.export_project_docx
        )
        self.file_menu.addAction(export_action)


class ToolsMenu:
    """
    A "Tools" menu to be added to the main menu bar with the following actions:

    - Backup Now
    - Restore...
    - Backups...
    """

    def __init__(self, main_menu: MainMenu, main_window: "MainWindow") -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self._log_viewer: LogViewerDialog
        self.populate()

    def populate(self) -> None:
        """
        Create tools menu.

        This means adding a "Tools" menu to the main menu bar, with the
        following actions: with the following actions:

        - Backup Now
        - Restore...
        - Backups...
        """
        self.tools_menu = self.main_menu.add_menu("&Tools")

        backup_action = QAction("&Backup Now", self.tools_menu)
        backup_action.triggered.connect(self.main_window.action_service.backup_now)
        self.tools_menu.addAction(backup_action)

        restore_action = QAction("&Restore...", self.tools_menu)
        restore_action.triggered.connect(self.main_window.show_restore_dialog)
        self.tools_menu.addAction(restore_action)

        backups_view_action = QAction("&Backups...", self.tools_menu)
        backups_view_action.triggered.connect(self.main_window.show_backups_dialog)
        self.tools_menu.addAction(backups_view_action)

        view_logs_action = QAction("&View Logs", self.tools_menu)
        view_logs_action.triggered.connect(self._show_log_viewer)
        self.tools_menu.addAction(view_logs_action)

        self.tools_menu.addSeparator()

        pos_presets_action = QAction("POS &Presets...", self.tools_menu)

        # Connect signal using a named function for better debugging
        def show_dialog():
            sys.stderr.flush()
            self._show_pos_presets_dialog()

        pos_presets_action.triggered.connect(show_dialog)
        self.tools_menu.addAction(pos_presets_action)

    # ------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------

    def _show_pos_presets_dialog(self) -> None:
        """
        Event handler for POS presets management menu item: Show the POS presets
        management dialog.
        """
        dialog = AnnotationPresetManagementDialog()
        dialog.exec()

    def _show_log_viewer(self) -> None:
        """
        Event handler for log viewer menu item: Show the log viewer dialog.
        """
        if not hasattr(self, "_log_viewer") or not self._log_viewer.isVisible():
            self._log_viewer = LogViewerDialog(self.main_window)
            self._log_viewer.show()
        else:
            self._log_viewer.raise_()
            self._log_viewer.activateWindow()


class PreferencesMenu:
    """
    A "Preferences" menu to be added to the main menu bar with the following
    actions:

    - Preferences...
    """

    def __init__(self, main_menu: MainMenu, main_window: "MainWindow") -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Populate the preferences menu with the following actions:

        - Preferences...

        On macOS, this goes in the application menu.
        On Windows/Linux, this goes in the File menu.

        """
        if sys.platform == "darwin":
            # macOS: Add to application menu (first menu, typically app name)
            # The application menu is automatically created by Qt on macOS
            # We need to find it by looking for menus

            menu_bar = self.main_window.menuBar()
            if isinstance(menu_bar, QMenuBar):
                actions = menu_bar.actions()
                if actions:
                    app_menu_action = actions[0]
                    app_menu = app_menu_action.menu()
                    if isinstance(app_menu, QMenu):
                        app_menu.addSeparator()
                        preferences_action = QAction("&Preferences...", app_menu)
                        preferences_action.setShortcut(QKeySequence("Ctrl+,"))
                        preferences_action.triggered.connect(
                            self.main_window.show_settings_dialog
                        )
                        app_menu.addAction(preferences_action)
        else:
            # Windows/Linux: Add to File menu
            self.main_menu.file_menu.addSeparator()
            settings_action = QAction("&Settings...", self.file_menu)
            settings_action.triggered.connect(self.main_window.show_settings_dialog)
            self.main_menu.file_menu.addAction(settings_action)


class ProjectMenu:
    """
    A "Project" menu to be added to the main menu bar with the following actions:

    - Append OE text...
    - Export...
    - Import...
    """

    def __init__(self, main_menu: MainMenu, main_window: "MainWindow") -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Populate the project menu with the following actions:

        This means adding a "Project" menu to the main menu bar, with the
        following actions: with the following actions:

        - Edit Project...
        - Append OE text...
        - Export...
        - Import...
        """
        self.project_menu = self.main_menu.add_menu("&Project")

        edit_action = QAction("&Edit Project...", self.project_menu)
        edit_action.triggered.connect(self.main_window.action_service.edit_project)
        self.project_menu.addAction(edit_action)

        append_action = QAction("Append &OE text...", self.project_menu)
        append_action.triggered.connect(
            lambda: AppendTextDialog(self.main_window).execute()
        )
        self.project_menu.addAction(append_action)

        self.project_menu.addSeparator()

        export_action = QAction("&Export...", self.project_menu)
        export_action.triggered.connect(
            self.main_window.action_service.export_project_json
        )
        self.project_menu.addAction(export_action)

        import_action = QAction("&Import...", self.project_menu)
        import_action.triggered.connect(
            self.main_window.action_service.import_project_json
        )
        self.project_menu.addAction(import_action)


class HelpMenu:
    """
    A "Help" menu to be added to the main menu bar with the following actions:

    - Help
    """

    def __init__(self, main_menu: MainMenu, main_window: "MainWindow") -> None:
        #: Main window instance
        self.main_window = main_window
        #: Main menu instance
        self.main_menu = main_menu
        self.populate()

    def populate(self) -> None:
        """
        Adding a "Help" menu to the main menu bar, with the following actions:

        - Help
        """
        self.help_menu = self.main_menu.add_menu("&Help")

        help_action = QAction("&Help", self.help_menu)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(lambda: self.main_window.show_help())
        self.help_menu.addAction(help_action)

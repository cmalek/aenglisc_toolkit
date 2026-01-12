"""Main application window."""

import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from oeapp.commands import (
    AnnotateTokenCommand,
)
from oeapp.exc import MigrationFailed
from oeapp.models.project import Project
from oeapp.services import (
    AutosaveService,
    BackupService,
    DOCXExporter,
    MigrationService,
    ProjectExporter,
    ProjectImporter,
)
from oeapp.state import (
    COPIED_ANNOTATION,
    CURRENT_PROJECT_ID,
    SELECTED_SENTENCE_CARD,
    ApplicationState,
)
from oeapp.ui.dialogs import (
    BackupsViewDialog,
    DeleteProjectDialog,
    EditProjectDialog,
    ImportProjectDialog,
    MigrationFailureDialog,
    NewProjectDialog,
    OpenProjectDialog,
    RestoreDialog,
    SettingsDialog,
)
from oeapp.ui.dialogs.help_dialog import HelpDialog
from oeapp.ui.menus import MainMenu
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.shortcuts import GlobalShortcuts
from oeapp.ui.token_details_sidebar import TokenDetailsSidebar
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.idiom import Idiom
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class MainWindow(QMainWindow):
    """Main application window."""

    #: Main window geometry
    MAIN_WINDOW_GEOMETRY: Final[tuple[int, int, int, int]] = (100, 100, 1600, 800)
    #: Sidebar Width
    SIDEBAR_WIDTH: Final[int] = 350
    #: Sidebar Style
    SIDEBAR_STYLE: Final[str] = (
        "background-color: #f5f5f5; border-left: 1px solid #ddd;"
    )

    def __init__(self) -> None:
        super().__init__()
        #: Messages
        self.messages = Messages(self)
        #: Backup service
        self.backup_service = BackupService()
        #: Backup check timer
        self.backup_timer: QTimer | None = None

        # Handle migrations with backup/restore on failure
        # Note: session is created after migrations to avoid issues
        self._handle_migrations()

        #: Sentence cards
        self.sentence_cards: list[SentenceCard] = []
        #: Autosave service
        self.autosave_service: AutosaveService | None = None
        #: Main window actions
        self.action_service = MainWindowActions(self)
        #: The application state
        self.application_state = ApplicationState()
        self.application_state.reset()
        self.application_state.set_main_window(self)

        self.content_layout: QVBoxLayout | None = None
        # Build the main window
        self.build()

        # Setup backup checking
        self._setup_backup_checking()

    def build(self) -> None:
        """
        Build the main window.

        - Setup the main window.
        - Initialize the project UI class.
        - Setup the main menu.
        - Setup global shortcuts.

        """
        self.build_main_window()
        # Create the project UI.  This has to be done after the main window is
        # built because various widgets need to exist in the main window so that
        # the project UI can access them.
        self.project_ui = ProjectUI(self)
        MainMenu(self).build()
        GlobalShortcuts(self).execute()

    def build_main_window(self) -> None:
        """
        Set up the main window.
        """
        # Create the QApplicaiton
        self.create_application()
        # Create a two-column layout for the main window.
        central_layout = self.build_main_container()
        # Create the main content area.  This is a scroll area that contains the
        # sentence cards.
        self.main_column = self.build_main_content_area()
        self.content_layout = self.build_main_content(self.main_column, central_layout)
        self.token_details_sidebar = self.build_sidebar_area(central_layout)
        self.show_empty(self.content_layout)

    def create_application(self) -> None:
        """
        Build the QApplication window.
        """
        self.setWindowTitle("Ænglisc Toolkit")
        # Set window icon from application icon
        app = QApplication.instance()
        if isinstance(app, QApplication) and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())
        self.setGeometry(100, 100, 1600, 800)

    def show_empty(self, layout: QVBoxLayout) -> None:
        """
        Show the empty state.
        """
        # Status bar for autosave status
        self.messages.show_message("Ready")
        welcome_label = QLabel(
            "Welcome to Ænglisc Toolkit\n\nUse File → New Project to get started"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 14pt; color: #666; padding: 50px;")
        layout.addWidget(welcome_label)

    def build_main_container(self) -> QHBoxLayout:
        """
        Build the content area widget.  This is where the columns are located.

        Returns:
            tuple[QWidget, QHBoxLayout]: The main window's content area widget
            and layout

        """
        # Central widget with two-column layout
        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.setCentralWidget(central_widget)
        return central_layout

    def build_main_content_area(self) -> QScrollArea:
        """
        Build the main content area scroll area.  This is where the sentence
        cards are located, and takes up the majority of the main window.

        Returns:
            QScrollArea: The main content area scroll area

        """
        # Left column: scroll area with sentence cards
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        return scroll_area

    def build_main_content(
        self, container: QScrollArea, layout: QHBoxLayout
    ) -> QVBoxLayout:
        """
        Build the main content area layout.  This is where the sentence cards
        are located.

        Args:
            container: The container to add the main content to
            layout: The layout to add the main content to

        Returns:
            QVBoxLayout: The main content area layout

        """
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        container.setWidget(content_widget)
        layout.addWidget(container, stretch=1)
        return content_layout

    def build_sidebar_area(self, layout: QHBoxLayout) -> TokenDetailsSidebar:
        """
        Build the sidebar area widget.  This is where the token details sidebar is
        located.

        Args:
            layout: The layout to add the sidebar to

        Returns:
            QWidget: The sidebar area widget

        """
        sidebar = TokenDetailsSidebar()
        sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar.setStyleSheet(self.SIDEBAR_STYLE)
        layout.addWidget(sidebar)
        return sidebar

    def reload_main_window(self) -> None:
        """
        Repaint the main window.
        """
        self.main_column.update()
        self.update()

    def clear_selected_tokens(self) -> None:
        """
        Clear the selected tokens from all sentence cards.
        """
        for card in self.sentence_cards:
            card.reset_selected_token()

    def _handle_migrations(self) -> None:
        """
        Handle database migrations with automatic backup and restore on failure.
        """
        settings = QSettings()
        migration_service = MigrationService()
        skip_until_version = cast(
            "str | None", settings.value("migration/skip_until_version", None, type=str)
        )
        try:
            result = migration_service.migrate(skip_until_version)
        except MigrationFailed as e:
            dialog = MigrationFailureDialog(
                self,
                e.error,
                e.backup_app_version,
            )
            settings.setValue(
                "migration/last_working_version",
                e.backup_migration_version,
            )
            dialog.execute()
            sys.exit(1)

        if result.migration_version:
            settings.setValue(
                "migration/last_working_version",
                result.migration_version,
            )
        if result.app_version:
            settings.setValue(
                "app/current_version",
                result.app_version,
            )

    def _setup_backup_checking(self) -> None:
        """Setup periodic backup checking."""
        # Check every 5 minutes if backup is needed
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self._check_backup)
        self.backup_timer.start(5 * 60 * 1000)  # 5 minutes in milliseconds

        # Also check on startup
        self._check_backup()

    def _check_backup(self) -> None:
        """Check if backup is needed and create one if so."""
        if self.backup_service.should_backup():
            backup_path = self.backup_service.create_backup()
            if backup_path:
                self.messages.show_message("Backup created", duration=2000)

    def _show_startup_dialog(self) -> None:
        """
        Show the appropriate startup dialog based on whether projects exist.

        - If there are no projects in the database, show NewProjectDialog.
        - If there are projects, show OpenProjectDialog.
        """
        # Check if there are any projects in the database
        if bool(Project.first()) and self.application_state.session:
            # Projects exist, show OpenProjectDialog
            OpenProjectDialog(self).execute()
        else:
            # No projects exist, show NewProjectDialog
            NewProjectDialog(self).execute()

    def ensure_visible(self, widget: QWidget) -> None:
        """
        Ensure a widget is visible.

        Args:
            widget: Widget to ensure visible

        """
        self.main_column.ensureWidgetVisible(widget)

    def show_help(self, topic: str | None = None) -> None:
        """
        Show help dialog.

        Args:
            topic: Optional topic to display initially

        """
        dialog = HelpDialog(topic=topic, parent=self)
        dialog.show()

    def show_settings_dialog(self) -> None:
        """
        Show settings dialog.
        """
        dialog = SettingsDialog(self)
        dialog.execute()

    def show_restore_dialog(self) -> None:
        """
        Show restore dialog.
        """
        dialog = RestoreDialog(self)
        dialog.execute()
        # After restore, we may need to reload
        if CURRENT_PROJECT_ID in self.application_state:
            project = Project.get(
                self.application_state[CURRENT_PROJECT_ID],
            )
            if project:
                self.project_ui.load(project)

    def show_backups_dialog(self) -> None:
        """
        Show backups view dialog.
        """
        dialog = BackupsViewDialog(self)
        dialog.execute()

    def save_project(self) -> None:
        """
        Save the current project.
        """
        self.project_ui.save()

    def load_project(self, project: Project) -> None:
        """
        Load the the project.

        Args:
            project: Project to load

        """
        self.project_ui.load(project)

    def reload_project(self) -> None:
        """
        Reload the entire project structure from database.

        This is needed after structural changes like merge/undo merge
        that change the number of sentences.
        """
        self.project_ui.reload()

    def refresh_project(self) -> None:
        """
        Refresh all the sentence cards from the database.

        - If the current project ID is not set, do nothing.
        - Reload annotations for all sentence cards.
        """
        self.project_ui.refresh()


class MainWindowActions:
    """
    Main window actions.  We separate the work from the UI to make the code more
    readable and maintainable.

    Args:
        main_window: Main window instance

    """

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize main window actions.
        """
        self.main_window = main_window
        #: Backup service
        self.backup_service = BackupService()
        #: Application state
        self.application_state = ApplicationState()
        #: Sentence cards (reference to main_window's list)
        self.sentence_cards = main_window.sentence_cards
        #: Messages
        self.messages = main_window.messages

    @property
    def command_manager(self):
        """Get the current command manager from main window."""
        return self.application_state.command_manager

    @property
    def autosave_service(self):
        """Get the current autosave service from main window."""
        return self.main_window.autosave_service

    def next_sentence(self) -> None:
        """
        Navigate to next sentence.

        - If no sentence card is focused, the first sentence card is focused.
        - If the last sentence card is focused, the last sentence card is focused.

        """
        if not self.sentence_cards:
            return

        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.has_focus:
                current_index = i
                break

        if current_index == -1:
            self.sentence_cards[0].focus()
        elif current_index < len(self.sentence_cards) - 1:
            self.sentence_cards[current_index + 1].focus()

    def prev_sentence(self) -> None:
        """
        Navigate to previous sentence.

        - If no sentence card is focused, the last sentence card is focused.
        - If the first sentence card is focused, the first sentence card is focused.

        """
        if not self.sentence_cards:
            return

        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.has_focus:
                current_index = i
                break

        if current_index == -1:
            self.sentence_cards[-1].focus()
        elif current_index > 0:
            self.sentence_cards[current_index - 1].focus()

    def focus_translation(self) -> None:
        """
        Focus translation field of current sentence.

        - If there is no sentence card focused, do nothing.
        - If no sentence card is focused, the translation field of the last
          sentence card is focused.
        - If the translation field of the last sentence card is focused, the
          translation field of the first sentence card is focused.

        """
        if not self.sentence_cards:
            return
        for card in self.sentence_cards:
            if card.has_focus:
                card.focus_translation()
                break

    def copy_annotation(self) -> bool:
        """
        Copy the annotation from the currently selected token.

        Returns:
            True if annotation was copied, False otherwise.
            Returns False if no token is selected (allows normal clipboard behavior).

        """
        # Check if a token is selected
        card = self.application_state.get(SELECTED_SENTENCE_CARD)
        if card is None:
            return False
        current_token_index = card.oe_text_edit.current_token_index()
        if current_token_index is None:
            # No token selected, allow normal clipboard behavior
            return False

        # Get the selected token
        order_index = current_token_index
        token = card.oe_text_edit.get_token(order_index)
        if not token:
            return False

        # Check if token has an annotation
        if not token.annotation:
            self.messages.show_message("No annotation to copy")
            return True  # Return True to indicate we handled the event

        # Extract annotation fields
        annotation = token.annotation
        self.application_state[COPIED_ANNOTATION] = annotation.to_json()
        self.messages.show_message("Annotation copied")
        return True

    def paste_annotation(self) -> bool:
        """
        Paste the copied annotation onto the currently selected token.

        Returns:
            True if annotation was pasted, False otherwise.
            Returns False if no token is selected (allows normal clipboard behavior).

        """
        # Check if a token is selected
        card = self.application_state.get(SELECTED_SENTENCE_CARD)
        if card is None:
            return False
        current_token_index = card.oe_text_edit.selector.current_token_index()
        if card is None or current_token_index is None:
            # No token selected, allow normal clipboard behavior
            return False

        # Check if there's a copied annotation
        if COPIED_ANNOTATION not in self.application_state:
            self.messages.show_message("No annotation to paste")
            return True  # Return True to indicate we handled the event

        # Get the selected token
        order_index = current_token_index
        token = card.oe_text_edit.get_token(order_index)
        if not token or not token.id:
            return False

        # Capture current annotation state for undo
        before_state: dict[str, Any] = {}
        if token.annotation:
            annotation = token.annotation
            before_state = annotation.to_json()

        # Create and execute the command
        if not self.command_manager:
            self.messages.show_message("Command manager not available")
            return True

        command = AnnotateTokenCommand(
            token_id=token.id,
            before=before_state,
            after=self.application_state[COPIED_ANNOTATION],
        )

        if self.command_manager.execute(command):
            # Refresh the token from database to update relationships
            self.application_state.session.refresh(token)

            # Refresh the sentence card
            card.set_tokens()

            # Update sidebar if the pasted token is currently displayed
            self.main_window.token_details_sidebar.render_token(token, card.sentence)

            self.messages.show_message("Annotation pasted")
        else:
            self.messages.show_message("Paste failed")

        return True

    def autosave(self) -> None:
        """
        Do an autosave operation.

        - If the current project ID is not set, do nothing.
        - Sanitize notes before committing to prevent SQLAlchemy mapping errors
        - Save the current project.
        - Show a message in the status bar that the project has been saved.

        """
        project = Project.get(self.application_state[CURRENT_PROJECT_ID])
        if project is None:
            return

        # Sanitize notes before committing to prevent SQLAlchemy mapping errors
        # Ensure nullable foreign keys are None instead of 0 or False
        for sentence in project.sentences:
            for note in sentence.notes:
                if note.start_token == 0 or note.start_token is False:
                    note.start_token = None
                if note.end_token == 0 or note.end_token is False:
                    note.end_token = None

        project.save()
        self.messages.show_message("Saved")

    def import_project_json(self) -> None:
        """
        Import project from JSON format.
        """
        # Get file path from user
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window, "Import Project", "", "JSON Files (*.json);;All Files (*)"
        )

        # If the user cancels the dialog, do nothing
        if not file_path:
            return

        try:
            # Import project
            imported_project, was_renamed = ProjectImporter().import_project_json(
                file_path
            )

            # Show confirmation dialog
            dialog = ImportProjectDialog(
                self.main_window, imported_project, was_renamed
            )
            if dialog.execute():
                # User chose to open the project
                ProjectUI(self.main_window).load(imported_project)
                self.main_window.setWindowTitle(
                    f"Ænglisc Toolkit - {imported_project.name}"
                )
                self.messages.show_message("Project imported and opened", duration=3000)
            else:
                self.messages.show_message(
                    "Project imported successfully", duration=2000
                )

        except ValueError as e:
            self.messages.show_error(str(e), title="Import Error")
        except Exception as e:  # noqa: BLE001
            self.messages.show_error(
                f"An error occurred during import:\n{e!s}", title="Import Error"
            )

    def export_project_json(
        self,
        project_id: int | bool | None = None,  # noqa: FBT001
        parent: QWidget | None = None,
    ) -> bool:
        """
        Export project to JSON format.

        Note that when called as a callback from a dialog, project_id will be a boolean.

        Args:
            project_id: Optional project ID to export. If not provided, uses
                the value of :data:`CURRENT_PROJECT_ID` in :data:`application_state`.
            parent: Optional parent widget for the file dialog. If not provided,
                uses self.

        Returns:
            True if export was successful, False if canceled or failed

        """
        target_project_id = (
            project_id if project_id else self.application_state[CURRENT_PROJECT_ID]
        )
        if not self.application_state.session or not target_project_id:
            self.messages.show_warning("No project open")
            return False

        # Get project name for default filename
        project = Project.get(target_project_id)
        if project is None:
            self.messages.show_warning("Project not found")
            return False

        default_filename = ProjectExporter.sanitize_filename(project.name) + ".json"

        # Get file path from user
        dialog_parent = parent if parent is not None else self.main_window
        file_path, _ = QFileDialog.getSaveFileName(
            dialog_parent,
            "Export Project",
            default_filename,
            "JSON Files (*.json);;All Files (*)",
        )

        # If the user cancels the dialog, do nothing
        if not file_path:
            return False

        # Export project data
        exporter = ProjectExporter()
        try:
            exporter.export_project_json(target_project_id, file_path)
        except ValueError as e:
            self.messages.show_error(str(e), title="Export Error")
            return False

        self.messages.show_information(
            f"Project exported successfully to:\n{file_path}",
            title="Export Successful",
        )
        self.messages.show_message("Export completed", duration=3000)
        return True

    def delete_project(self) -> None:
        """
        Delete a project from the database.

        Creates a backup before deletion and opens DeleteProjectDialog.
        """
        # Create backup before any destructive action
        backup_path = self.main_window.backup_service.create_backup()
        if not backup_path:
            self.messages.show_error(
                "Failed to create backup. Deletion cancelled for safety.",
                title="Backup Failed",
            )
            return

        # Open delete project dialog
        dialog = DeleteProjectDialog(self.main_window)
        dialog.execute()

    def edit_project(self) -> None:
        """
        Edit the current project's metadata.
        """
        if CURRENT_PROJECT_ID not in self.application_state:
            self.messages.show_warning("No project open")
            return

        project = Project.get(self.application_state[CURRENT_PROJECT_ID])
        if project is None:
            self.messages.show_warning("Project not found")
            return

        dialog = EditProjectDialog(self.main_window, project)
        dialog.execute()

    def export_project_docx(self) -> None:
        """
        Export project to DOCX.
        """
        if (
            not self.application_state.session
            or CURRENT_PROJECT_ID not in self.application_state
        ):
            self.messages.show_warning("No project open")
            return

        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self.main_window,
            "Export Project",
            "",
            "Word Documents (*.docx);;All Files (*)",
        )

        # If the user cancels the dialog, do nothing.
        if not file_path:
            return

        # Ensure .docx extension
        if not file_path.endswith(".docx"):
            file_path += ".docx"

        exporter = DOCXExporter()
        try:
            export_success = exporter.export(
                self.application_state[CURRENT_PROJECT_ID], Path(file_path)
            )
        except PermissionError as e:
            self.messages.show_error(
                f"Export failed: Permission denied.\n{e!s}",
                title="Export Error",
            )
            return
        except OSError as e:
            self.messages.show_error(
                f"Export failed: File not found.\n{e!s}",
                title="Export Error",
            )
            return

        if export_success:
            self.messages.show_information(
                f"Project exported successfully to:\n{file_path}",
                title="Export Successful",
            )
            self.messages.show_message("Export completed", duration=3000)
        else:
            self.messages.show_warning(
                "Failed to export project. Check console for details.",
                title="Export Failed",
            )

    def backup_now(self) -> None:
        """
        Create a backup immediately.

        - Create a backup
        - Show a message in the status bar that the backup has been created

        """
        backup_path = self.backup_service.create_backup()
        if backup_path:
            self.messages.show_information(
                f"Backup created successfully:\n{backup_path.name}",
                title="Backup Complete",
            )
            self.messages.show_message("Backup created", duration=2000)
        else:
            self.messages.show_error("Failed to create backup.")


class Messages:
    """
    Helper class for showing messages in the main window.
    """

    def __init__(self, main_window: MainWindow) -> None:
        self.main_window = main_window

    def show_message(self, message: str, duration: int = 2000) -> None:
        """
        Show a message in the status bar.

        Args:
            message: Message to show

        Keyword Args:
            duration: Duration of the message in milliseconds (default: 2000)

        """
        self.main_window.statusBar().showMessage(message, duration)

    def show_warning(self, message: str, title: str = "Warning") -> None:
        """
        Show a warning message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Warning")

        """
        QMessageBox.warning(self.main_window, title, message)

    def show_error(self, message: str, title: str = "Error") -> None:
        """
        Show an error message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Error")

        """
        QMessageBox.warning(self.main_window, title, message)

    def show_information(self, message: str, title: str = "Information") -> None:
        """
        Show an information message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Information")

        """
        msg_box = QMessageBox(
            QMessageBox.Icon.Information,
            title,
            message,
            QMessageBox.StandardButton.Ok,
            self.main_window,
        )
        # Set custom icon
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        msg_box.exec()


class ProjectUI:
    """
    Build out the UI for a particular project inside the main window.

    Important:
        Only run ``ProjectUI(main_window).load(project_id)`` once the main
        window has been built, because it needs to access the main window's
        content+layout.

    """

    def __init__(self, main_window: MainWindow) -> None:
        self.main_window = main_window
        self.application_state = main_window.application_state
        self.action_service = main_window.action_service
        self.command_manager = self.action_service.command_manager
        self.sentence_cards: list[SentenceCard] = []
        self.content_layout: QVBoxLayout = cast(
            "QVBoxLayout", self.main_window.content_layout
        )
        self.token_details_sidebar = main_window.token_details_sidebar
        self.show_message = main_window.messages.show_message
        self.show_warning = main_window.messages.show_warning
        self.show_error = main_window.messages.show_error
        self.show_information = main_window.messages.show_information

    def load(self, project: Project) -> None:
        """
        Build the project.

        Args:
            project: Project to load

        """
        self.application_state[CURRENT_PROJECT_ID] = project.id

        # Initialize autosave and command manager
        self.autosave_service = AutosaveService(self.action_service.autosave)

        # Clear existing content
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().deleteLater()  # type: ignore[union-attr]

        self.sentence_cards = []
        for sentence in project.sentences:
            # Add paragraph separator if this sentence starts a paragraph
            if sentence.is_paragraph_start and len(self.sentence_cards) > 0:
                separator = QWidget()
                separator.setFixedHeight(20)
                separator.setStyleSheet(
                    "background-color: #e0e0e0; border-top: 2px solid #999;"
                )
                self.content_layout.addWidget(separator)

            card = SentenceCard(
                sentence,
                command_manager=self.application_state.command_manager,
                main_window=self.main_window,
            )
            self.sentence_cards.append(card)
            self.content_layout.addWidget(card)
            card.translation_edit.textChanged.connect(self._on_translation_changed)
            card.oe_text_edit.textChanged.connect(self._on_sentence_text_changed)
            card.sentence_merged.connect(self._on_sentence_merged)
            card.sentence_added.connect(self._on_sentence_added)
            card.sentence_deleted.connect(self._on_sentence_deleted)
            card.token_selected_for_details.connect(self._on_token_selected_for_details)
            card.idiom_selected_for_details.connect(self._on_idiom_selected_for_details)
            card.annotation_applied.connect(self._on_annotation_applied)

    def reload(self) -> None:
        """
        Reload the entire project structure from database.

        This is needed after structural changes like merge/undo merge
        that change the number of sentences.
        """
        if (
            not self.application_state.session
            or CURRENT_PROJECT_ID not in self.application_state
        ):
            return

        # Reload project from database
        project = Project.get(self.application_state[CURRENT_PROJECT_ID])
        if project is None:
            return

        # Preserve existing services
        existing_command_manager = self.command_manager
        existing_autosave = self.autosave_service

        # Refresh the project configuration (reloads all sentence cards)
        self.load(project)

        # Restore preserved services
        if existing_command_manager:
            self.command_manager = existing_command_manager
        if existing_autosave:
            self.autosave_service = existing_autosave

        # Update all sentence cards to use the preserved command manager
        for card in self.sentence_cards:
            card.command_manager = self.application_state.command_manager

        # Ensure UI is updated/repainted
        self.main_window.reload_main_window()

    def refresh(self) -> None:
        """
        Refresh all sentence cards from database.

        - If there is no database or the current project ID is not set, do nothing.
        - Reload annotations for all sentence cards.
        """
        if (
            not self.application_state.session
            or CURRENT_PROJECT_ID not in self.application_state
        ):
            return
        # Reload annotations for all cards
        for card in self.sentence_cards:
            if card.sentence.id:
                card.set_tokens()

    def save(self) -> None:
        """
        Save current project.
        """
        if (
            not self.application_state.session
            or CURRENT_PROJECT_ID not in self.application_state
        ):
            self.show_warning("No project open")
            return
        if self.autosave_service:
            self.autosave_service.save_now()
            self.show_message("Project saved")
        else:
            self.show_information("Project saved (autosave enabled)", title="Info")

    def _on_translation_changed(self) -> None:
        """
        Handle translation text change by autosaving.
        """
        if self.autosave_service:
            self.show_message("Saving...", duration=500)
            self.autosave_service.trigger()

    def _on_sentence_text_changed(self):
        """
        Handle sentence text change by autosaving.
        """
        if self.autosave_service:
            self.show_message("Saving...", duration=500)
            self.autosave_service.trigger()

    def _on_sentence_merged(self) -> None:
        """
        Handle sentence merge signal.

        Reloads the project from the database to refresh all sentence cards
        after a merge operation.

        """
        if (
            not self.application_state.session
            or CURRENT_PROJECT_ID not in self.application_state
        ):
            return

        # Reload project from database
        project = Project.get(self.application_state[CURRENT_PROJECT_ID])
        if project is None:
            return

        # Preserve existing command manager to keep undo history
        existing_command_manager = self.application_state.command_manager
        existing_autosave = self.autosave_service

        # Refresh the project configuration (reloads all sentence cards)
        self.load(project)

        # Restore preserved services
        if existing_command_manager:
            self.command_manager = existing_command_manager
        if existing_autosave:
            self.autosave_service = existing_autosave

        # Update all sentence cards to use the preserved command manager
        for card in self.sentence_cards:
            card.command_manager = self.command_manager

        # Ensure UI is updated/repainted
        self.main_window.reload_main_window()

        self.show_message("Sentences merged", duration=2000)

    def _on_sentence_added(self, sentence_id: int) -> None:
        """
        Handle sentence added signal.

        Reloads the project from the database to refresh all sentence cards
        after adding a new sentence, then puts the new sentence card in edit mode.

        Args:
            sentence_id: ID of the newly added sentence

        """
        if (
            not self.application_state.session
            or CURRENT_PROJECT_ID not in self.application_state
        ):
            return

        # Reload project from database
        project = Project.get(self.application_state[CURRENT_PROJECT_ID])
        if project is None:
            return

        # Preserve existing command manager to keep undo history
        existing_command_manager = self.application_state.command_manager
        existing_autosave = self.autosave_service

        # Refresh the project configuration (reloads all sentence cards)
        self.load(project)

        # Restore preserved services
        if existing_command_manager:
            self.command_manager = existing_command_manager
        if existing_autosave:
            self.autosave_service = existing_autosave

        # Update all sentence cards to use the preserved command manager
        for card in self.sentence_cards:
            card.command_manager = self.command_manager

        # Find the sentence card with matching sentence.id
        new_card = None
        for card in self.sentence_cards:
            if card.sentence.id == sentence_id:
                new_card = card
                break

        if new_card:
            # Scroll card into view
            self.main_window.ensure_visible(new_card)
            # Enter edit mode and focus OE text box
            new_card.enter_edit_mode()

        # Ensure UI is updated/repainted
        self.main_window.reload_main_window()

        self.show_message("Sentence added", duration=2000)

    def _on_sentence_deleted(self, sentence_id: int) -> None:  # noqa: ARG002
        """
        Handle sentence deleted signal.

        Reloads the project from the database to refresh all sentence cards
        after a deletion operation.

        Args:
            sentence_id: ID of the deleted sentence

        """
        if (
            not self.application_state.session
            or CURRENT_PROJECT_ID not in self.application_state
        ):
            return

        # Reload project from database
        project = Project.get(self.application_state[CURRENT_PROJECT_ID])
        if project is None:
            return

        # Preserve existing command manager to keep undo history
        existing_command_manager = self.application_state.command_manager
        existing_autosave = self.autosave_service

        # Refresh the project configuration (reloads all sentence cards)
        self.load(project)

        # Restore preserved services
        if existing_command_manager:
            self.command_manager = existing_command_manager
        if existing_autosave:
            self.autosave_service = existing_autosave

        # Update all sentence cards to use the preserved command manager
        for card in self.sentence_cards:
            card.command_manager = self.command_manager

        # Ensure UI is updated/repainted
        self.main_window.reload_main_window()

        self.show_message("Sentence deleted", duration=2000)

    def _on_token_selected_for_details(
        self, token: Token, sentence: Sentence, sentence_card: SentenceCard
    ) -> None:
        """
        Handle token selection for details sidebar.

        Args:
            token: Selected token
            sentence: Sentence containing the token
            sentence_card: Sentence card containing the token

        """
        # Clear selection on all other sentence cards to ensure only one selection
        # exists across the entire project view
        for other_card in self.sentence_cards:
            if other_card != sentence_card:
                other_card.clear_token_selection()

        # Check if token is being deselected (selected_token_index is None)
        if sentence_card.oe_text_edit.current_token_index() is None:
            # Clear sidebar
            self.token_details_sidebar.clear_sidebar()
            if SELECTED_SENTENCE_CARD in self.application_state:
                del self.application_state[SELECTED_SENTENCE_CARD]
        else:
            # Update sidebar with token details
            self.token_details_sidebar.render_token(token, sentence)

            # Store reference to currently selected sentence card
            self.application_state[SELECTED_SENTENCE_CARD] = sentence_card

    def _on_idiom_selected_for_details(
        self, idiom: Idiom, sentence: Sentence, sentence_card: SentenceCard
    ) -> None:
        """
        Handle idiom selection for details sidebar.

        Args:
            idiom: Selected idiom
            sentence: Sentence containing the idiom
            sentence_card: Sentence card containing the idiom

        """
        # Clear selection on all other sentence cards
        for other_card in self.sentence_cards:
            if other_card != sentence_card:
                other_card.clear_token_selection()

        # Update sidebar with idiom details
        self.token_details_sidebar.render_idiom(idiom, sentence)

        # Store reference to currently selected sentence card
        self.application_state[SELECTED_SENTENCE_CARD] = sentence_card

    def _on_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied signal.

        If the annotation is for the currently selected token in the sidebar,
        refresh the sidebar.

        Args:
            annotation: Applied annotation

        """
        # Check if this annotation is for the currently selected token
        if CURRENT_PROJECT_ID not in self.application_state:
            return
        card = self.application_state.get(SELECTED_SENTENCE_CARD)
        if card is not None and card.oe_text_edit.current_token_index() is not None:
            order_index = card.oe_text_edit.current_token_index()
            token = card.oe_text_edit.tokens_by_index.get(order_index)
            if token and token.id == annotation.token_id:
                # Refresh sidebar with updated annotation
                # Refresh token from database to ensure annotation relationship
                # is up-to-date
                if self.application_state.session:
                    self.application_state.session.refresh(token)
                self.token_details_sidebar.render_token(token, card.sentence)

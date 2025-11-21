"""Main application window."""

from pathlib import Path
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oeapp.exc import AlreadyExists
from oeapp.models.project import Project
from oeapp.models.token import Token
from oeapp.services.autosave import AutosaveService
from oeapp.services.commands import CommandManager
from oeapp.services.db import Database
from oeapp.services.export_docx import DOCXExporter
from oeapp.services.filter import FilterService
from oeapp.ui.filter_dialog import FilterDialog
from oeapp.ui.help_dialog import HelpDialog
from oeapp.ui.sentence_card import SentenceCard


class MainMenu:
    """Main application menu."""

    def __init__(self, main_window: MainWindow) -> None:
        """
        Initialize main menu.

        Args:
            main_window: Main window instance

        """
        #: Main window instance
        self.main_window = main_window
        #: Menu bar
        self.menu = self.main_window.menuBar()

    def add_file_menu(self) -> None:
        """
        Create file menu.

        This means adding a "File" menu to :attr:`self.menu`, the main menu bar,
        with the following actions:

        - New Project...
        - Open Project...
        - Save
        - Export...
        - Filter Annotations...

        """
        file_menu = self.menu.addMenu("&File")

        new_action = QAction("&New Project...", file_menu)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.main_window.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", file_menu)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.main_window.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", file_menu)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.main_window.save_project)
        file_menu.addAction(save_action)

        export_action = QAction("&Export...", file_menu)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        export_action.triggered.connect(self.main_window.export_project)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        filter_action = QAction("&Filter Annotations...", file_menu)
        filter_action.setShortcut(QKeySequence("Ctrl+F"))
        filter_action.triggered.connect(self.main_window.show_filter_dialog)
        file_menu.addAction(filter_action)

    def add_help_menu(self) -> None:
        """
        Create help menu.

        This means adding a "Help" menu to :attr:`self.menu`, the main menu bar,
        with the following actions:

        - Help
        """
        help_menu = self.menu.addMenu("&Help")

        help_action = QAction("&Help", help_menu)
        help_action.setShortcut(QKeySequence("F1"))
        help_action.triggered.connect(lambda: self.main_window.show_help())
        help_menu.addAction(help_action)

    def build(self) -> None:
        """Build the main menu."""
        self.add_file_menu()
        self.add_help_menu()


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        #: Datbase
        self.db: Database = Database()
        #: Current project ID
        self.current_project_id: int | None = None
        #: Sentence cards
        self.sentence_cards: list[SentenceCard] = []
        #: Autosave service
        self.autosave_service: AutosaveService | None = None
        #: Command manager
        self.command_manager: CommandManager | None = None
        #: Filter service
        self.filter_service: FilterService | None = None
        #: Main window actions
        self.action_service = MainWindowActions(self)

        # Build the main window
        self.build()

    def _setup_main_window(self) -> None:
        """
        Set up the main window.
        """
        self.setWindowTitle("Ænglisc Toolkit")
        # Set window icon from application icon
        app = QApplication.instance()
        if isinstance(app, QApplication) and not app.windowIcon().isNull():
            self.setWindowIcon(app.windowIcon())
        self.setGeometry(100, 100, 1200, 800)
        # Central widget with scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area = scroll_area
        self.setCentralWidget(scroll_area)
        # Content widget with layout
        content_widget = QWidget()
        self.content_layout = QVBoxLayout(content_widget)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(content_widget)
        # Status bar for autosave status
        self.show_message("Ready")
        # Initial message
        welcome_label = QLabel(
            "Welcome to Ænglisc Toolkit\n\nUse File → New Project to get started"
        )
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("font-size: 14pt; color: #666; padding: 50px;")
        self.content_layout.addWidget(welcome_label)

    def _setup_main_menu(self) -> None:
        """Set up the main menu."""
        menu = MainMenu(self)
        menu.build()

    def build(self) -> None:
        """
        Build the main window.

        - Setup the main window.
        - Setup the main menu.
        - Setup global shortcuts.

        """
        self._setup_main_window()
        self._setup_main_menu()
        self._setup_global_shortcuts()

    def _setup_global_shortcuts(self) -> None:
        """
        Set up global keyboard shortcuts for navigation.

        The following shortcuts are set up:
        - J/K for next/previous sentence
        - T for focus translation
        - Undo: Ctrl+Z
        - Redo: Ctrl+R or Ctrl+Shift+R
        """
        # J/K for next/previous sentence
        next_sentence_shortcut = QShortcut(QKeySequence("J"), self)
        next_sentence_shortcut.activated.connect(self.action_service.next_sentence)
        prev_sentence_shortcut = QShortcut(QKeySequence("K"), self)
        prev_sentence_shortcut.activated.connect(self.action_service.prev_sentence)

        # T for focus translation
        focus_translation_shortcut = QShortcut(QKeySequence("T"), self)
        focus_translation_shortcut.activated.connect(
            self.action_service.focus_translation
        )

        # Undo/Redo shortcuts
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.action_service.undo)
        redo_shortcut = QShortcut(QKeySequence("Ctrl+R"), self)
        redo_shortcut.activated.connect(self.action_service.redo)
        redo_shortcut_alt = QShortcut(QKeySequence("Ctrl+Shift+R"), self)
        redo_shortcut_alt.activated.connect(self.action_service.redo)

    def show_message(self, message: str, duration: int = 2000) -> None:
        """
        Show a message in the status bar.

        Args:
            message: Message to show

        Keyword Args:
            duration: Duration of the message in milliseconds (default: 2000)

        """
        self.statusBar().showMessage(message, duration)

    def show_warning(self, message: str, title: str = "Warning") -> None:
        """
        Show a warning message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Warning")

        """
        QMessageBox.warning(self, title, message)

    def show_error(self, message: str, title: str = "Error") -> None:
        """
        Show an error message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Error")

        """
        QMessageBox.warning(self, title, message)

    def show_information(self, message: str, title: str = "Information") -> None:
        """
        Show an information message.

        Args:
            message: Message to show

        Keyword Args:
            title: Title of the message (default: "Information")

        """
        QMessageBox.information(self, title, message)

    def ensure_visible(self, widget: QWidget) -> None:
        """
        Ensure a widget is visible.

        Args:
            widget: Widget to ensure visible

        """
        self.scroll_area.ensureWidgetVisible(widget)

    def new_project(self) -> None:
        """
        Create a new project.

        - If the user cancels the dialog, do nothing.
        - If the user enters valid Old English text, create a new project from the text.

        """
        dialog = QDialog(self)
        dialog.setWindowTitle("New Project")
        layout = QVBoxLayout(dialog)

        title_edit = QLineEdit(self)
        title_edit.setPlaceholderText("Enter project title...")
        layout.addWidget(QLabel("Project Title:"))
        layout.addWidget(title_edit)

        text_edit = QTextEdit()
        text_edit.setPlaceholderText("Paste Old English text here...")
        text_edit.setMinimumHeight(200)
        layout.addWidget(QLabel("Old English Text:"))
        layout.addWidget(text_edit)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec():
            text = text_edit.toPlainText()
            title = title_edit.text()
            if text.strip() and title.strip():
                try:
                    self._create_project_from_text(text, title)
                except AlreadyExists:
                    self.show_error(
                        f'Project with title "{title!s}" already exists. Please '
                        "choose a different title or delete the existing project."
                    )

    def _configure_project(self, project: Project) -> None:
        """
        Configure the app for the given project.

        Args:
            project: Project to configure

        """
        self.current_project_id = project.id

        # Initialize autosave and command manager
        self.autosave_service = AutosaveService(self.action_service.autosave)
        self.command_manager = CommandManager(self.db)
        self.filter_service = FilterService(self.db)

        # Clear existing content
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().setParent(None)  # type: ignore[union-attr]

        self.sentence_cards = []
        for sentence in project.sentences:
            card = SentenceCard(
                sentence, db=self.db, command_manager=self.command_manager
            )
            card.set_tokens(sentence.tokens)
            card.translation_edit.textChanged.connect(self._on_translation_changed)
            card.oe_text_edit.textChanged.connect(self._on_sentence_text_changed)
            self.sentence_cards.append(card)
            self.content_layout.addWidget(card)

    def _create_project_from_text(self, text: str, title: str) -> None:
        """
        Create a new project from the text, split into sentences, split
        sentences into tokens, and create sentence cards.

        - If the text is empty, do nothing.
        - If the text is not empty, create a new project from the text.

        Args:
            text: Old English text to process
            title: Project title

        """
        # Create project in the shared database
        project = Project.create(self.db, text, title)
        self._configure_project(project)
        self.setWindowTitle(f"Ænglisc Toolkit - {project.name}")
        self.show_message("Project created")

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

    def open_project(self) -> None:
        """
        Open an existing project.

        - If there are no projects in the database, show a message.
        - If the user cancels the dialog, do nothing.
        - If the user selects a project, load it by ID.
        """
        # Get all projects from the database
        projects = Project.list(self.db)
        if not projects:
            self.show_information(
                "No projects found. Create a new project first.",
                title="No Projects",
            )
            return

        # Create dialog to select project
        dialog = QDialog(self)
        dialog.setWindowTitle("Open Project")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Select a project to open:"))

        # Create list widget to display projects, and add items to it.
        project_list = QListWidget()
        for project in projects:
            item = QListWidgetItem(project.name)
            item.setData(Qt.ItemDataRole.UserRole, project.id)
            project_list.addItem(item)
        project_list.setCurrentRow(0)
        layout.addWidget(project_list)

        # Create button box with OK and Cancel buttons.
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec():
            # Get the selected project from the list widget.
            selected_item = project_list.currentItem()
            if selected_item:
                project_id = selected_item.data(Qt.ItemDataRole.UserRole)
                # Get the project from the database.
                project = Project.get(self.db, project_id)
                # Configure the app for the project.
                self._configure_project(project)
                # Set the window title to the project name.
                self.setWindowTitle(f"Ænglisc Toolkit - {project.name}")
                self.show_message("Project opened")

    def save_project(self) -> None:
        """
        Save current project.
        """
        if not self.db or not self.current_project_id:
            self.show_warning("No project open")
            return
        if self.autosave_service:
            self.autosave_service.save_now()
            self.show_message("Project saved")
        else:
            self.show_information("Project saved (autosave enabled)", title="Info")

    def export_project(self) -> None:
        """
        Export project to DOCX.
        """
        if not self.db or not self.current_project_id:
            self.show_warning("No project open")
            return

        # Get file path from user
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Project", "", "Word Documents (*.docx);;All Files (*)"
        )

        # If the user cancels the dialog, do nothing.
        if not file_path:
            return

        # Ensure .docx extension
        if not file_path.endswith(".docx"):
            file_path += ".docx"

        try:
            exporter = DOCXExporter(self.db)
            if exporter.export(self.current_project_id, Path(file_path)):
                self.show_information(
                    f"Project exported successfully to:\n{file_path}",
                    title="Export Successful",
                )
                self.show_message("Export completed", duration=3000)
            else:
                self.show_warning(
                    "Failed to export project. Check console for details.",
                    title="Export Failed",
                )
        except Exception as e:
            self.show_error(
                f"An error occurred during export:\n{e!s}", title="Export Error"
            )

    def show_help(self, topic: str | None = None) -> None:
        """
        Show help dialog.

        Args:
            topic: Optional topic to display initially

        """
        dialog = HelpDialog(topic=topic, parent=self)
        dialog.exec()

    def show_filter_dialog(self) -> None:
        """
        Show filter dialog.
        """
        if not self.db or not self.current_project_id:
            self.show_warning(
                "Please create or open a project first.", title="No Project"
            )
            return

        dialog = FilterDialog(
            cast("FilterService", self.filter_service),
            self.current_project_id,
            parent=self,
        )
        dialog.token_selected.connect(self.action_service.navigate_to_token)
        dialog.exec()


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
        #: Database
        self.db = main_window.db
        #: Current project ID
        self.current_project_id = main_window.current_project_id
        #: Sentence cards
        self.sentence_cards = main_window.sentence_cards
        #: Autosave service
        self.autosave_service = main_window.autosave_service
        #: Command manager
        self.command_manager = main_window.command_manager
        #: Filter service

    def next_sentence(self) -> None:
        """
        Navigate to next sentence.

        - If no sentence card is focused, the first sentence card is focused.
        - If the last sentence card is focused, the last sentence card is focused.

        """
        if not self.sentence_cards:
            self.sentence_cards[0].focus()
            return
        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.has_focus:
                current_index = i
                break
        if current_index >= 0 and current_index < len(self.sentence_cards) - 1:
            self.sentence_cards[current_index + 1].focus()

    def prev_sentence(self) -> None:
        """
        Navigate to previous sentence.

        - If no sentence card is focused, the last sentence card is focused.
        - If the first sentence card is focused, the first sentence card is focused.

        """
        if not self.sentence_cards:
            self.sentence_cards[-1].focus()
            return
        # Find currently focused sentence card
        current_index = -1
        for i, card in enumerate(self.sentence_cards):
            if card.has_focus:
                current_index = i
                break
        if current_index > 0:
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

    def undo(self) -> None:
        """
        Undo last action.

        - If there is no command manager or the command manager cannot undo, do nothing.
        - If the command manager can undo, undo the last action.
        - If the undo fails, show a message in the status bar.
        """
        if self.command_manager and self.command_manager.can_undo():
            if self.command_manager.undo():
                self.main_window.show_message("Undone")
                self.refresh_all_cards()
            else:
                self.main_window.show_message("Undo failed")

    def redo(self) -> None:
        """
        Redo last undone action.

        - If there is no command manager or the command manager cannot redo, do nothing.
        - If the command manager can redo, redo the last action.
        - If the redo fails, show a message in the status bar.
        """
        if self.command_manager and self.command_manager.can_redo():
            if self.command_manager.redo():
                self.main_window.show_message("Redone")
                self.refresh_all_cards()
            else:
                self.main_window.show_message("Redo failed")

    def refresh_all_cards(self) -> None:
        """
        Refresh all sentence cards from database.

        - If there is no database or the current project ID is not set, do nothing.
        - Reload annotations for all sentence cards.
        """
        if not self.db or not self.current_project_id:
            return
        # Reload annotations for all cards
        for card in self.sentence_cards:
            if card.sentence.id:
                card.set_tokens(card.sentence.tokens)

    def autosave(self) -> None:
        """
        Do an autosave operation.

        - If there is no database or the current project ID is not set, do nothing.
        - Save the current project.
        - Show a message in the status bar that the project has been saved.

        """
        assert self.db is not None, "Database not initialized"  # noqa: S101
        assert self.current_project_id is not None, "Current project ID not set"  # noqa: S101
        project = Project.get(self.db, self.current_project_id)
        project.save()
        self.main_window.show_message("Saved")

    def navigate_to_token(self, token_id: int) -> None:
        """
        Navigate to a specific token.

        - If there is no database or the current project ID is not set, do nothing.
        - If there is no token with the given ID, do nothing.
        - If there is a token with the given ID, navigate to the token.

        Args:
            token_id: Token ID to navigate to

        """
        token = Token.get(self.db, token_id)
        sentence_id = token.sentence.id

        # Find the sentence card
        for card in self.sentence_cards:
            if card.sentence.id == sentence_id:
                # Scroll to the card
                self.main_window.ensure_visible(card)
                # Select the token by finding it in the tokens list
                token_idx = None
                for idx, token in enumerate(card.tokens):
                    if token.id == token_id:
                        token_idx = idx
                        break
                if token_idx is not None:
                    card.token_table.focus()
                    card.token_table.select_token(token_idx)
                    # Open annotation modal
                    card._open_annotation_modal()
                break

    def export_project(self) -> None:
        """
        Export project to DOCX.
        """
        if not self.db or not self.current_project_id:
            self.main_window.show_warning("No project open")
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

        try:
            exporter = DOCXExporter(self.db)
            if exporter.export(self.current_project_id, Path(file_path)):
                self.main_window.show_information(
                    f"Project exported successfully to:\n{file_path}",
                    title="Export Successful",
                )
                self.main_window.show_message("Export completed", duration=3000)
            else:
                self.main_window.show_warning(
                    "Failed to export project. Check console for details.",
                    title="Export Failed",
                )
        except Exception as e:
            self.main_window.show_error(
                f"An error occurred during export:\n{e!s}", title="Export Error"
            )

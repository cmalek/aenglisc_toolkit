"""Main application window."""

import sys
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final, cast

from PySide6.QtCore import QPoint, QSettings, Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from oeapp.commands import (
    AnnotateTokenCommand,
)
from oeapp.db import run_pragma_optimize
from oeapp.exc import MigrationFailed
from oeapp.help.help_engine import HelpEngineError
from oeapp.models.project import Project
from oeapp.models.search_result import SearchResult
from oeapp.services import (
    AnnotationPropagationService,
    AutosaveService,
    BackupService,
    DOCXExporter,
    MigrationService,
    ProjectExporter,
    ProjectImporter,
)
from oeapp.services.remembered_annotation_service import RememberedAnnotationService
from oeapp.state import AppContext
from oeapp.ui.dialogs import (
    BackupsViewDialog,
    DeleteProjectDialog,
    EditProjectDialog,
    ImportProjectDialog,
    MigrationFailureDialog,
    NewProjectDialog,
    OpenProjectDialog,
    RememberedAnnotationsDialog,
    RestoreDialog,
    SettingsDialog,
)
from oeapp.ui.dialogs.help_center_dialog import HelpCenterDialog
from oeapp.ui.menus import MainMenu
from oeapp.ui.project_workspace import ProjectUI
from oeapp.ui.search_controller import SearchController
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.shortcuts import GlobalShortcuts
from oeapp.ui.token_details_sidebar import TokenDetailsSidebar
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
    from PySide6.QtGui import QKeyEvent

    from oeapp.models.token import Token


class MainWindow(QMainWindow):
    """Main application window."""

    #: Main window geometry
    MAIN_WINDOW_GEOMETRY: Final[tuple[int, int, int, int]] = (100, 100, 1600, 800)
    #: Sidebar Width
    SIDEBAR_WIDTH: Final[int] = 350
    #: Sidebar Style
    SIDEBAR_STYLE: Final[str] = (
        "#sidebar { background-color: palette(base); "
        "border-left: 3px solid palette(highlight); }"
    )

    def __init__(self, app_context: AppContext | None = None) -> None:
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
        # Best-effort planner/statistics maintenance after DB is ready.
        with suppress(Exception):
            run_pragma_optimize()

        #: Sentence cards
        self.sentence_cards: list[SentenceCard] = []
        #: Stable application context.
        self.app_context = app_context or AppContext()
        self.app_context.set_main_window(self)
        #: Main window actions
        self.action_service = MainWindowActions(self, self.app_context)
        #: Autosave service
        self.autosave_service: AutosaveService | None = AutosaveService(
            self.action_service.autosave
        )

        #: Count of sentence cards in edit mode
        self._edit_mode_count = 0
        #: Non-modal help center dialog.
        self._help_dialog: HelpCenterDialog | None = None
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
        self.main_menu = MainMenu(self)
        self.main_menu.build()
        GlobalShortcuts(self).execute()

    def build_main_window(self) -> None:
        """
        Set up the main window.
        """
        # Create the QApplicaiton
        self.create_application()

        # Central widget with vertical layout to hold search toolbar and content
        central_widget = QWidget()
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.setCentralWidget(central_widget)

        # Create a container for the two-column layout
        column_container = QWidget()
        central_layout = QHBoxLayout(column_container)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        self.main_layout.addWidget(column_container, stretch=1)

        # Build a QVBoxLayout for the main content area so we can add the
        # toolbar and the main content area to it
        self.main_content_layout = QVBoxLayout()
        self.main_content_layout.setContentsMargins(0, 0, 0, 0)
        self.main_content_layout.setSpacing(0)
        central_layout.addLayout(self.main_content_layout)

        # Build top toolbar
        self.toolbar = self.build_toolbar()
        self.main_content_layout.addWidget(self.toolbar)

        # Build navigation toolbar
        self.navigation_toolbar = self.build_navigation_toolbar()
        self.main_content_layout.addWidget(self.navigation_toolbar)
        # Create the main content area.  This is a scroll area that contains the
        # sentence cards.

        self.main_column = self.build_main_content_area()
        self.content_layout = self.build_main_content(
            self.main_column, self.main_content_layout
        )
        self.token_details_sidebar = self.build_sidebar_area(central_layout)
        self.show_empty(self.content_layout)

    def build_toolbar(self) -> QWidget:
        """
        Build the search toolbar.

        Returns:
            QWidget: The search toolbar widget

        """
        toolbar = QWidget()
        toolbar.setObjectName("main_toolbar")
        toolbar.setStyleSheet(
            "#main_toolbar { border-bottom: 1px solid palette(mid); }"
        )
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Search:"))

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter tokens or phrases...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self.action_service.focus_first_match)

        # Intercept Escape key in search input
        def on_key_pressed(event: "QKeyEvent"):
            if event.key() == Qt.Key.Key_Escape:
                self._on_clear_search_clicked()
                event.accept()
            else:
                QLineEdit.keyPressEvent(self.search_input, event)

        self.search_input.keyPressEvent = on_key_pressed  # type: ignore[assignment]

        layout.addWidget(self.search_input, stretch=1)

        self.search_counter_label = QLabel("0 / 0")
        self.search_counter_label.setStyleSheet(
            "color: palette(highlight); font-weight: bold;"
        )
        layout.addWidget(self.search_counter_label)

        self.search_clear_button = QPushButton("Clear")
        self.search_clear_button.clicked.connect(self._on_clear_search_clicked)
        layout.addWidget(self.search_clear_button)

        self.search_scope_combo = QComboBox()
        self.search_scope_combo.addItems(["OE Text", "ModE text", "Notes", "All"])
        self.search_scope_combo.currentIndexChanged.connect(
            self._on_search_scope_changed
        )
        layout.addWidget(self.search_scope_combo)

        return toolbar

    def _on_search_text_changed(self, text: str) -> None:
        """Handle search text change."""
        self.action_service.perform_search(text, self.search_scope_combo.currentText())

    def _on_search_scope_changed(self, index: int) -> None:  # noqa: ARG002
        """Handle search scope change."""
        self.action_service.perform_search(
            self.search_input.text(), self.search_scope_combo.currentText()
        )

    def _on_clear_search_clicked(self) -> None:
        """Handle clear search button click."""
        self.action_service.clear_search(restore_origin_focus=True)

    def _clear_search_without_focus_restore(self) -> None:
        """Clear search state without restoring origin focus."""
        self.action_service.clear_search(restore_origin_focus=False)

    def build_navigation_toolbar(self) -> QWidget:
        """
        Build the chapter and section navigation toolbar.

        Returns:
            QWidget: The navigation toolbar widget

        """
        toolbar = QWidget()
        toolbar.setObjectName("navigation_toolbar")
        toolbar.setStyleSheet(
            "#navigation_toolbar { border-bottom: 3px solid palette(highlight); }"
        )
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)

        # Chapter navigation
        layout.addWidget(QLabel("Chapter:"))
        self.chapter_prev_button = QPushButton("<")
        self.chapter_prev_button.setFixedWidth(30)
        self.chapter_prev_button.clicked.connect(self._on_prev_chapter_clicked)
        layout.addWidget(self.chapter_prev_button)

        self.chapter_combo = QComboBox()
        self.chapter_combo.setMinimumWidth(150)
        self.chapter_combo.currentIndexChanged.connect(self._on_chapter_changed)
        layout.addWidget(self.chapter_combo)

        self.chapter_next_button = QPushButton(">")
        self.chapter_next_button.setFixedWidth(30)
        self.chapter_next_button.clicked.connect(self._on_next_chapter_clicked)
        layout.addWidget(self.chapter_next_button)

        layout.addSpacing(20)

        # Section navigation
        layout.addWidget(QLabel("Section:"))
        self.section_prev_button = QPushButton("<")
        self.section_prev_button.setFixedWidth(30)
        self.section_prev_button.clicked.connect(self._on_prev_section_clicked)
        layout.addWidget(self.section_prev_button)

        self.section_combo = QComboBox()
        self.section_combo.setMinimumWidth(150)
        self.section_combo.currentIndexChanged.connect(self._on_section_changed)
        layout.addWidget(self.section_combo)

        self.section_next_button = QPushButton(">")
        self.section_next_button.setFixedWidth(30)
        self.section_next_button.clicked.connect(self._on_next_section_clicked)
        layout.addWidget(self.section_next_button)

        layout.addStretch()

        return toolbar

    def _on_prev_chapter_clicked(self) -> None:
        """Handle previous chapter button click."""
        idx = self.chapter_combo.currentIndex()
        if idx > 0:
            self.chapter_combo.setCurrentIndex(idx - 1)

    def _on_next_chapter_clicked(self) -> None:
        """Handle next chapter button click."""
        idx = self.chapter_combo.currentIndex()
        if idx < self.chapter_combo.count() - 1:
            self.chapter_combo.setCurrentIndex(idx + 1)

    def _on_chapter_changed(self, index: int) -> None:
        """Handle chapter selection change."""
        if index < 0:
            return
        chapter_id = self.chapter_combo.itemData(index)
        self.app_context.current_chapter_id = chapter_id
        self.project_ui.update_sections_for_chapter(chapter_id)

    def _on_prev_section_clicked(self) -> None:
        """Handle previous section button click."""
        idx = self.section_combo.currentIndex()
        if idx > 0:
            self.section_combo.setCurrentIndex(idx - 1)

    def _on_next_section_clicked(self) -> None:
        """Handle next section button click."""
        idx = self.section_combo.currentIndex()
        if idx < self.section_combo.count() - 1:
            self.section_combo.setCurrentIndex(idx + 1)

    def _on_section_changed(self, index: int) -> None:
        """Handle section selection change."""
        if index < 0:
            return
        section_id = self.section_combo.itemData(index)
        self.app_context.current_section_id = section_id
        self.project_ui.load_section(section_id)

    def keyPressEvent(self, event: "QKeyEvent") -> None:  # noqa: N802
        """
        Handle global key presses, like Escape to clear search.

        Args:
            event: The key event

        """
        if event.key() == Qt.Key.Key_Escape and self.search_input.text():
            self._on_clear_search_clicked()
            event.accept()
            return
        super().keyPressEvent(event)

    def update_search_ui_state(self, is_editing: bool) -> None:
        """
        Update the search UI state (enabled/disabled) based on whether
        any sentence card is in edit mode.

        Args:
            is_editing: Whether any sentence card is in edit mode

        """
        if is_editing:
            self._edit_mode_count += 1
        else:
            self._edit_mode_count = max(0, self._edit_mode_count - 1)

        enabled = self._edit_mode_count == 0
        self.search_input.setEnabled(enabled)
        self.search_clear_button.setEnabled(enabled)
        self.search_scope_combo.setEnabled(enabled)

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
        welcome_label.setStyleSheet(
            "font-size: 14pt; color: pallete(text-muted); padding: 50px;"
        )
        layout.addWidget(welcome_label)

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
        self, container: QScrollArea, layout: QVBoxLayout
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
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(self.SIDEBAR_WIDTH)
        sidebar.setStyleSheet(self.SIDEBAR_STYLE)
        layout.addWidget(sidebar)
        return sidebar

    def closeEvent(self, event) -> None:  # noqa: N802
        """Handle window close event."""
        # Stop backup timer
        if self.backup_timer:
            self.backup_timer.stop()
            self.backup_timer.deleteLater()
            self.backup_timer = None
        # Stop autosave service
        if self.autosave_service:
            self.autosave_service.cancel()
            self.autosave_service = None
        # Keep this non-blocking on shutdown.
        with suppress(Exception):
            run_pragma_optimize()
        super().closeEvent(event)

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
        if bool(Project.first()) and self.app_context.session:
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
        content_widget = self.main_column.widget()
        if content_widget is None:
            return

        viewport_height = self.main_column.viewport().height()
        scrollbar = self.main_column.verticalScrollBar()
        if viewport_height <= 0:
            self.main_column.ensureWidgetVisible(widget)
            return

        widget_top = widget.mapTo(content_widget, QPoint(0, 0)).y()
        widget_bottom = widget_top + widget.height()
        viewport_top = scrollbar.value()
        viewport_bottom = viewport_top + viewport_height
        top_padding = 8

        # Prefer full-card visibility when the card fits in the viewport.
        if widget.height() <= viewport_height:
            if widget_top < viewport_top or widget_bottom > viewport_bottom:
                target = max(
                    scrollbar.minimum(),
                    min(widget_top - top_padding, scrollbar.maximum()),
                )
                scrollbar.setValue(target)
            return

        # Fallback for very tall cards: keep the top of the card visible.
        if widget_top < viewport_top or widget_top > viewport_bottom:
            target = max(
                scrollbar.minimum(),
                min(widget_top - top_padding, scrollbar.maximum()),
            )
            scrollbar.setValue(target)

    def show_help(self, topic: str | None = None) -> None:
        """
        Show help dialog.

        Args:
            topic: Optional topic to display initially

        """
        if self._help_dialog and self._help_dialog.isVisible():
            self._help_dialog.show_topic(topic)
            self._help_dialog.raise_()
            self._help_dialog.activateWindow()
            return

        try:
            self._help_dialog = HelpCenterDialog(topic=topic, parent=self)
        except (FileNotFoundError, HelpEngineError) as error:
            self.messages.show_error(str(error), title="Help Unavailable")
            return

        self._help_dialog.show()

    def show_settings_dialog(self) -> None:
        """
        Show settings dialog.
        """
        dialog = SettingsDialog(self)
        dialog.execute()
        # Clear search after settings changes as they may affect display/tokenization
        self._clear_search_without_focus_restore()

    def show_restore_dialog(self) -> None:
        """
        Show restore dialog.
        """
        dialog = RestoreDialog(self)
        dialog.execute()
        # After restore, we may need to reload
        project_id = self.app_context.current_project_id
        if project_id is not None:
            project = Project.get(project_id)
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
        self.token_details_sidebar.show_empty()

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

    def __init__(self, main_window: MainWindow, app_context: AppContext) -> None:
        """
        Initialize main window actions.

        Args:
            main_window: Main window instance.
            app_context: Shared application context.

        """
        #: Main window instance.
        self.main_window = main_window
        #: Backup service
        self.backup_service = BackupService()
        #: Stable app context.
        self.app_context = app_context
        #: Messages
        self.messages = main_window.messages
        #: Search UI state and navigation
        self._search_controller = SearchController(
            main_window, self.app_context
        )

    @property
    def search_results(self) -> list[SearchResult]:
        """
        Ordered search results across the entire project.

        Returns:
            Current ordered search results.

        """
        return self._search_controller.search_results

    @property
    def search_total_matches(self) -> int:
        """
        Total number of matched occurrences across all results.

        Returns:
            Total match count for the active search.

        """
        return self._search_controller.search_total_matches

    @property
    def current_match_index(self) -> int:
        """
        Current match index in search_results.

        Returns:
            Zero-based index of the active search result.

        """
        return self._search_controller.current_match_index

    @property
    def sentence_cards(self) -> list[SentenceCard]:
        """
        Get the current sentence cards from main window.

        Returns:
            Sentence cards currently loaded in the workspace.

        """
        return self.main_window.sentence_cards

    def perform_search(self, pattern: str, scope: str) -> None:
        """
        Perform project-wide search and update visible highlights.

        Args:
            pattern: Search pattern
            scope: Search scope ("OE Text", "ModE text", "Notes", "All")

        """
        self._search_controller.perform_search(pattern, scope)

    def next_match(self) -> None:
        """Navigate to the next matching search result."""
        self._search_controller.next_match()

    def prev_match(self) -> None:
        """Navigate to the previous matching search result."""
        self._search_controller.prev_match()

    def focus_search_input(self) -> None:
        """Focus the search input."""
        self.main_window.search_input.setFocus()
        self.main_window.search_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.main_window.search_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def focus_first_match(self) -> None:
        """Focus the first match in search results."""
        self._search_controller.focus_first_match()

    def clear_search(self, restore_origin_focus: bool = False) -> None:
        """
        Clear search state, highlights, and optionally restore origin focus.

        Args:
            restore_origin_focus: Whether to restore focus to search origin ModE field.

        """
        self._search_controller.clear_search(restore_origin_focus=restore_origin_focus)

    def scroll_to_end(self) -> None:
        """
        Scroll to the last sentence card and focus it.

        This is a the event handler for the Shift+Down shortcut.
        """
        if self.sentence_cards:
            card = self.sentence_cards[-1]
            self.main_window.ensure_visible(card)
            card.oe_text_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            card.oe_text_edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def on_escape_pressed(self) -> None:
        """
        Handle escape key press.

        This is a the event handler for the Escape shortcut.
        """
        # If we're in search mode, clear the search
        if self.main_window.search_input.text():
            self.main_window._on_clear_search_clicked()
            return

        # If we're not in search mode, iterate through the sentence cards
        # and clear all highlighting
        for card in self.sentence_cards:
            card.oe_text_edit.unhighlight()

        # Clear the sidebar
        self.main_window.token_details_sidebar.clear_sidebar()

    def scroll_to_start(self) -> None:
        """
        Scroll to the first sentence card and focus it.

        This is a the event handler for the Shift+Up shortcut.
        """
        if self.sentence_cards:
            card = self.sentence_cards[0]
            self.main_window.ensure_visible(card)
            card.oe_text_edit.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            card.oe_text_edit.setFocus(Qt.FocusReason.OtherFocusReason)

    @property
    def command_manager(self):
        """Get the current command manager from main window."""
        return self.app_context.command_manager

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
        card = self._selected_sentence_card()
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
        self.app_context.copied_annotation = annotation.to_json()
        self.messages.show_message("Annotation copied")
        return True

    def _selected_sentence_card(self) -> SentenceCard | None:
        """
        Get the workspace-local selected sentence card.

        Returns:
            Selected sentence card, or ``None`` when no card is selected.

        """
        project_ui = getattr(self.main_window, "project_ui", None)
        if project_ui is None:
            return None
        return project_ui.get_selected_sentence_card()

    def paste_annotation(self) -> bool:
        """
        Paste the copied annotation onto the currently selected token.

        Returns:
            True if annotation was pasted, False otherwise.
            Returns False if no token is selected (allows normal clipboard behavior).

        """
        # Check if a token is selected
        card = self._selected_sentence_card()
        if card is None:
            return False
        selector = card.oe_text_edit.selector
        current_token_index = (
            selector.current_token_index() if selector is not None else None
        )
        if current_token_index is None:
            # No token selected, allow normal clipboard behavior
            return False

        # Check if there's a copied annotation
        copied_annotation = self.app_context.copied_annotation
        if copied_annotation is None:
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
            after=copied_annotation,
        )

        if self.command_manager.execute(command):
            # Refresh the token from database to update relationships
            self.app_context.session.refresh(token)

            # Refresh the sentence card
            card.set_tokens()

            # Update sidebar if the pasted token is currently displayed
            self.main_window.token_details_sidebar.render_token(token, card.sentence)

            self.messages.show_message("Annotation pasted")
        else:
            self.messages.show_message("Paste failed")

        return True

    def remember_token_annotation(self, token: "Token", project_id: int | None) -> None:
        """
        Remember one token annotation into global or project scope.

        Args:
            token: Token whose annotation should be remembered.
            project_id: Scope discriminator. ``None`` means global.

        """
        annotation = token.annotation
        if annotation is None or annotation.is_safe_to_auto_fill():
            self.messages.show_warning("Token has no annotation to remember")
            return
        RememberedAnnotationService().remember_token_annotation(token, project_id)
        scope_text = "globally" if project_id is None else "for project"
        self.messages.show_message(f"Remembered '{token.surface}' {scope_text}")

    def apply_remembered_annotations(self) -> None:
        """
        Apply remembered annotations across the current project.

        """
        project_id = self.app_context.current_project_id
        if project_id is None:
            self.messages.show_warning("No project open")
            return

        plan = RememberedAnnotationService().plan_apply(project_id)
        if plan.applied_count == 0:
            self.messages.show_message(plan.message, duration=3000)
            return

        if not self.command_manager.execute(plan.command):
            self.messages.show_error("Failed to apply remembered annotations")
            return

        self.main_window.refresh_project()
        self.messages.show_message(plan.message, duration=3000)

    def propagate_token_annotation(self, token: "Token") -> None:
        """
        Propagate one token annotation to safe empty same-surface matches.

        Args:
            token: Source token for propagation.

        """
        project_id = self.app_context.current_project_id
        if project_id is None:
            self.messages.show_warning("No project open")
            return

        plan = AnnotationPropagationService().plan_surface_propagation(
            project_id, token
        )
        if plan.updated_count > 0 and not self.command_manager.execute(plan.command):
            self.messages.show_error("Failed to propagate annotation")
            return
        if plan.updated_count > 0:
            self.main_window.refresh_project()
        self.messages.show_information(plan.dialog_message)

    def force_propagate_token_meaning(self, token: "Token") -> None:
        """
        Propagate one token meaning to same-root matches across project.

        Args:
            token: Source token for propagation.

        """
        project_id = self.app_context.current_project_id
        if project_id is None:
            self.messages.show_warning("No project open")
            return

        plan = AnnotationPropagationService().plan_meaning_propagation(
            project_id, token
        )
        if plan.updated_count > 0 and not self.command_manager.execute(plan.command):
            self.messages.show_error("Failed to propagate meaning")
            return
        if plan.updated_count > 0:
            self.main_window.refresh_project()
        self.messages.show_information(plan.dialog_message)

    def show_project_remembered_annotations_dialog(self) -> None:
        """
        Open the project-scoped remembered annotation management dialog.

        """
        project_id = self.app_context.current_project_id
        if project_id is None:
            self.messages.show_warning("No project open")
            return
        dialog = RememberedAnnotationsDialog(project_id, parent=self.main_window)
        dialog.exec()

    def autosave(self) -> None:
        """
        Do an autosave operation.

        - If the current project ID is not set, do nothing.
        - Sanitize notes before committing to prevent SQLAlchemy mapping errors
        - Save the current project.
        - Show a message in the status bar that the project has been saved.

        """
        project_id = self.app_context.current_project_id
        if project_id is None:
            return
        project = Project.get(project_id)
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
        try:
            self.messages.show_message("Saved")
        except RuntimeError:
            # Main window can already be deleted when late timer callbacks run.
            return

    def import_project_json(self) -> None:
        """
        Import project from JSON format.
        """
        # Get file path from user
        file_path, _ = QFileDialog.getOpenFileName(
            self.main_window,
            "Import Project",
            "",
            "Project Exports (*.json *.json.gz);;JSON Files (*.json);;GZip JSON Files (*.json.gz);;All Files (*)",  # noqa: E501
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
                self.main_window.project_ui.load(imported_project)
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
        project_id: int | bool | None = None,
        parent: QWidget | None = None,
    ) -> bool:
        """
        Export project to JSON format.

        Note that when called as a callback from a dialog, project_id will be a boolean.

        Args:
            project_id: Optional project ID to export. If not provided, uses
                :attr:`oeapp.state.AppContext.current_project_id`.
            parent: Optional parent widget for the file dialog. If not provided,
                uses self.

        Returns:
            True if export was successful, False if canceled or failed

        """
        target_project_id = (
            project_id
            if isinstance(project_id, int)
            else self.app_context.current_project_id
        )
        if not self.app_context.session or target_project_id is None:
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
            "Project Exports (*.json *.json.gz);;JSON Files (*.json);;GZip JSON Files (*.json.gz);;All Files (*)",  # noqa: E501
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
        project_id = self.app_context.current_project_id
        if project_id is None:
            self.messages.show_warning("No project open")
            return

        project = Project.get(project_id)
        if project is None:
            self.messages.show_warning("Project not found")
            return

        dialog = EditProjectDialog(self.main_window, project)
        dialog.execute()

    def export_project_docx(self) -> None:
        """
        Export project to DOCX.
        """
        project_id = self.app_context.current_project_id
        if not self.app_context.session or project_id is None:
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
            export_success = exporter.export(project_id, Path(file_path))
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

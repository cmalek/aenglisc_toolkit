"""Full translation side-by-side window."""

import re
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QTextCharFormat,
    QTextCursor,
    QTextFormat,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oeapp.services.export_docx import DOCXExporter
from oeapp.ui.highlighting import SearchHighlighter
from oeapp.ui.mixins import ThemeMixin
from oeapp.ui.oe_text_edit import OldEnglishTextEdit, OldEnglishTextSelector
from oeapp.ui.token_details_sidebar import FullTranslationSidebar

if TYPE_CHECKING:
    from oeapp.models import Idiom
    from oeapp.models.project import Project
    from oeapp.models.token import Token
    from oeapp.ui.main_window import MainWindow

# Custom property to store sentence ID in text fragments
SENTENCE_ID_PROPERTY: Final[int] = QTextFormat.UserProperty + 10  # type: ignore[attr-defined]
# Property IDs for ExtraSelections
TOKEN_HIGHLIGHT_PROPERTY: Final[int] = QTextFormat.UserProperty + 11  # type: ignore[attr-defined]
SENTENCE_HIGHLIGHT_PROPERTY: Final[int] = QTextFormat.UserProperty + 12  # type: ignore[attr-defined]
NOTE_ID_PROPERTY: Final[int] = QTextFormat.UserProperty + 13  # type: ignore[attr-defined]
NOTE_HIGHLIGHT_PROPERTY: Final[int] = QTextFormat.UserProperty + 14  # type: ignore[attr-defined]


class FullProjectOldEnglishTextEdit(ThemeMixin, OldEnglishTextEdit):
    """
    OE text edit for the full project view.

    Args:
        project: The project to display
        parent: The parent widget (optional)

    """

    # Signal emitted when a token is hovered
    token_hovered = Signal(object)  # Token or None
    # Signal emitted when a sentence is selected (via token selection)
    sentence_selected = Signal(int)

    def __init__(self, project: Project, parent: FullTranslationWindow | None = None):
        super().__init__(parent)
        self.project: Project = project
        self._full_window: FullTranslationWindow | None = parent
        self.setMouseTracking(True)
        # Override selector to not depend on sentence_card
        self.selector = FullProjectTextSelector(self)
        self.clicked.connect(self.selector.select_tokens)

        # Mapping of (sentence_id, token_id) -> position in text
        self.token_positions: dict[tuple[int, int], tuple[int, int]] = {}
        # Mapping of sentence_id -> list of (start, end) positions
        self.sentence_positions: dict[int, tuple[int, int]] = {}

        self.render_readonly_text()

    def connect_signals(self) -> None:
        """
        Connect signals to the sidebar.
        """
        if hasattr(self._full_window, "token_details_sidebar"):
            sidebar = cast(
                "FullTranslationWindow", self._full_window
            ).token_details_sidebar
            self.token_selected.connect(sidebar._on_token_selected)
            self.token_deselected.connect(sidebar._on_token_deselected)
            self.idiom_selection.connect(sidebar._on_idiom_selected)

    def render_readonly_text(self) -> None:
        """
        Render the entire project's OE text.
        """
        self.clear()
        self.token_positions.clear()
        self.sentence_positions.clear()
        self.tokens_by_id.clear()

        cursor = QTextCursor(self.document())

        for i, sentence in enumerate(self.project.sentences):
            sentence_id = cast("int", sentence.id)
            if sentence.is_paragraph_start and i > 0:
                cursor.insertText("\n\n")
            elif i > 0:
                cursor.insertText(" ")

            sentence_start = cursor.position()

            tokens, token_id_to_start = sentence.sorted_tokens
            text = sentence.text_oe
            last_pos = 0

            # Map of end_token_id -> list of note numbers
            token_to_note_numbers: dict[int, list[int]] = {}
            if self._full_window:
                for note_num, note in self._full_window.project_notes:
                    if note.sentence_id == sentence_id and note.end_token:
                        if note.end_token not in token_to_note_numbers:
                            token_to_note_numbers[note.end_token] = []
                        token_to_note_numbers[note.end_token].append(note_num)

            for token in tokens:
                token_id = cast("int", token.id)
                self.tokens_by_id[token_id] = token

                token_start = token_id_to_start[token_id]
                token_end = token_start + len(token.surface)

                if token_start > last_pos:
                    # Non-token text within sentence
                    fmt = QTextCharFormat()
                    fmt.setProperty(SENTENCE_ID_PROPERTY, sentence_id)
                    cursor.insertText(text[last_pos:token_start], fmt)

                # Format for token
                fmt = QTextCharFormat()
                fmt.setProperty(self.TOKEN_INDEX_PROPERTY, token_id)
                fmt.setProperty(SENTENCE_ID_PROPERTY, sentence_id)

                start_in_doc = cursor.position()
                cursor.insertText(token.surface, fmt)
                end_in_doc = cursor.position()

                self.token_positions[(sentence_id, token_id)] = (
                    start_in_doc,
                    end_in_doc,
                )

                # Insert note superscripts if any
                if token_id in token_to_note_numbers:
                    for note_num in token_to_note_numbers[token_id]:
                        note_fmt = QTextCharFormat()
                        note_fmt.setVerticalAlignment(
                            QTextCharFormat.VerticalAlignment.AlignSuperScript
                        )
                        # We don't want the superscript to be part of the token for selection
                        # but it should belong to the sentence
                        note_fmt.setProperty(SENTENCE_ID_PROPERTY, sentence_id)
                        note_fmt.setProperty(NOTE_ID_PROPERTY, note_num)
                        cursor.insertText(str(note_num), note_fmt)

                last_pos = token_end

            if last_pos < len(text):
                # Remaining non-token text
                fmt = QTextCharFormat()
                fmt.setProperty(SENTENCE_ID_PROPERTY, sentence_id)
                cursor.insertText(text[last_pos:], fmt)

            sentence_end = cursor.position()
            self.sentence_positions[sentence_id] = (sentence_start, sentence_end)

    def find_token_at_position(self, position: int) -> int | None:
        """
        Find token ID at character position.

        - Get the cursor at the position in the document
        - Check character after the cursor
        - If the character after the cursor belongs to a token, return the token ID
        - Otherwise, return ``None``

        Args:
            position: Position to find token at

        Returns:
            ID of the token at the position, or ``None`` if no token is found

        """
        doc = self.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(position)

        # Check character after
        if position < doc.characterCount() - 1:
            test_cursor = QTextCursor(doc)
            test_cursor.setPosition(position)
            test_cursor.movePosition(
                QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
            )
            val = test_cursor.charFormat().property(self.TOKEN_INDEX_PROPERTY)
            if val is not None:
                return cast("int", val)

        # Check current
        val = cursor.charFormat().property(self.TOKEN_INDEX_PROPERTY)
        return cast("int", val) if val is not None else None

    def find_sentence_at_position(self, position: int) -> int | None:
        """Find sentence ID at character position."""
        doc = self.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(position)

        # Check character after
        if position < doc.characterCount() - 1:
            test_cursor = QTextCursor(doc)
            test_cursor.setPosition(position)
            test_cursor.movePosition(
                QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
            )
            val = test_cursor.charFormat().property(SENTENCE_ID_PROPERTY)
            if val is not None:
                return cast("int", val)

        # Check current
        val = cursor.charFormat().property(SENTENCE_ID_PROPERTY)
        return cast("int", val) if val is not None else None

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle hover effect.

        - Get the cursor at the position
        - Get the token ID at the cursor position
        - If a token is found, emit the :attr:`token_hovered` signal with the token
        - Otherwise, emit the :attr:`token_hovered` signal with ``None``
        """
        cursor = self.cursorForPosition(event.position().toPoint())
        token_id = self.find_token_at_position(cursor.position())
        if token_id:
            token = self.tokens_by_id.get(token_id)
            self.token_hovered.emit(token)
        else:
            self.token_hovered.emit(None)
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Bidirectional navigation on double-click.

        - Get the cursor at the position the mouse was double-clicked at
        - Get the token ID at the cursor position in the document
        - If a token is found, navigate to the main sentence of the token by calling
          :meth:`_navigate_to_main_sentence` with the token's sentence ID
        - Otherwise, do nothing

        Args:
            event: Mouse double-click event

        """
        cursor = self.cursorForPosition(event.position().toPoint())
        token_id = self.find_token_at_position(cursor.position())
        if token_id:
            token = self.tokens_by_id.get(token_id)
            if token and self._full_window:
                cast(
                    "FullTranslationWindow", self._full_window
                )._navigate_to_main_sentence(token.sentence_id)
        super().mouseDoubleClickEvent(event)

    def highlight_sentence(self, sentence_id: int | None) -> None:  # type: ignore[override]
        """
        Highlight the entire sentence range using ExtraSelection.

        - Filter out existing sentence highlights
        - If the sentence ID is not None and in the sentence positions, highlight the
          sentence range by creating an :class:`QTextEdit.ExtraSelection` for
          the sentence range
        - Set the background color to very light yellow
        - Set the sentence highlight property
          (:attr:`SENTENCE_HIGHLIGHT_PROPERTY`) to ``True``
        - Append the :class:`QTextEdit.ExtraSelection` to the extra selections
        - Set the extra selections on the text edit

        Args:
            sentence_id: ID of the sentence to highlight; if ``None``, deselect any
                existing sentence highlights

        """
        selections = self.extraSelections()
        # Filter out existing sentence context highlights
        selections = [
            s
            for s in selections
            if not s.format.property(SENTENCE_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]

        if sentence_id is not None and sentence_id in self.sentence_positions:
            start, end = self.sentence_positions[sentence_id]
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor  # type: ignore[attr-defined]
            selection.format.setBackground(  # type: ignore[attr-defined]
                QColor("#fff9c4")
            )  # Very light yellow
            selection.format.setProperty(SENTENCE_HIGHLIGHT_PROPERTY, True)  # type: ignore[attr-defined]  # noqa: FBT003
            selections.append(selection)

        self.setExtraSelections(selections)

    def highlight_note_tokens(self, note: Note, highlight: bool) -> None:
        """
        Highlight the tokens covered by a note.
        """
        selections = self.extraSelections()
        # Filter out existing highlights for THIS specific note
        # We use a custom property to identify which note this highlight belongs to
        selections = [
            s
            for s in selections
            if s.format.property(NOTE_HIGHLIGHT_PROPERTY) != note.id
        ]

        if highlight:
            # Find all tokens in the range
            tokens_in_range = []
            in_range = False
            # We need to sort tokens by order_index to find the range
            sorted_tokens = sorted(
                [
                    t
                    for t in self.tokens_by_id.values()
                    if t.sentence_id == note.sentence_id
                ],
                key=lambda t: t.order_index,
            )

            for token in sorted_tokens:
                if token.id == note.start_token:
                    in_range = True
                if in_range:
                    tokens_in_range.append(token)
                if token.id == note.end_token:
                    break

            for token in tokens_in_range:
                pos = self.token_positions.get(
                    (note.sentence_id, cast("int", token.id))
                )
                if pos:
                    start, end = pos
                    cursor = QTextCursor(self.document())
                    cursor.setPosition(start)
                    cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

                    selection = QTextEdit.ExtraSelection()
                    selection.cursor = cursor
                    selection.format.setBackground(
                        QColor("#e1f5fe")
                    )  # Light blue for notes
                    if self.is_dark_theme:
                        selection.format.setForeground(self.theme_base_color)
                    selection.format.setProperty(NOTE_HIGHLIGHT_PROPERTY, note.id)
                    selections.append(selection)

        self.setExtraSelections(selections)

    def clear_all_note_highlights(self) -> None:
        """
        Clear all note-related highlights.
        """
        selections = self.extraSelections()
        selections = [
            s for s in selections if not s.format.property(NOTE_HIGHLIGHT_PROPERTY)
        ]
        self.setExtraSelections(selections)


class FullProjectModernEnglishTextEdit(ThemeMixin, QTextEdit):
    """
    Modern English text edit for the full project view with sentence mapping.
    """

    sentence_selected = Signal(int)
    sentence_deselected = Signal()

    def __init__(self, project: Project, parent: QWidget | None = None):
        super().__init__(parent)
        self.project = project
        self.setReadOnly(True)
        self.sentence_positions: dict[int, tuple[int, int]] = {}
        self._selected_sentence_id: int | None = None

        self.render_text()

    def render_text(self) -> None:
        """Render the project's translation text."""
        self.clear()
        self.sentence_positions.clear()
        cursor = QTextCursor(self.document())

        for i, sentence in enumerate(self.project.sentences):
            sentence_id = cast("int", sentence.id)
            if sentence.is_paragraph_start and i > 0:
                cursor.insertText("\n\n")
            elif i > 0:
                cursor.insertText(" ")

            start = cursor.position()
            fmt = QTextCharFormat()
            fmt.setProperty(SENTENCE_ID_PROPERTY, sentence_id)

            text = sentence.text_modern or "[...]"
            cursor.insertText(text, fmt)
            end = cursor.position()

            self.sentence_positions[sentence_id] = (start, end)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle clicking on sentences.

        - Get the cursor position
        - Get the sentence ID at the cursor position
        - Select the sentence
        - Deselect any previously selected sentence if no sentence is found

        Args:
            event: Mouse press event

        """
        cursor = self.cursorForPosition(event.position().toPoint())
        pos = cursor.position()

        doc = self.document()
        # Check character at position
        char_cursor = QTextCursor(doc)
        char_cursor.setPosition(pos)
        if pos < doc.characterCount() - 1:
            char_cursor.movePosition(
                QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
            )
            sentence_id = char_cursor.charFormat().property(SENTENCE_ID_PROPERTY)
        else:
            sentence_id = None

        if sentence_id is not None:
            self.select_sentence(cast("int", sentence_id))
        else:
            self.deselect()

        super().mousePressEvent(event)

    def select_sentence(self, sentence_id: int) -> None:
        """
        Select and highlight a sentence.

        - Toggle off if already selected
        - Set the selected sentence ID
        - Highlight the sentence by calling :meth:`highlight_sentence`
        - Emit the :attr:`sentence_selected` signal

        Args:
            sentence_id: ID of the sentence to select

        """
        if self._selected_sentence_id == sentence_id:
            # Toggle off if already selected
            self.deselect()
            return

        self._selected_sentence_id = sentence_id
        self.highlight_sentence(sentence_id)
        self.sentence_selected.emit(sentence_id)

    def deselect(self) -> None:
        """
        Deselect current sentence.

        - Set the selected sentence ID to None
        - Highlight the sentence by calling :meth:`highlight_sentence` with ``None``
        - Emit the :attr:`sentence_deselected` signal
        """
        self._selected_sentence_id = None
        self.highlight_sentence(None)
        self.sentence_deselected.emit()

    def highlight_sentence(self, sentence_id: int | None) -> None:
        """
        Highlight the given sentence range using ExtraSelection.

        - Filter out existing sentence highlights
        - If the sentence ID is not None and in the sentence positions,
          highlight the sentence range by creating an ExtraSelection for the
          sentence range
        - Set the background color to light blue
        - Set the sentence highlight property
        - Append the ExtraSelection to the extra selections
        - Set the extra selections

        Args:
            sentence_id: ID of the sentence to highlight; if ``None``, deselect any
                existing sentence highlights

        """
        selections = self.extraSelections()
        # Filter out existing sentence highlights
        selections = [
            s
            for s in selections
            if not s.format.property(SENTENCE_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]

        if sentence_id is not None and sentence_id in self.sentence_positions:
            start, end = self.sentence_positions[sentence_id]
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor  # type: ignore[attr-defined]
            selection.format.setBackground(  # type: ignore[attr-defined]
                QColor("#e3f2fd")
            )  # Light blue
            if self.is_dark_theme:
                selection.format.setForeground(self.theme_base_color)  # type: ignore[attr-defined]
            selection.format.setProperty(SENTENCE_HIGHLIGHT_PROPERTY, True)  # type: ignore[attr-defined]  # noqa: FBT003
            selections.append(selection)

        self.setExtraSelections(selections)


class FullProjectTextSelector(OldEnglishTextSelector):
    """
    Selector for the full project view.

    Args:
        text_edit: The text edit to select tokens from

    """

    def __init__(self, text_edit: FullProjectOldEnglishTextEdit):
        self.text_edit: FullProjectOldEnglishTextEdit = text_edit
        self._deselect_timer: QTimer = QTimer(self.text_edit)
        self._deselect_timer.setSingleShot(True)
        self._deselect_timer.timeout.connect(self.deselect)
        self._pending_deselect_token_index: int | None = None
        self.selected_token_index: int | None = None  # This will store token_id here
        self.selected_token_range: tuple[int, int] | None = None

    def select_tokens(self, position: QPoint, modifiers: Qt.KeyboardModifier) -> None:  # noqa: ARG002
        """
        Select tokens at the given position.

        - If the text edit is read-only, get the token ID at the cursor position
        - If a token is found, select the token by calling :meth:`token_selection`
        - If no token is found, check if a note superscript was clicked
        - If a note is found, scroll to and highlight it
        - If no note is found, get the sentence ID at the cursor position
        - If a sentence is found, emit the :attr:`sentence_selected` signal
        - If no sentence is found, deselect any existing token or sentence highlights
          by calling :meth:`deselect`

        Args:
            position: Position to select tokens at
            modifiers: Modifiers pressed (Ctrl, Shift, etc.) (unused)

        """
        if self.text_edit.isReadOnly():
            cursor = self.text_edit.cursorForPosition(position)
            token_id = self.text_edit.find_token_at_position(cursor.position())
            if token_id:
                self.token_selection(token_id)
            else:
                # Check for note superscript click
                note_num = cursor.charFormat().property(NOTE_ID_PROPERTY)
                if note_num and self.text_edit._full_window:
                    self.text_edit._full_window._on_note_clicked(note_num)
                    # Optionally scroll to the note widget
                    area = self.text_edit._full_window.notes_area
                    if note_num in area.note_widgets:
                        area.ensureWidgetVisible(area.note_widgets[note_num])
                    return

                # If we clicked non-token text, we might still want to select
                # the sentence
                sentence_id = self.text_edit.find_sentence_at_position(
                    cursor.position()
                )
                if sentence_id:
                    self.text_edit.sentence_selected.emit(sentence_id)
                else:
                    self.deselect()

    def token_selection(self, token_id: int) -> None:
        """
        Select a token.

        - If the token is already selected, start a timer to deselect the token,
          and return
        - If the token is not selected, select the token by calling
          :meth:`token_selection` with the token ID
        - Highlight the token by calling :meth:`highlight_token` with the token ID
        - Emit the :attr:`token_selected` signal with the token
        - Emit the :attr:`sentence_selected` signal with the token's sentence ID

        Args:
            token_id: ID of the token to select

        """
        if self.selected_token_index == token_id:
            self._pending_deselect_token_index = token_id
            self._deselect_timer.start(100)
        else:
            self.selected_token_index = token_id
            token = self.text_edit.tokens_by_id.get(token_id)
            if token:
                # Highlight the token
                self.highlight_token(token_id)
                self.text_edit.token_selected.emit(token)
                # Also signal that the sentence is selected
                self.text_edit.sentence_selected.emit(token.sentence_id)

    def highlight_token(self, token_id: int) -> None:
        """
        Apply temporary highlight to a token using :class:`QTextEdit.ExtraSelection`.

        - Filter out existing token highlights
        - If the token ID is in the token positions, apply the highlight to the
          token range by creating an ExtraSelection for the token range
        - Set the background color to light yellow
        - Set the token highlight property (:attr:`TOKEN_HIGHLIGHT_PROPERTY`) to True
        - Append the :class:`QTextEdit.ExtraSelection` to the extra selections
        - Set the extra selections on the text edit

        Args:
            token_id: ID of the token to highlight

        """
        selections = self.text_edit.extraSelections()
        # Filter out existing token highlights
        selections = [
            s
            for s in selections
            if not s.format.property(TOKEN_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]

        # Apply highlight to selected
        pos = None
        for (_sid, tid), (start, end) in self.text_edit.token_positions.items():
            if tid == token_id:
                pos = (start, end)
                break

        if pos:
            cursor = QTextCursor(self.text_edit.document())
            cursor.setPosition(pos[0])
            cursor.setPosition(pos[1], QTextCursor.MoveMode.KeepAnchor)

            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor  # type: ignore[attr-defined]
            selection.format.setBackground(  # type: ignore[attr-defined]
                QColor("#ffeb3b")
            )  # Light yellow
            selection.format.setProperty(TOKEN_HIGHLIGHT_PROPERTY, True)  # type: ignore[attr-defined]  # noqa: FBT003
            selections.append(selection)

        self.text_edit.setExtraSelections(selections)

    def deselect(self) -> None:
        """
        Deselect the currently selected token, if any.

        - Reset the selected token index
        - Remove token highlights by filtering out any ExtraSelections with the
          token highlight property (:attr:`TOKEN_HIGHLIGHT_PROPERTY`)
        - Set the new extra selections on the text edit
        - Emit the :attr:`token_deselected` signal
        """
        self.selected_token_index = None
        selections = self.text_edit.extraSelections()
        # Remove token highlights
        selections = [
            s
            for s in selections
            if not s.format.property(TOKEN_HIGHLIGHT_PROPERTY)  # type: ignore[attr-defined]
        ]
        self.text_edit.setExtraSelections(selections)
        self.text_edit.token_deselected.emit()


class FullTranslationWindow(QMainWindow):
    """
    Window for side-by-side OE and ModE translation view.
    """

    #: Width of the sidebar in pixels
    SIDEBAR_WIDTH: Final[int] = 350

    def __init__(self, project: Project, main_window: MainWindow):
        super().__init__(main_window)
        self.project = project
        self.main_window = main_window
        self.setWindowTitle(f"Full Translation - {project.name}")
        self.resize(1200, 800)

        self.project_notes: list[tuple[int, Note]] = []
        self._collect_project_notes()
        self.build()

    def _collect_project_notes(self) -> None:
        """
        Collect all notes from all sentences in the project and number them.
        """
        self.project_notes.clear()
        note_num = 1
        for sentence in self.project.sentences:
            for note in sentence.sorted_notes:
                self.project_notes.append((note_num, note))
                note_num += 1

    def build(self) -> None:
        """
        Build the full translation window.
        """
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Horizontal layout for the whole window: [Main Content Area | Sidebar]
        self.window_layout = QHBoxLayout(central_widget)
        self.window_layout.setContentsMargins(0, 0, 0, 0)
        self.window_layout.setSpacing(0)

        # Left side: Vertical layout for [Banner | Toolbar | Text Area]
        self.main_area = QWidget()
        self.main_layout = QVBoxLayout(self.main_area)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Source Banner (Pinned)
        self.build_source_banner()
        # Toolbar
        self.build_toolbar()
        # Content columns
        self.build_content()

        # Add main area to window layout
        self.window_layout.addWidget(self.main_area, 1)

        # Sidebar (on the right side of the entire window)
        self.build_sidebar()

        # Connect signals after both edits and sidebar are created
        self.oe_edit.connect_signals()

    def build_source_banner(self) -> None:
        """
        Build the source banner.
        """
        if self.project.source:
            self.source_banner = QWidget()
            self.source_banner.setStyleSheet(
                "background-color: palette(alternate-base); "
                "border-bottom: 1px solid palette(border);"
            )
            self.source_layout = QHBoxLayout(self.source_banner)
            self.source_label = QLabel(f"<b>Source:</b> {self.project.source}")
            self.source_layout.addWidget(self.source_label)
            self.main_layout.addWidget(self.source_banner, 0)  # 0 stretch factor

    def build_toolbar(self) -> None:
        """
        Build the toolbar.
        """
        self.toolbar = QWidget()
        self.toolbar.setStyleSheet(
            "background-color: palette(base); border-bottom: 1px solid palette(border);"
        )
        self.toolbar_layout = QHBoxLayout(self.toolbar)
        self.build_search_input()
        self.build_toggle_sidebar_btn()
        self.build_export_btn()
        self.main_layout.addWidget(self.toolbar, 0)  # 0 stretch factor

    def build_search_input(self) -> None:
        """
        Build the search input.
        """
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search full translation...")
        self.search_input.textChanged.connect(self._on_search_changed)
        self.toolbar_layout.addWidget(QLabel("Search:"))
        self.toolbar_layout.addWidget(self.search_input)

    def build_toggle_sidebar_btn(self) -> None:
        """
        Build the toggle sidebar button.
        """
        self.toggle_sidebar_btn = QPushButton("Show Details")
        self.toggle_sidebar_btn.setCheckable(True)
        self.toggle_sidebar_btn.clicked.connect(self._toggle_sidebar)
        self.toolbar_layout.addWidget(self.toggle_sidebar_btn)

    def build_export_btn(self) -> None:
        """
        Build the export button.
        """
        self.export_btn = QPushButton("Export DOCX (Landscape)")
        self.export_btn.clicked.connect(self._export_docx)
        self.toolbar_layout.addWidget(self.export_btn)

    def build_content(self) -> None:
        """
        Build the content: OE and ModE columns.
        """
        # Text Content Splitter (OE and ModE columns)
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.build_oe_edit()
        self.build_modern_english_edit()
        # Synchronized Scrolling
        self.oe_edit.verticalScrollBar().valueChanged.connect(
            self.mode_edit.verticalScrollBar().setValue
        )
        self.mode_edit.verticalScrollBar().valueChanged.connect(
            self.oe_edit.verticalScrollBar().setValue
        )
        self.splitter.addWidget(self.oe_edit)
        self.splitter.addWidget(self.mode_edit)
        # Add splitter to main layout
        self.main_layout.addWidget(
            self.splitter, 1
        )  # 1 stretch factor - fills remaining space

        # Add Notes Area underneath splitter
        self.notes_area = FullProjectNotesArea(self.project_notes, self)
        self.notes_area.setMaximumHeight(200)  # Limit height of notes area
        self.notes_area.note_clicked.connect(self._on_note_clicked)
        self.main_layout.addWidget(self.notes_area, 0)

    def build_oe_edit(self) -> None:
        """
        Build the OE edit.
        """
        self.oe_edit = FullProjectOldEnglishTextEdit(self.project, self)
        self.oe_edit.setFont(QFont("Anvers", 16))
        self.oe_edit.sentence_selected.connect(self._on_oe_sentence_selected)
        self.oe_edit.token_selected.connect(self._on_token_selected)
        self.oe_edit.idiom_selection.connect(self._on_idiom_selected)
        self.oe_edit.token_deselected.connect(
            self._on_oe_token_deselected
        )  # Connect deselection
        self.oe_edit.token_hovered.connect(self._on_token_hovered)
        # self.oe_edit.connect_signals() will be called after sidebar is created

    def build_modern_english_edit(self) -> None:
        """
        Build the modern english edit.
        """
        self.mode_edit = FullProjectModernEnglishTextEdit(self.project, self)
        self.mode_edit.setFont(QFont("Helvetica", 16))
        self.mode_edit.sentence_selected.connect(self._on_mode_sentence_selected)
        self.mode_edit.sentence_deselected.connect(self._on_mode_sentence_deselected)

    def build_sidebar(self) -> None:
        """
        Build the sidebar.
        """
        self.token_details_sidebar = FullTranslationSidebar(self)
        self.token_details_sidebar.setMaximumWidth(0)  # Initially closed
        self.window_layout.addWidget(self.token_details_sidebar, 0)  # 0 stretch factor

    # ------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------

    def _on_oe_sentence_selected(self, sentence_id: int) -> None:
        """
        Event handler for OE sentence selected:  Highlight the corresponding
        ModE sentence.

        Args:
            sentence_id: ID of the sentence to highlight

        """
        self.mode_edit.highlight_sentence(sentence_id)

    def _on_oe_token_deselected(self) -> None:
        """
        Event handler for OE token deselected: Clear ModE highlighting if not
        explicitly selected.

        Args:
            sentence_id: ID of the sentence to highlight

        """
        if self.mode_edit._selected_sentence_id is None:
            self.mode_edit.highlight_sentence(None)

    def _on_mode_sentence_selected(self, sentence_id: int) -> None:
        """
        Event handler for ModE sentence selected: Highlight the corresponding
        OE sentence.

        Args:
            sentence_id: ID of the sentence to highlight

        """
        # Deselect any active token selection before highlighting the sentence
        # context
        cast("OldEnglishTextSelector", self.oe_edit.selector).deselect()
        self.oe_edit.highlight_sentence(sentence_id)
        self.deselect_all_notes()

    def _on_mode_sentence_deselected(self) -> None:
        """ModE sentence deselected -> clear OE highlighting."""
        self.oe_edit.highlight_sentence(None)

    def _on_token_selected(self, token: Token) -> None:  # noqa: ARG002
        """
        Event handler for token selected: Highlight the corresponding ModE sentence
        and ensure sidebar is open.

        Args:
            token: Selected token (unused)

        """
        # Highlight is now handled via sentence_selected signal,
        # but we use this to open the sidebar.
        if not self.token_details_sidebar._is_sidebar_open:
            self._toggle_sidebar(True)  # noqa: FBT003
        self.deselect_all_notes()

    def deselect_all_notes(self) -> None:
        """
        Deselect all notes in the UI and clear highlights.
        """
        if hasattr(self, "notes_area"):
            for widget in self.notes_area.note_widgets.values():
                widget.set_selected(False)
        self.oe_edit.clear_all_note_highlights()

    def _on_idiom_selected(self, idiom: Idiom) -> None:  # noqa: ARG002
        """
        Ensure sidebar is open for idiom details.

        Args:
            idiom: Selected idiom (unused)

        """
        if not self.token_details_sidebar._is_sidebar_open:
            self._toggle_sidebar(True)  # noqa: FBT003

    def _on_token_hovered(self, token: Token | None) -> None:
        """
        Light hover effect for aligned sentences.

        Args:
            token: Token hovered (unused)

        """
        # Clear previous hover by resetting translation highlight if nothing hovered
        # But we only want to do this if nothing is selected.
        # For now, let's just use the highlight_sentence with a very light color
        # for hover.
        if token:
            # We could implement a specific hover highlight color here
            pass

    def _on_search_changed(self, text: str) -> None:
        """
        Event handler for search changed: Highlight the search text in both
        the OE and ModE columns, and the notes area.

        Args:
            text: Search text

        """
        SearchHighlighter.highlight_text(self.oe_edit, text)
        SearchHighlighter.highlight_text(self.mode_edit, text)
        self.notes_area.highlight_search(text)

    def _on_note_clicked(self, note_num: int) -> None:
        """
        Handle clicking on a note in the notes area.
        """
        # Find the note
        note = next((n for num, n in self.project_notes if num == note_num), None)
        if not note:
            return

        target_widget = self.notes_area.note_widgets.get(note_num)
        was_selected = target_widget.is_selected

        # Always deselect all notes in the UI first
        for widget in self.notes_area.note_widgets.values():
            widget.set_selected(False)

        # Clear all note highlights in the OE edit
        self.oe_edit.clear_all_note_highlights()

        # If it wasn't selected, select it now
        if not was_selected:
            target_widget.set_selected(True)
            self.oe_edit.highlight_note_tokens(note, True)

    def _toggle_sidebar(self, checked: bool) -> None:  # noqa: FBT001
        """
        Event handler for sidebar toggle: Animate the sidebar width so
        that it opens or closes smoothly.

        Args:
            checked: Whether the sidebar is checked

        """
        self.token_details_sidebar.set_sidebar_open(checked)
        target_sidebar_width = self.SIDEBAR_WIDTH if checked else 0

        if checked:
            self.token_details_sidebar.setMinimumWidth(self.SIDEBAR_WIDTH)
        else:
            self.token_details_sidebar.setMinimumWidth(0)

        self.animation = QPropertyAnimation(self.token_details_sidebar, b"maximumWidth")
        self.animation.setDuration(300)
        self.animation.setStartValue(self.token_details_sidebar.width())
        self.animation.setEndValue(target_sidebar_width)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()

        self.toggle_sidebar_btn.setText("Hide Details" if checked else "Show Details")

    def _navigate_to_main_sentence(self, sentence_id: int) -> None:
        """Scroll main window to sentence and focus."""
        for card in self.main_window.sentence_cards:
            if card.sentence.id == sentence_id:
                self.main_window.ensure_visible(card)
                card.focus()
                break

    def _export_docx(self) -> None:
        """Export to landscape DOCX."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Side-by-Side",
            f"{self.project.name}_side_by_side.docx",
            "Word Documents (*.docx)",
        )
        if file_path:
            exporter = DOCXExporter()
            if exporter.export_side_by_side(self.project.id, Path(file_path)):
                self.main_window.messages.show_message("Exported successfully")
            else:
                self.main_window.messages.show_error("Export failed")


class FullProjectNoteWidget(ThemeMixin, QWidget):
    """Widget for a single note in the notes area."""

    clicked = Signal(int)  # emits note_num

    def __init__(self, note_num: int, note: Note, parent: QWidget | None = None):
        super().__init__(parent)
        self.note_num = note_num
        self.note = note
        self.is_selected = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.label = QLabel(f"<b>{note_num}.</b> {note.note_text_md}")
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.clicked.emit(self.note_num)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.is_selected = selected
        if selected:
            self.setStyleSheet(
                "background-color: palette(highlight); color: palette(highlighted-text);"
            )
        else:
            self.setStyleSheet("")


class FullProjectNotesArea(QScrollArea):
    """Area displaying all project notes."""

    note_clicked = Signal(int)

    def __init__(
        self, project_notes: list[tuple[int, Note]], parent: QWidget | None = None
    ):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.container = QWidget()
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self.container)

        self.note_widgets: dict[int, FullProjectNoteWidget] = {}

        if not project_notes:
            self.main_layout.addWidget(QLabel("No notes in this project."))
        else:
            for note_num, note in project_notes:
                widget = FullProjectNoteWidget(note_num, note)
                widget.clicked.connect(self.note_clicked.emit)
                self.main_layout.addWidget(widget)
                self.note_widgets[note_num] = widget

    def set_note_selected(self, note_num: int, selected: bool) -> None:
        if note_num in self.note_widgets:
            self.note_widgets[note_num].set_selected(selected)

    def highlight_search(self, text: str) -> None:
        """
        Highlight search matches in note widgets.
        """
        for widget in self.note_widgets.values():
            original_content = widget.note.note_text_md
            if not text:
                widget.label.setText(f"<b>{widget.note_num}.</b> {original_content}")
                continue

            # Case-insensitive search and replacement using HTML
            if text.lower() in original_content.lower():
                highlighted = re.sub(
                    f"({re.escape(text)})",
                    r'<span style="background-color: #ffeb3b; color: black;">\1</span>',
                    original_content,
                    flags=re.IGNORECASE,
                )
                widget.label.setText(f"<b>{widget.note_num}.</b> {highlighted}")
            else:
                widget.label.setText(f"<b>{widget.note_num}.</b> {original_content}")

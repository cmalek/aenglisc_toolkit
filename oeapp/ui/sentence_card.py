"""Sentence card UI component."""

from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtCore import QPoint, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    Qt,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oeapp.commands import (
    AddSentenceCommand,
    AnnotateTokenCommand,
    CommandManager,
    DeleteSentenceCommand,
    EditSentenceCommand,
    MergeSentenceCommand,
    ToggleParagraphStartCommand,
)
from oeapp.mixins import TokenOccurrenceMixin
from oeapp.models import Annotation, Idiom
from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence
from oeapp.ui.dialogs import (
    AnnotationModal,
    CaseFilterDialog,
    NoteDialog,
    POSFilterDialog,
)
from oeapp.ui.notes_panel import NotesPanel
from oeapp.ui.token_table import TokenTable
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
    from oeapp.models.note import Note
    from oeapp.models.token import Token
    from oeapp.ui.main_window import MainWindow


class ClickableTextEdit(QTextEdit):
    """
    QTextEdit that emits a signal when clicked.

    This currently handles:

    - Mouse clicks
    - Double mouse clicks
    - Key presses for annotation copy/paste

    """

    clicked = Signal(QPoint, object)  # position, modifiers
    double_clicked = Signal(QPoint)
    # Signals for annotation copy/paste
    copy_annotation_requested = Signal()
    paste_annotation_requested = Signal()

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse press event and emit clicked signal."""
        super().mousePressEvent(event)
        self.clicked.emit(event.position().toPoint(), event.modifiers())

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse double-click event and emit double_clicked signal."""
        super().mouseDoubleClickEvent(event)
        self.double_clicked.emit(event.position().toPoint())

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """
        Handle key press events for annotation copy/paste.

        Intercepts Cmd/Ctrl+C and Cmd/Ctrl+V to emit signals for annotation
        copy/paste when a token is selected.

        Args:
            event: Key event

        """
        if event.matches(QKeySequence.StandardKey.Copy):
            self.copy_annotation_requested.emit()
            event.accept()
            return
        if event.matches(QKeySequence.StandardKey.Paste):
            self.paste_annotation_requested.emit()
            event.accept()
            return

        # For arrow keys, ignore them so they bubble up to SentenceCard
        # when a token is selected (SentenceCard will handle navigation)
        # ONLY if we are in read-only mode (not editing OE)
        if self.isReadOnly() and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
            event.ignore()
            return

        # For all other keys, use default behavior
        super().keyPressEvent(event)


class SentenceCard(TokenOccurrenceMixin, SessionMixin, QWidget):
    """
    Widget representing a sentence card with annotations.

    Args:
        sentence: Sentence model instance

    Keyword Args:
        command_manager: Command manager for undo/redo
        parent: Parent widget

    """

    # Signal emitted when a sentence is merged
    sentence_merged = Signal(int)  # Emits current sentence ID
    # Signal emitted when a sentence is added
    sentence_added = Signal(int)  # Emits new sentence ID
    # Signal emitted when a sentence is deleted
    sentence_deleted = Signal(int)  # Emits deleted sentence ID
    # Signal emitted when a token is selected for details sidebar
    # Note: Using object for SentenceCard to avoid circular import
    token_selected_for_details = Signal(
        object, object, object
    )  # Token, Sentence, SentenceCard
    idiom_selected_for_details = Signal(
        object, object, object
    )  # Idiom, Sentence, SentenceCard
    # Signal emitted when an annotation is applied
    annotation_applied = Signal(Annotation)

    # Property ID for token index in QTextCharFormat
    TOKEN_INDEX_PROPERTY: ClassVar[int] = 1000
    # Property ID for selection highlight in ExtraSelection
    SELECTION_HIGHLIGHT_PROPERTY: ClassVar[int] = 1001

    #: Color maps for highlighting POS tags
    POS_COLORS: ClassVar[dict[str | None, QColor]] = {
        "N": QColor(173, 216, 230),  # Light blue for Noun
        "V": QColor(255, 182, 193),  # Light pink for Verb
        "A": QColor(144, 238, 144),  # Light green for Adjective
        "R": QColor(255, 165, 0),  # Orange for Pronoun
        "D": QColor(221, 160, 221),  # Plum for Determiner/Article
        "B": QColor(175, 238, 238),  # Pale turquoise for Adverb
        "C": QColor(255, 20, 147),  # Deep pink for Conjunction
        "E": QColor(255, 255, 0),  # Yellow for Preposition
        "I": QColor(255, 192, 203),  # Pink for Interjection
        None: QColor(255, 255, 255),  # White (no highlight) for unannotated
    }

    #: Color maps for highlighting cases
    CASE_COLORS: ClassVar[dict[str | None, QColor]] = {
        "n": QColor(173, 216, 230),  # Light blue for Nominative
        "a": QColor(144, 238, 144),  # Light green for Accusative
        "g": QColor(255, 255, 153),  # Light yellow for Genitive
        "d": QColor(255, 200, 150),  # Light orange for Dative
        "i": QColor(255, 182, 193),  # Light pink for Instrumental
        None: QColor(255, 255, 255),  # White (no highlight) for unannotated
    }

    #: Color maps for highlighting numbers
    NUMBER_COLORS: ClassVar[dict[str | None, QColor]] = {
        "s": QColor(173, 216, 230),  # Light blue for Singular
        "d": QColor(144, 238, 144),  # Light green for Dual
        "pl": QColor(255, 127, 127),  # Light coral for Plural
        "p": QColor(255, 127, 127),  # Light coral for Plural (Verbs)
        None: QColor(255, 255, 255),  # White (no highlight) for unannotated
    }

    #: Color for idiom selection (pale magenta)
    IDIOM_SELECTION_COLOR: ClassVar[QColor] = QColor(255, 200, 255, 150)
    #: Color for idiom highlighting mode (pale magenta)
    IDIOM_HIGHLIGHT_COLOR: ClassVar[QColor] = QColor(255, 200, 255)

    def __init__(
        self,
        sentence: Sentence,
        command_manager: CommandManager | None = None,
        main_window: MainWindow | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.sentence = sentence
        self.session = self._get_session()
        self.command_manager = command_manager
        self.main_window = main_window
        self.token_table = TokenTable()
        self.tokens: list[Token] = sentence.tokens
        self.idioms: list[Idiom] = sentence.idioms
        self.annotations: dict[int, Annotation | None] = {
            cast("int", token.id): token.annotation for token in self.tokens if token.id
        }
        # Track current token select highlight position to clear it later
        self._current_highlight_start: int | None = None
        self._current_highlight_length: int | None = None
        # Track current token highlight mode (None, 'pos', 'case', 'number')
        self._current_highlight_mode: str | None = None
        # Track selected cases for highlighting (default: all cases)
        self._selected_cases: set[str] = {"n", "a", "g", "d", "i"}
        # Track selected POS tags for highlighting (default: all POS tags)
        self._selected_pos: set[str] = {"N", "V", "A", "R", "D", "B", "C", "E", "I"}
        # Case filter dialog reference
        self._case_filter_dialog: CaseFilterDialog | None = None
        # POS filter dialog reference
        self._pos_filter_dialog: POSFilterDialog | None = None
        # Track selected token index for details sidebar
        self.selected_token_index: int | None = None
        # Mapping of token order_index to Token object
        self.tokens_by_index: dict[int, Token] = {}
        # Mapping of token order_index to index in self.tokens list
        self.order_to_list_index: dict[int, int] = {}
        # Mapping of token ID to its (start, end) position in the editor
        self._token_positions: dict[int, tuple[int, int]] = {}
        # Track selected token range for notes (start_index, end_index inclusive)
        self._selected_token_range: tuple[int, int] | None = None
        # Timer to delay deselection to allow double-click to cancel it
        self._deselect_timer = QTimer(self)
        self._deselect_timer.setSingleShot(True)
        self._deselect_timer.timeout.connect(self._perform_deselection)
        self._pending_deselect_token_index: int | None = None
        # Track OE edit mode state
        self._oe_edit_mode: bool = False
        self._original_oe_text: str | None = None
        self.build()

    @property
    def has_focus(self) -> bool:
        """
        Check if this sentence card has focus.
        """
        return any(
            [
                self.hasFocus(),
                self.token_table.has_focus,
                self.translation_edit.hasFocus(),
                self.oe_text_edit.hasFocus(),
            ]
        )

    def _next_token(self) -> None:
        """
        Navigate to next token in the sentence and in the token table.

        - If no token is selected, do nothing.
        - If the last token is selected, do nothing.
        """
        if not self.tokens or self.selected_token_index is None:
            return

        current_list_index = self.order_to_list_index.get(self.selected_token_index)
        if current_list_index is not None and current_list_index < len(self.tokens) - 1:
            next_list_index = current_list_index + 1
        else:
            # Already at last token or invalid index
            return

        token = self.tokens[next_list_index]
        self.selected_token_index = token.order_index
        self.token_table.select_token(next_list_index)
        self._highlight_token_in_text(token)
        self.token_selected_for_details.emit(token, self.sentence, self)

    def _prev_token(self) -> None:
        """
        Navigate to previous token in the sentence and in the token table.

        - If no token is selected, do nothing.
        - If the first token is selected, do nothing.
        """
        if not self.tokens or self.selected_token_index is None:
            return

        current_list_index = self.order_to_list_index.get(self.selected_token_index)
        if current_list_index is not None and current_list_index > 0:
            prev_list_index = current_list_index - 1
        else:
            # Already at first token or invalid index
            return

        token = self.tokens[prev_list_index]
        self.selected_token_index = token.order_index
        self.token_table.select_token(prev_list_index)
        self._highlight_token_in_text(token)
        self.token_selected_for_details.emit(token, self.sentence, self)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        """
        Handle keyboard shortcuts for annotation copy/paste.

        Intercepts Cmd/Ctrl+C and Cmd/Ctrl+V when a token is selected,
        otherwise lets Qt handle the event normally.

        Args:
            event: Key event

        """
        # Check for copy/paste shortcuts only when a token is selected
        # and NOT in edit mode
        if (
            self.selected_token_index is not None
            and self.main_window
            and not self._oe_edit_mode
        ):
            if event.matches(QKeySequence.StandardKey.Copy):
                self.main_window.action_service.copy_annotation()
                event.accept()
                return
            if event.matches(QKeySequence.StandardKey.Paste):
                self.main_window.action_service.paste_annotation()
                event.accept()
                return
            # If right arrow key is pressed, navigate to next token
            if event.key() == Qt.Key.Key_Right:
                self._next_token()
                event.accept()
                return
            # If left arrow key is pressed, navigate to previous token
            if event.key() == Qt.Key.Key_Left:
                self._prev_token()
                event.accept()
                return

            # If Enter/Return is pressed and not in edit mode, open annotation modal
            if (
                event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
                and not self._oe_edit_mode
            ):
                self._open_annotation_modal()
                event.accept()
                return

        # For all other keys, use default behavior
        super().keyPressEvent(event)

    def _on_copy_annotation_requested(self) -> None:
        """Handle copy annotation request from OE text edit."""
        if self.selected_token_index is not None and self.main_window:
            self.main_window.action_service.copy_annotation()

    def _on_paste_annotation_requested(self) -> None:
        """Handle paste annotation request from OE text edit."""
        if self.selected_token_index is not None and self.main_window:
            self.main_window.action_service.paste_annotation()

    def build_paragraph_header(self) -> QLabel:
        """
        Add the paragraph header to the layout and return the sentence number label.

        - Add Display Order
        - Add Paragraph Number
        - Add Sentence Number

        Args:
            layout: Layout to add the paragraph header to

        """
        paragraph_num = self.sentence.paragraph_number
        sentence_num = self.sentence.sentence_number_in_paragraph
        self.sentence_number_label = QLabel(
            f"[{self.sentence.display_order}] ¶:{paragraph_num} S:{sentence_num}"
        )
        self.sentence_number_label.setFont(QFont("Helvetica", 14, QFont.Weight.Bold))
        return self.sentence_number_label

    def build_top_row_action_buttons(self) -> QHBoxLayout:
        """
        Add the top row action buttons to the layout and return the layout.

        - Add Sentence Button with menu for adding a sentence before or after
        - Toggle Paragraph Start button with menu for toggling the paragraph start
        - Merge with next button
        - Delete button

        Returns:
            Layout with the top row action buttons

        """
        layout = QHBoxLayout()
        self.add_sentence_button = QPushButton("Add Sentence")
        # Create menu for Add Sentence button
        add_sentence_menu = QMenu(self)
        before_action = add_sentence_menu.addAction("Before")
        before_action.triggered.connect(self._on_add_sentence_before_clicked)
        after_action = add_sentence_menu.addAction("After")
        after_action.triggered.connect(self._on_add_sentence_after_clicked)
        self.add_sentence_button.setMenu(add_sentence_menu)
        self.toggle_paragraph_button = QPushButton("Toggle Paragraph Start")
        self.toggle_paragraph_button.clicked.connect(self._on_toggle_paragraph_clicked)
        self._update_paragraph_button_state()
        # Hide toggle button for first sentence (must always be paragraph start)
        if self.sentence.display_order == 1:
            self.toggle_paragraph_button.setVisible(False)
        self.merge_button = QPushButton("Merge with next")
        self.merge_button.clicked.connect(self._on_merge_clicked)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self._on_delete_clicked)
        layout.addStretch()
        layout.addWidget(self.add_sentence_button)
        layout.addWidget(self.toggle_paragraph_button)
        layout.addWidget(self.merge_button)
        layout.addWidget(self.delete_button)
        return layout

    def build_oe_text_label_line(self) -> QHBoxLayout:
        """
        Add the OE text label line to the layout.

        - Add "Old English:" label
        - Add Add Note button
        - Add Edit OE button
        - Add Save OE button
        - Add Cancel Edit button
        - Add Dropdown for highlighting options

            - Part of Speech
            - Case
            - Number

        Returns:
            Layout with the OE text label line

        """
        layout = QHBoxLayout()
        # Add "Old English:" label
        self.oe_label = QLabel("Old English:")
        self.oe_label.setFont(QFont("Anvers", 18))
        layout.addWidget(self.oe_label)
        layout.addStretch()

        # Add Note button
        self.add_note_button = QPushButton("Add Note")
        self.add_note_button.clicked.connect(self._on_add_note_clicked)
        self.add_note_button.setEnabled(False)  # Disabled until tokens are selected
        layout.addWidget(self.add_note_button)

        # Edit OE button
        self.edit_oe_button = QPushButton("Edit OE")
        self.edit_oe_button.clicked.connect(self._on_edit_oe_clicked)
        layout.addWidget(self.edit_oe_button)

        # Save OE and Cancel Edit buttons (initially hidden)
        self.save_oe_button = QPushButton("Save OE")
        self.save_oe_button.clicked.connect(self._on_save_oe_clicked)
        self.save_oe_button.setVisible(False)
        layout.addWidget(self.save_oe_button)

        self.cancel_edit_button = QPushButton("Cancel Edit")
        self.cancel_edit_button.clicked.connect(self._on_cancel_edit_clicked)
        self.cancel_edit_button.setVisible(False)
        layout.addWidget(self.cancel_edit_button)

        highlighting_label = QLabel("Highlighting:")
        layout.addWidget(highlighting_label)
        self.highlighting_combo = QComboBox()
        self.highlighting_combo.addItems(
            ["None", "Part of Speech", "Case", "Number", "Idioms"]
        )
        self.highlighting_combo.currentIndexChanged.connect(
            self._on_highlighting_changed
        )
        layout.addWidget(self.highlighting_combo)

        return layout

    def build_oe_text_edit(self) -> ClickableTextEdit:
        """
        Build the OE text edit widget.

        Returns:
            OE text edit widget

        """
        oe_text_edit = ClickableTextEdit()
        oe_text_edit.setPlainText(self.sentence.text_oe)
        oe_text_edit.setFont(QFont("Anvers", 18))
        oe_text_edit.setPlaceholderText("Enter Old English text...")
        # Make read-only by default (selectable but not editable)
        oe_text_edit.setReadOnly(True)
        oe_text_edit.textChanged.connect(self._on_oe_text_changed)
        oe_text_edit.clicked.connect(self._on_oe_text_clicked)
        oe_text_edit.double_clicked.connect(self._on_oe_text_double_clicked)
        oe_text_edit.copy_annotation_requested.connect(
            self._on_copy_annotation_requested
        )
        oe_text_edit.paste_annotation_requested.connect(
            self._on_paste_annotation_requested
        )
        # set the maximum height of the oe_text_edit to just fit the text
        # and its superscripts
        oe_text_edit.document().setTextWidth(oe_text_edit.viewport().width())
        margins = oe_text_edit.contentsMargins()
        height = int(
            oe_text_edit.document().size().height() + margins.top() + margins.bottom()
        )
        oe_text_edit.setFixedHeight(int(height * 0.8))
        # Render OE text with superscripts after setting up the widget
        # Use QTimer.singleShot to ensure widget is fully initialized
        QTimer.singleShot(0, self._render_oe_text_with_superscripts)
        return oe_text_edit

    def build_token_table(self) -> QPushButton:
        """
        Build the token table widget.

        Returns:
            Button to toggle the token table

        """
        # Token annotation grid (hidden by default)
        self.token_table.annotation_requested.connect(self._open_annotation_modal)
        self.token_table.token_selected.connect(self._on_token_table_token_selected)
        self.token_table.setVisible(False)
        self.set_tokens(self.tokens)
        button = QPushButton("Show Token Table")
        button.clicked.connect(self._toggle_token_table)
        return button

    def build_translation_edit(self) -> tuple[QHBoxLayout, QTextEdit]:
        """
        Build the translation edit widget.

        Returns:
            Tuple with the layout and the translation edit widget

        """
        layout = QHBoxLayout()
        # Label for the translation edit
        translation_label = QLabel("Modern English Translation:")
        translation_label.setFont(QFont("Helvetica", 16))
        layout.addWidget(translation_label)
        layout.addStretch()

        # Toggle button for token table
        layout.addWidget(self.token_table_toggle_button)

        # Translation edit
        edit = QTextEdit()
        edit.setPlainText(self.sentence.text_modern or "")
        edit.setFont(QFont("Helvetica", 16))
        edit.setPlaceholderText("Enter Modern English translation...")
        edit.setMaximumHeight(100)
        edit.textChanged.connect(self._on_translation_changed)
        return layout, edit

    def build_notes_panel(self) -> tuple[QLabel, NotesPanel]:
        """
        Build the notes panel widget.

        Returns:
            Notes panel widget

        """
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont("Helvetica", 10))

        notes_panel = NotesPanel(sentence=self.sentence, parent=self)
        notes_panel.note_clicked.connect(self._on_note_clicked)
        notes_panel.note_double_clicked.connect(self._on_note_double_clicked)
        return notes_label, notes_panel

    def build(self) -> None:
        """
        Build the sentence card widget.

        - Paragraph header: [Display Order] ¶:Paragraph Number S:Sentence Number
        - Top row action buttons:

            - Add Sentence Button with menu for adding a sentence before or after
            - Toggle Paragraph Start button with menu for toggling the paragraph start
            - Merge with next button
            - Delete button

        - Old English text label, and its buttons and highlighting dropdown

            - Old English: label
            - Add Note button
            - Edit OE button
            - Save OE button
            - Cancel Edit button
            - Dropdown for highlighting options: Part of Speech, Case, Number

        - Add Old English text edit itself
        - Add Token annotation grid (hidden by default)
        - Add Modern English translation edit with toggle button for token table
        - Add Notes section

        Returns:
            Sentence card widget

        """
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Add paragraph header: [Display Order] ¶:Paragraph Number S:Sentence Number
        layout.addWidget(self.build_paragraph_header())
        # Action buttons
        layout.addLayout(self.build_top_row_action_buttons())
        # Old English text line (editable) its buttons and highlighting dropdown
        layout.addLayout(self.build_oe_text_label_line())
        # Old English text edit
        self.oe_text_edit = self.build_oe_text_edit()
        layout.addWidget(self.oe_text_edit)
        # Token annotation grid (hidden by default)
        self.token_table_toggle_button = self.build_token_table()
        layout.addWidget(self.token_table)
        # Modern English translation edit
        translation_label_layout, self.translation_edit = self.build_translation_edit()
        layout.addLayout(translation_label_layout)
        layout.addWidget(self.translation_edit)
        # Notes section
        notes_label, self.notes_panel = self.build_notes_panel()
        layout.addWidget(notes_label)
        layout.addWidget(self.notes_panel)
        # Update notes display on initialization
        self._update_notes_display()

        layout.addStretch()

    def set_tokens(self, _tokens: list[Token] | None = None):
        """
        Set tokens for this sentence card.  This will also load the annotations
        for the tokens.

        Args:
            _tokens: List of tokens (optional, ignored in favor of
                self.sentence.sorted_tokens)

        """
        # Ensure tokens are sorted by their position in the text
        # We always use the sentence's sorted_tokens as the source of truth for order
        # as requested in the plan.
        sorted_tokens, _ = self.sentence.sorted_tokens
        self.tokens = sorted_tokens
        self.idioms = self.sentence.idioms

        self.tokens_by_index = {t.order_index: t for t in self.tokens}
        self.order_to_list_index = {t.order_index: i for i, t in enumerate(self.tokens)}
        self.annotations = {
            cast("int", token.id): token.annotation for token in self.tokens if token.id
        }
        self.token_table.set_tokens(self.tokens)

        # Re-apply highlighting if a mode is active
        if self._current_highlight_mode == "pos":
            self._apply_pos_highlighting()
        elif self._current_highlight_mode == "case":
            self._apply_case_highlighting()
        elif self._current_highlight_mode == "number":
            self._apply_number_highlighting()

    def _open_annotation_modal(self) -> None:
        """Open annotation modal for selected token or idiom."""
        # 1. Check for selected idiom range
        if self._selected_token_range:
            start_order, end_order = self._selected_token_range
            idiom = self._find_matching_idiom(start_order, end_order)
            if idiom:
                self._open_idiom_modal(idiom)
                return

            # If it's a new selection, we might want to create an idiom
            # For now, let's just open the modal for the range and create idiom on apply
            # Actually, the prompt says "show all the tokens selected as the main token"
            self._open_new_idiom_modal(start_order, end_order)
            return

        # 2. Check for single token selection
        token: Token | None = self.token_table.get_selected_token()
        if not token and self.selected_token_index is not None:
            token = self.tokens_by_index.get(self.selected_token_index)

        if not token:
            # Select first token if none selected
            if self.tokens:
                token = self.tokens[0]
                self.token_table.select_token(0)
            else:
                return

        # Check if this token is part of an idiom
        idiom = self._find_idiom_at_order_index(token.order_index)
        if idiom:
            self._open_idiom_modal(idiom)
            return

        # Open normal token modal
        self._open_token_modal(token)

    def _find_matching_idiom(self, start_order: int, end_order: int) -> Idiom | None:
        """Find an idiom that exactly matches the given range."""
        for idiom in self.idioms:
            if (
                idiom.start_token.order_index == start_order
                and idiom.end_token.order_index == end_order
            ):
                return idiom
        return None

    def _open_idiom_modal(self, idiom: Idiom) -> None:
        """Open annotation modal for an existing idiom."""
        annotation = idiom.annotation
        if annotation is None:
            annotation = Annotation(idiom_id=idiom.id)

        # We'll need to update AnnotationModal to take a list of tokens or an Idiom
        modal = AnnotationModal(idiom=idiom, annotation=annotation, parent=self)
        modal.annotation_applied.connect(self._on_annotation_applied)
        modal.exec()

    def _open_new_idiom_modal(self, start_order: int, end_order: int) -> None:
        """Open annotation modal for a new idiom."""
        # Create a temporary idiom object (not saved yet)
        start_token = self.tokens_by_index[start_order]
        end_token = self.tokens_by_index[end_order]
        idiom = Idiom(
            sentence_id=self.sentence.id,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
        )
        idiom.start_token = start_token
        idiom.end_token = end_token

        annotation = Annotation()

        modal = AnnotationModal(idiom=idiom, annotation=annotation, parent=self)
        modal.annotation_applied.connect(self._on_idiom_annotation_applied)
        modal.exec()

    def _open_token_modal(self, token: Token) -> None:
        """Open annotation modal for a single token."""
        annotation = token.annotation
        if annotation is None and token.id:
            annotation = Annotation.get_by_token(token.id)

        modal = AnnotationModal(token=token, annotation=annotation, parent=self)
        modal.annotation_applied.connect(self._on_annotation_applied)
        modal.exec()

    def _on_idiom_annotation_applied(self, annotation: Annotation) -> None:
        """Handle annotation applied for a new idiom (needs creation)."""
        # Create the idiom first
        idiom = annotation.idiom  # This was passed to the modal
        idiom.save()

        # Link annotation to idiom
        annotation.idiom_id = idiom.id
        self._on_annotation_applied(annotation)

        # Refresh idioms
        self.session.refresh(self.sentence)
        self.idioms = self.sentence.idioms
        self._render_oe_text_with_superscripts()

    def _on_annotation_applied(self, annotation: Annotation) -> None:
        """Handle annotation applied signal."""
        before_state = self._get_annotation_state(annotation)
        after_state = self._extract_annotation_state(annotation)

        if self.command_manager:
            self._execute_annotate_command(annotation, before_state, after_state)
        else:
            self._save_annotation(annotation)

        self._finalize_annotation_update(annotation)

    def _get_annotation_state(self, annotation: Annotation) -> dict:
        """Get the current state of an annotation before updates."""
        token_id = annotation.token_id
        idiom_id = annotation.idiom_id

        existing = None
        if token_id:
            existing = self.annotations.get(token_id)
        elif idiom_id:
            existing = Annotation.get_by_idiom(idiom_id)

        return self._extract_annotation_state(existing) if existing else {}

    def _extract_annotation_state(self, annotation: Annotation) -> dict:
        """Extract morphological state from an annotation object."""
        return {
            "pos": annotation.pos,
            "gender": annotation.gender,
            "number": annotation.number,
            "case": annotation.case,
            "declension": annotation.declension,
            "pronoun_type": annotation.pronoun_type,
            "pronoun_number": annotation.pronoun_number,
            "verb_class": annotation.verb_class,
            "verb_tense": annotation.verb_tense,
            "verb_person": annotation.verb_person,
            "verb_mood": annotation.verb_mood,
            "verb_aspect": annotation.verb_aspect,
            "verb_form": annotation.verb_form,
            "prep_case": annotation.prep_case,
            "adverb_degree": annotation.adverb_degree,
            "adjective_inflection": annotation.adjective_inflection,
            "adjective_degree": annotation.adjective_degree,
            "conjunction_type": annotation.conjunction_type,
            "confidence": annotation.confidence,
            "modern_english_meaning": annotation.modern_english_meaning,
            "root": annotation.root,
        }

    def _execute_annotate_command(
        self, annotation: Annotation, before: dict, after: dict
    ) -> None:
        """Execute the annotate command via command manager."""
        command = AnnotateTokenCommand(
            token_id=annotation.token_id,
            idiom_id=annotation.idiom_id,
            before=before,
            after=after,
        )
        if cast("CommandManager", self.command_manager).execute(command):
            # Command manager will handle the actual save or update
            pass

    def _finalize_annotation_update(self, annotation: Annotation) -> None:
        """Update local caches and UI after annotation is applied."""
        if annotation.token_id:
            self.annotations[annotation.token_id] = annotation
            self.token_table.update_annotation(annotation)

        self.annotation_applied.emit(annotation)
        self._refresh_highlights_after_annotation()

    def _refresh_highlights_after_annotation(self) -> None:
        """Re-apply the current highlighting mode."""
        mode_map = {
            "pos": self._apply_pos_highlighting,
            "case": self._apply_case_highlighting,
            "number": self._apply_number_highlighting,
            "idioms": self._apply_idiom_highlighting,
        }
        if self._current_highlight_mode in mode_map:
            mode_map[self._current_highlight_mode]()

    def _on_token_table_token_selected(self, token: Token) -> None:
        """
        Handle token selection from the token table.

        Args:
            token: Selected token

        """
        # Cancel any pending deselection timer
        if self._deselect_timer.isActive():
            self._deselect_timer.stop()
        self._pending_deselect_token_index = None

        self.selected_token_index = token.order_index
        self._selected_token_range = None
        self._highlight_token_in_text(token)
        self.token_selected_for_details.emit(token, self.sentence, self)

    def _on_oe_text_clicked(
        self, position: QPoint, modifiers: Qt.KeyboardModifier
    ) -> None:
        """Handle click on Old English text to select corresponding token."""
        # If in edit mode, don't handle clicks for selection
        if self._oe_edit_mode:
            return

        cursor = self.oe_text_edit.cursorForPosition(position)
        cursor_pos = cursor.position()

        if not self.oe_text_edit.toPlainText() or not self.tokens:
            return

        order_index = self._find_token_at_position(cursor_pos)
        if order_index is None:
            return

        # Cancel any pending deselection
        if self._deselect_timer.isActive():
            self._deselect_timer.stop()
            self._pending_deselect_token_index = None

        if modifiers & (
            Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.ControlModifier
            | Qt.KeyboardModifier.MetaModifier
        ):
            # Cmd/Ctrl+Click for idiom selection
            self._handle_idiom_selection_click(order_index)
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Shift+click for range selection (notes)
            self._handle_range_selection_click(order_index)
        else:
            # Normal click
            self._handle_single_selection_click(order_index)

    def _handle_idiom_selection_click(self, order_index: int) -> None:
        """Handle Cmd/Ctrl+Click for idiom selection."""
        # Un-highlight and deselect any currently selected or highlighted tokens
        # if we are starting a new idiom selection or if it's already selected

        if self._selected_token_range is None:
            # Start new idiom selection
            self.selected_token_index = order_index
            self._selected_token_range = (order_index, order_index)
            # Emit signal to clear other cards and update sidebar
            token = self.tokens_by_index.get(order_index)
            if token:
                self.token_selected_for_details.emit(token, self.sentence, self)
        else:
            # Extend idiom selection
            start_order, end_order = self._selected_token_range
            new_start = min(start_order, order_index)
            new_end = max(end_order, order_index)
            self._selected_token_range = (new_start, new_end)
            self.selected_token_index = None  # Clear single selection

        self._highlight_token_range(
            self._selected_token_range[0],
            self._selected_token_range[1],
            color=self.IDIOM_SELECTION_COLOR,
        )
        self.add_note_button.setEnabled(False)

    def _handle_range_selection_click(self, order_index: int) -> None:
        """Handle Shift+Click for range selection."""
        # Clear any active idiom selection/highlight
        self._selected_token_range = None
        self._clear_highlight()

        if self.selected_token_index is not None:
            start_order = min(self.selected_token_index, order_index)
            end_order = max(self.selected_token_index, order_index)
            self._selected_token_range = (start_order, end_order)
            self._highlight_token_range(start_order, end_order)
            self.selected_token_index = None
        else:
            self._handle_single_selection_click(order_index)

        self.add_note_button.setEnabled(True)

    def _handle_single_selection_click(self, order_index: int) -> None:
        """Handle normal click for single token selection."""
        # 1. If click is within existing range selection, don't clear it yet.
        # This allows double-click to work on the selection.
        if self._selected_token_range:
            start, end = self._selected_token_range
            if start <= order_index <= end:
                # Clicked inside active range.
                # Start deselection timer so double-click can cancel it.
                self._pending_deselect_token_index = order_index
                self._deselect_timer.start(300)
                return
            # Clicked outside range, clear it
            self._selected_token_range = None

        # 2. Check if clicking a SAVED idiom token
        idiom = self._find_idiom_at_order_index(order_index)
        if idiom:
            # Select the whole idiom
            self._selected_token_range = (
                idiom.start_token.order_index,
                idiom.end_token.order_index,
            )
            self._highlight_token_range(
                self._selected_token_range[0],
                self._selected_token_range[1],
                color=self.IDIOM_SELECTION_COLOR,
            )
            self.selected_token_index = None
            self.idiom_selected_for_details.emit(idiom, self.sentence, self)
            self.add_note_button.setEnabled(False)
            return

        # 3. Standard single token selection
        if self.selected_token_index == order_index:
            self._pending_deselect_token_index = order_index
            self._deselect_timer.start(300)
        else:
            self.selected_token_index = order_index
            token = self.tokens_by_index.get(order_index)
            if token:
                self._highlight_token_in_text(token)
                self.token_selected_for_details.emit(token, self.sentence, self)
                list_index = self.order_to_list_index.get(order_index)
                if list_index is not None:
                    self.token_table.select_token(list_index)
            self.add_note_button.setEnabled(False)

    def _find_idiom_at_order_index(self, order_index: int) -> Idiom | None:
        """Find if an idiom covers the given token order index."""
        for idiom in self.idioms:
            if (
                idiom.start_token.order_index
                <= order_index
                <= idiom.end_token.order_index
            ):
                return idiom
        return None

    def _on_oe_text_double_clicked(self, position: QPoint) -> None:
        """
        Handle double-click on Old English text to open annotation dialog.

        Args:
            position: Mouse double-click position in widget coordinates

        """
        # If in edit mode, don't handle double-clicks for annotation
        if self._oe_edit_mode:
            return

        # Get cursor at click position
        cursor = self.oe_text_edit.cursorForPosition(position)
        cursor_pos = cursor.position()

        # Find which token contains this cursor position
        order_index = self._find_token_at_position(cursor_pos)
        if order_index is None:
            return

        # Cancel any pending deselection timer from the first click
        if self._deselect_timer.isActive():
            self._deselect_timer.stop()
            self._pending_deselect_token_index = None

        # Check if click is already inside current selection
        current_range = self._selected_token_range
        in_range = current_range and current_range[0] <= order_index <= current_range[1]
        is_selected = self.selected_token_index == order_index

        if not (in_range or is_selected):
            # Select the token/idiom first (e.g. if double-clicking an unselected token)
            self._handle_single_selection_click(order_index)
            # Cancel the timer started by _handle_single_selection_click
            if self._deselect_timer.isActive():
                self._deselect_timer.stop()
                self._pending_deselect_token_index = None

        # Then open the annotation modal (handles both tokens and idioms correctly)
        self._open_annotation_modal()

    def _find_token_at_position(self, position: int) -> int | None:
        """
        Find the token index that contains the given character position.

        Uses the custom TOKEN_INDEX_PROPERTY stored in the QTextCharFormat.
        Checks both the character after and before the cursor to handle edge clicks.

        Args:
            position: Character position in the document

        Returns:
            Token index if found, None otherwise

        """
        if not self.tokens:
            return None

        # Get the cursor at the position
        doc = self.oe_text_edit.document()
        cursor = QTextCursor(doc)
        cursor.setPosition(position)

        # 1. Try character AFTER the cursor (preferred for clicks on left half of char)
        if position < doc.characterCount() - 1:
            test_cursor = QTextCursor(doc)
            test_cursor.setPosition(position)
            test_cursor.movePosition(
                QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor
            )
            fmt = test_cursor.charFormat()
            val = fmt.property(self.TOKEN_INDEX_PROPERTY)
            if val is not None:
                return cast("int", val)

        # 2. Try character BEFORE the cursor (for clicks on right half of char)
        fmt = cursor.charFormat()
        val = fmt.property(self.TOKEN_INDEX_PROPERTY)
        if val is not None:
            return cast("int", val)

        return None

    def _on_oe_text_changed(self) -> None:
        """Handle Old English text change."""
        # Don't process changes if not in edit mode (shouldn't happen if signal
        # is disconnected)
        if not self._oe_edit_mode:
            return

        # Clear temporary selection highlight when text is edited
        self._clear_highlight()
        # Re-apply highlighting mode if active (though highlights will be
        # cleared when entering edit mode)
        if self._current_highlight_mode == "pos":
            self._apply_pos_highlighting()
        elif self._current_highlight_mode == "case":
            self._apply_case_highlighting()
        elif self._current_highlight_mode == "number":
            self._apply_number_highlighting()

    def _on_edit_oe_clicked(self) -> None:
        """Handle Edit OE button click - enter edit mode."""
        # Set edit mode
        self._oe_edit_mode = True
        # Clear any active idiom or single token selection
        self.selected_token_index = None
        self._selected_token_range = None
        # Store original text (plain text without superscripts)
        self._original_oe_text = self.sentence.text_oe
        # Set plain text (remove superscripts)
        self.oe_text_edit.setPlainText(self._original_oe_text)
        # Clear all highlighting
        self._clear_all_highlights()
        # Clear token selection highlight
        self._clear_highlight()
        # Reset highlighting dropdown to None (index 0)
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
        self._current_highlight_mode = None
        # Hide any open filter dialogs
        if self._pos_filter_dialog is not None:
            self._pos_filter_dialog.hide()
        if self._case_filter_dialog is not None:
            self._case_filter_dialog.hide()
        # Hide Edit OE button and Add Note button
        self.edit_oe_button.setVisible(False)
        self.add_note_button.setVisible(False)
        # Show Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(True)
        self.cancel_edit_button.setVisible(True)
        # Enable editing
        self.oe_text_edit.setReadOnly(False)
        # Disconnect textChanged signal to prevent auto-tokenization
        with suppress(TypeError):
            self.oe_text_edit.textChanged.disconnect(self._on_oe_text_changed)

    def _on_save_oe_clicked(self) -> None:
        """Handle Save OE button click - save changes and exit edit mode."""
        # Exit edit mode
        self._oe_edit_mode = False
        # Make read-only again
        self.oe_text_edit.setReadOnly(True)
        # Hide Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        # Show Edit OE button
        self.edit_oe_button.setVisible(True)
        # Reconnect textChanged signal
        self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)

        # Get new text and save
        if not self.command_manager or not self.sentence.id:
            self._original_oe_text = None
            # Re-render with superscripts
            self._render_oe_text_with_superscripts()
            return

        new_text = self.oe_text_edit.toPlainText()
        old_text = self.sentence.text_oe

        if new_text != old_text:
            command = EditSentenceCommand(
                sentence_id=self.sentence.id,
                field="text_oe",
                before=old_text,
                after=new_text,
            )
            if self.command_manager.execute(command):
                self.sentence.text_oe = new_text
                # Show any messages from the command (e.g. deleted idioms)
                if hasattr(command, "messages") and command.messages:
                    for msg in command.messages:
                        if self.main_window:
                            self.main_window.messages.show_message(msg, duration=5000)

                # Refresh tokens after retokenization
                self.session.refresh(self.sentence)
                self.set_tokens(self.sentence.tokens)
                # Update notes display
                self._update_notes_display()
                # Re-apply highlighting if a mode is active
                if self._current_highlight_mode == "pos":
                    self._apply_pos_highlighting()
                elif self._current_highlight_mode == "case":
                    self._apply_case_highlighting()
                elif self._current_highlight_mode == "number":
                    self._apply_number_highlighting()

        # Re-render with superscripts
        self._render_oe_text_with_superscripts()
        # Clear original text
        self._original_oe_text = None

    def _on_cancel_edit_clicked(self) -> None:
        """Handle Cancel Edit button click - discard changes and exit edit mode."""
        # Exit edit mode
        self._oe_edit_mode = False
        # Restore original text
        if self._original_oe_text is not None:
            self.oe_text_edit.setPlainText(self._original_oe_text)
        # Make read-only again
        self.oe_text_edit.setReadOnly(True)
        # Hide Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        # Show Edit OE button and Add Note button
        self.edit_oe_button.setVisible(True)
        self.add_note_button.setVisible(True)
        # Reconnect textChanged signal
        self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)
        # Re-render with superscripts
        self._render_oe_text_with_superscripts()
        # Clear original text
        self._original_oe_text = None

    def enter_edit_mode(self) -> bool:
        """
        Programmatically enter edit mode and focus the Old English text box.

        Returns:
            True if successful, False otherwise

        """
        if self._oe_edit_mode:
            # Already in edit mode, just focus
            self.oe_text_edit.setFocus()
            return True

        # Enter edit mode
        self._on_edit_oe_clicked()
        # Set focus on OE text edit
        self.oe_text_edit.setFocus()
        return True

    def _on_translation_changed(self) -> None:
        """Handle translation text change."""
        if not self.command_manager or not self.sentence.id:
            return

        new_text = self.translation_edit.toPlainText()
        old_text = self.sentence.text_modern or ""

        if new_text != old_text:
            command = EditSentenceCommand(
                sentence_id=self.sentence.id,
                field="text_modern",
                before=old_text,
                after=new_text,
            )
            if self.command_manager.execute(command):
                self.sentence.text_modern = new_text

    def _on_highlighting_changed(self, index: int) -> None:
        """
        Handle highlighting dropdown selection change.

        Args:
            index: Selected index (0=None, 1=Part of Speech, 2=Case, 3=Number)

        """
        # Block signals to prevent recursive calls when updating dropdown
        # programmatically
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003

        if index == 0:  # None
            self._current_highlight_mode = None
            self._clear_all_highlights()
            # Hide dialogs if they exist
            if self._pos_filter_dialog is not None:
                self._pos_filter_dialog.hide()
            if self._case_filter_dialog is not None:
                self._case_filter_dialog.hide()
        elif index == 1:  # Part of Speech
            self._current_highlight_mode = "pos"
            # Create or show the POS filter dialog
            if self._pos_filter_dialog is None:
                self._pos_filter_dialog = POSFilterDialog(self)
                self._pos_filter_dialog.pos_changed.connect(self._on_pos_changed)
                self._pos_filter_dialog.dialog_closed.connect(
                    self._on_pos_dialog_closed
                )
                # Set initial selected POS tags
                self._pos_filter_dialog.set_selected_pos(self._selected_pos)
            self._pos_filter_dialog.show()
            self._apply_pos_highlighting()
        elif index == 2:  # Case  # noqa: PLR2004
            self._current_highlight_mode = "case"
            # Create or show the case filter dialog
            if self._case_filter_dialog is None:
                self._case_filter_dialog = CaseFilterDialog(self)
                self._case_filter_dialog.cases_changed.connect(self._on_cases_changed)
                self._case_filter_dialog.dialog_closed.connect(self._on_dialog_closed)
                # Set initial selected cases
                self._case_filter_dialog.set_selected_cases(self._selected_cases)
            self._case_filter_dialog.show()
            self._apply_case_highlighting()
        elif index == 3:  # Number  # noqa: PLR2004
            self._current_highlight_mode = "number"
            self._apply_number_highlighting()
        elif index == 4:  # Idioms # noqa: PLR2004
            self._current_highlight_mode = "idioms"
            self._apply_idiom_highlighting()

        self.highlighting_combo.blockSignals(False)  # noqa: FBT003

    def _apply_idiom_highlighting(self) -> None:
        """Apply colors based on idioms."""
        self._clear_all_highlights()
        if not self.oe_text_edit.toPlainText() or not self.tokens or not self.idioms:
            return

        extra_selections = []
        for idiom in self.idioms:
            # Highlight every token in the idiom
            start_order = idiom.start_token.order_index
            end_order = idiom.end_token.order_index
            for order_idx in range(start_order, end_order + 1):
                token = self.tokens_by_index.get(order_idx)
                if token:
                    selection = self._create_token_selection(
                        token, self.IDIOM_HIGHLIGHT_COLOR
                    )
                    if selection:
                        extra_selections.append(selection)

        self.oe_text_edit.setExtraSelections(extra_selections)

    def _on_pos_toggle(self, checked: bool) -> None:  # noqa: FBT001
        """
        Handle POS highlighting toggle.

        Args:
            checked: True if the toggle is checked, False otherwise

        """
        if checked:
            # Update dropdown to Part of Speech
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(1)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(1)
        else:
            # Update dropdown to None
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(0)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(0)

    def _on_case_toggle(self, checked: bool) -> None:  # noqa: FBT001
        """Handle case highlighting toggle."""
        if checked:
            # Update dropdown to Case
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(2)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(2)
        else:
            # Update dropdown to None
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(0)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(0)

    def _on_cases_changed(self, selected_cases: set[str]) -> None:
        """
        Handle case selection changes from the dialog.

        Args:
            selected_cases: Set of selected case codes

        """
        self._selected_cases = selected_cases
        # Re-apply highlighting if case highlighting is active
        if self._current_highlight_mode == "case":
            self._apply_case_highlighting()

    def _on_dialog_closed(self) -> None:
        """Handle dialog close event by resetting the dropdown to None."""
        # Reset dropdown to None and clear highlights
        # Block signals temporarily to avoid triggering change signal
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
        # Clear highlights and reset mode (dialog is already closing, so don't hide it)
        self._current_highlight_mode = None
        self._clear_all_highlights()

    def _on_pos_changed(self, selected_pos: set[str]) -> None:
        """
        Handle POS selection changes from the dialog.

        Args:
            selected_pos: Set of selected POS codes

        """
        self._selected_pos = selected_pos
        # Re-apply highlighting if POS highlighting is active
        if self._current_highlight_mode == "pos":
            self._apply_pos_highlighting()

    def _on_pos_dialog_closed(self) -> None:
        """Handle POS dialog close event by resetting the dropdown to None."""
        # Reset dropdown to None and clear highlights
        # Block signals temporarily to avoid triggering change signal
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.highlighting_combo.setCurrentIndex(0)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
        # Clear highlights and reset mode (dialog is already closing, so don't hide it)
        self._current_highlight_mode = None
        self._clear_all_highlights()

    def _on_number_toggle(self, checked: bool) -> None:  # noqa: FBT001
        """Handle number highlighting toggle."""
        if checked:
            # Update dropdown to Number
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(3)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(3)
        else:
            # Update dropdown to None
            self.highlighting_combo.blockSignals(True)  # noqa: FBT003
            self.highlighting_combo.setCurrentIndex(0)
            self.highlighting_combo.blockSignals(False)  # noqa: FBT003
            self._on_highlighting_changed(0)

    def _apply_pos_highlighting(self) -> None:
        """
        Apply colors based on parts of speech.

        Only highlights POS tags that are in the :attr:`_selected_pos` set.
        """
        self._clear_all_highlights()
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        extra_selections = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue

            pos = annotation.pos
            # Only highlight if POS is in selected POS tags
            if pos in self._selected_pos:
                color = self.POS_COLORS.get(pos, self.POS_COLORS[None])
                if color != self.POS_COLORS[None]:  # Only highlight if not default
                    selection = self._create_token_selection(token, color)
                    if selection:
                        extra_selections.append(selection)

        self.oe_text_edit.setExtraSelections(extra_selections)

    def _apply_case_highlighting(self) -> None:
        """
        Apply colors based on case values.

        Highlights articles, nouns, pronouns, adjectives, and prepositions.
        Only highlights cases that are in the :attr:`_selected_cases` set.
        """
        self._clear_all_highlights()
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        extra_selections = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue

            pos = annotation.pos
            # Only highlight articles (D), nouns (N), pronouns (R),
            # adjectives (A), and prepositions (E)
            if pos not in ["D", "N", "R", "A", "E"]:
                continue

            # For prepositions, use prep_case; for others, use case
            case_value = annotation.prep_case if pos == "E" else annotation.case
            # Only highlight if case is in selected cases and not default
            if case_value in self._selected_cases:
                color = self.CASE_COLORS.get(case_value, self.CASE_COLORS[None])
                # Only highlight if not default
                if color != self.CASE_COLORS[None]:
                    selection = self._create_token_selection(token, color)
                    if selection:
                        extra_selections.append(selection)

        self.oe_text_edit.setExtraSelections(extra_selections)

    def _apply_number_highlighting(self) -> None:
        """
        Apply colors based on number values.

        Highlights articles, nouns, pronouns, and adjectives.
        """
        self._clear_all_highlights()
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        extra_selections = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue

            pos = annotation.pos
            # Only highlight articles (D), nouns (N), pronouns (R),
            # and adjectives (A)
            if pos not in ["D", "N", "R", "A", "V"]:
                continue

            if pos == "R":
                # Pronouns use pronoun_number, because pronouns can be s, d or pl
                # while everything else is just s or p.
                number_value = annotation.pronoun_number
            else:
                number_value = annotation.number
            color = self.NUMBER_COLORS.get(number_value, self.NUMBER_COLORS[None])
            # Only highlight if not default
            if color != self.NUMBER_COLORS[None]:
                selection = self._create_token_selection(token, color)
                if selection:
                    extra_selections.append(selection)

        self.oe_text_edit.setExtraSelections(extra_selections)

    def _create_token_selection(
        self, token: Token, color: QColor
    ) -> QTextEdit.ExtraSelection | None:
        """
        Create an extra selection for highlighting a token's surface text.

        Args:
            token: Token to highlight
            text: The full sentence text (ignored)
            color: Color to use for highlighting

        Returns:
            ExtraSelection object or None if token not found

        """
        if token.id not in self._token_positions:
            return None

        token_start, token_end = self._token_positions[token.id]

        # Create cursor and highlight the text
        cursor = QTextCursor(self.oe_text_edit.document())
        cursor.setPosition(token_start)
        cursor.setPosition(token_end, QTextCursor.MoveMode.KeepAnchor)

        # Apply highlight format
        char_format = QTextCharFormat()
        char_format.setBackground(color)

        # Create extra selection
        extra_selection = QTextEdit.ExtraSelection()
        extra_selection.cursor = cursor  # type: ignore[attr-defined]
        extra_selection.format = char_format  # type: ignore[attr-defined]

        return extra_selection

    def _clear_all_highlights(self) -> None:
        """Clear all highlighting from the text."""
        self.oe_text_edit.setExtraSelections([])

    def _clear_highlight(self) -> None:
        """
        Clear the temporary selection highlight (yellow/pink) while preserving
        highlighting mode highlights if active.
        """
        # Get existing selections and filter out the selection highlight
        # We identify it by checking for our special property in the format
        existing_selections = self.oe_text_edit.extraSelections()
        filtered_selections = []

        for selection in existing_selections:
            if selection.format.property(self.SELECTION_HIGHLIGHT_PROPERTY):  # type: ignore[attr-defined]
                # This is a selection highlight, skip it
                continue
            # Keep other highlights (e.g. POS mode)
            filtered_selections.append(selection)

        self.oe_text_edit.setExtraSelections(filtered_selections)
        self._current_highlight_start = None
        self._current_highlight_length = None

    def _highlight_token_in_text(self, token: Token) -> None:
        """
        Highlight the corresponding token in the oe_text_edit.

        Args:
            token: Token to highlight

        """
        # Clear any existing selection highlight first
        self._clear_highlight()

        if token.id not in self._token_positions:
            return

        highlight_pos, highlight_end = self._token_positions[token.id]

        # Get existing extra selections (for highlighting mode)
        existing_selections = self.oe_text_edit.extraSelections()

        # Create cursor and highlight the text using extraSelections
        cursor = QTextCursor(self.oe_text_edit.document())
        cursor.setPosition(highlight_pos)
        cursor.setPosition(highlight_end, QTextCursor.MoveMode.KeepAnchor)

        # Apply highlight format for selection (yellow, semi-transparent)
        char_format = QTextCharFormat()
        # Use a yellow background color with transparency
        char_format.setBackground(QColor(200, 200, 0, 150))
        # Mark as selection highlight
        char_format.setProperty(self.SELECTION_HIGHLIGHT_PROPERTY, True)  # noqa: FBT003

        # Use extraSelections for temporary highlighting
        selection_highlight = QTextEdit.ExtraSelection()
        selection_highlight.cursor = cursor  # type: ignore[attr-defined]
        selection_highlight.format = char_format  # type: ignore[attr-defined]

        # Combine existing selections (from highlighting mode)
        # with the selection highlight
        all_selections = [*existing_selections, selection_highlight]
        self.oe_text_edit.setExtraSelections(all_selections)

        # Store position for reference
        self._current_highlight_start = highlight_pos
        self._current_highlight_length = highlight_end - highlight_pos

    def _highlight_token_range(
        self, start_order: int, end_order: int, color: QColor | None = None
    ) -> None:
        """
        Highlight a range of tokens in the oe_text_edit.

        Args:
            start_order: Starting token order_index (inclusive)
            end_order: Ending token order_index (inclusive)
            color: Optional background color for highlight. Defaults to yellow.

        """
        # Clear any existing selection highlight first
        self._clear_highlight()

        if not self.tokens:
            return

        if color is None:
            # Default yellow with semi-transparency
            color = QColor(200, 200, 0, 150)

        # Get existing extra selections (for highlighting mode)
        existing_selections = self.oe_text_edit.extraSelections()

        # Build list of token positions
        token_positions: list[tuple[int, int]] = []  # (start_pos, end_pos)
        for order_idx in range(start_order, end_order + 1):
            token = self.tokens_by_index.get(order_idx)
            if token and token.id in self._token_positions:
                token_positions.append(self._token_positions[token.id])

        if not token_positions:
            return

        # Create highlights for all tokens in range
        range_highlights = []
        for token_start, token_end in token_positions:
            cursor = QTextCursor(self.oe_text_edit.document())
            cursor.setPosition(token_start)
            cursor.setPosition(token_end, QTextCursor.MoveMode.KeepAnchor)

            # Apply highlight format for selection
            char_format = QTextCharFormat()
            char_format.setBackground(color)
            # Mark as selection highlight
            char_format.setProperty(self.SELECTION_HIGHLIGHT_PROPERTY, True)  # noqa: FBT003

            selection_highlight = QTextEdit.ExtraSelection()
            selection_highlight.cursor = cursor  # type: ignore[attr-defined]
            selection_highlight.format = char_format  # type: ignore[attr-defined]
            range_highlights.append(selection_highlight)

        # Combine existing selections with range highlights
        all_selections = [*existing_selections, *range_highlights]
        self.oe_text_edit.setExtraSelections(all_selections)

        # Store range for clearing later
        if token_positions:
            first_start = token_positions[0][0]
            last_end = token_positions[-1][1]
            self._current_highlight_start = first_start
            self._current_highlight_length = last_end - first_start

    def _save_annotation(self, annotation: Annotation) -> None:
        """
        Save annotation to database.

        Args:
            annotation: Annotation to save

        """
        # Check if annotation exists for this token or idiom
        existing = None
        if annotation.token_id:
            existing = Annotation.get_by_token(annotation.token_id)
        elif annotation.idiom_id:
            existing = Annotation.get_by_idiom(annotation.idiom_id)

        if existing:
            self._update_existing_annotation(existing, annotation)
        else:
            # Insert new annotation
            annotation.save()

    def _update_existing_annotation(
        self, existing: Annotation, new_data: Annotation
    ) -> None:
        """Update existing annotation with data from new_data."""
        existing.pos = new_data.pos
        existing.gender = new_data.gender
        existing.number = new_data.number
        existing.case = new_data.case
        existing.declension = new_data.declension
        existing.pronoun_type = new_data.pronoun_type
        existing.pronoun_number = new_data.pronoun_number
        existing.verb_class = new_data.verb_class
        existing.verb_tense = new_data.verb_tense
        existing.verb_person = new_data.verb_person
        existing.verb_mood = new_data.verb_mood
        existing.verb_aspect = new_data.verb_aspect
        existing.verb_form = new_data.verb_form
        existing.prep_case = new_data.prep_case
        existing.adverb_degree = new_data.adverb_degree
        existing.adjective_inflection = new_data.adjective_inflection
        existing.adjective_degree = new_data.adjective_degree
        existing.conjunction_type = new_data.conjunction_type
        existing.confidence = new_data.confidence
        existing.modern_english_meaning = new_data.modern_english_meaning
        existing.root = new_data.root
        existing.save()

    def _on_add_note_clicked(self) -> None:
        """
        Handle Add Note button click - open note dialog.

        """
        if not self.sentence.id:
            return

        # Determine token range (order indices)
        if self._selected_token_range:
            start_order, end_order = self._selected_token_range
        elif self.selected_token_index is not None:
            start_order = self.selected_token_index
            end_order = self.selected_token_index
        else:
            return

        # Get tokens
        start_token = self.tokens_by_index.get(start_order)
        end_token = self.tokens_by_index.get(end_order)

        if not start_token or not end_token or not start_token.id or not end_token.id:
            return

        # Open dialog for creating new note
        dialog = NoteDialog(
            sentence=self.sentence,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
            parent=self,
        )
        dialog.note_saved.connect(self._on_note_saved)
        dialog.exec()

    def _on_note_saved(self, note_id: int) -> None:  # noqa: ARG002
        """
        Handle note saved signal - refresh display.

        This refreshes the notes display and re-renders the OE text with
        superscripts. Note numbers are computed dynamically based on creation
        time order, so remaining notes will be automatically renumbered after
        a deletion.

        Args:
            note_id: ID of saved/deleted note (may be deleted note ID)

        """
        self.session.refresh(self.sentence)
        # Refresh notes display (will renumber notes dynamically)
        self._update_notes_display()
        # Re-render OE text with updated note numbers in superscripts
        self._render_oe_text_with_superscripts()

    def _update_notes_display(self) -> None:
        """Update notes panel display."""
        if hasattr(self, "notes_panel"):
            # Ensure notes relationship is loaded
            if self.sentence.id:
                self.session.refresh(self.sentence, ["notes"])
            self.notes_panel.update_notes(self.sentence)

    def _on_note_clicked(self, note: Note) -> None:
        """
        Handle note clicked - highlight associated tokens.

        Args:
            note: Note that was clicked

        """
        # Clear any active idiom or single token selection
        self.selected_token_index = None
        self._selected_token_range = None
        self._clear_highlight()
        self.add_note_button.setEnabled(False)

        self._highlight_note_tokens(note)

    def _on_note_double_clicked(self, note: Note) -> None:
        """
        Handle note double-clicked - open edit dialog.

        Args:
            note: Note that was double-clicked

        """
        if not note.start_token or not note.end_token:
            return

        # Open dialog for editing note
        dialog = NoteDialog(
            sentence=self.sentence,
            start_token_id=note.start_token,
            end_token_id=note.end_token,
            note=note,
            parent=self,
        )
        dialog.note_saved.connect(self._on_note_saved)
        dialog.exec()

    def _highlight_note_tokens(self, note: Note) -> None:
        """
        Highlight tokens associated with a note.

        Args:
            note: Note to highlight tokens for

        """
        if (
            not self.sentence
            or not self.sentence.tokens
            or not note.start_token
            or not note.end_token
        ):
            return

        # Find token order indices
        start_order = None
        end_order = None
        for token in self.tokens:
            if token.id == note.start_token:
                start_order = token.order_index
            if token.id == note.end_token:
                end_order = token.order_index

        if start_order is not None and end_order is not None:
            self._highlight_token_range(start_order, end_order)

    def _render_oe_text_with_superscripts(self) -> None:
        """
        Render OE text with note superscripts and idiom italics.

        This is the method we use to render the OE text with note superscripts
        and idiom italics, for reading.  We use a different method to render it
        for editing.

        Only renders superscripts when NOT in edit mode.
        """
        if self._oe_edit_mode or not self.sentence:
            return

        # Ensure relationships are loaded
        try:
            if self.sentence.id:
                self.session.refresh(self.sentence, ["notes", "idioms", "tokens"])
        except Exception:  # noqa: BLE001
            return

        self._token_positions.clear()
        self.oe_text_edit.clear()
        cursor = QTextCursor(self.oe_text_edit.document())

        tokens, token_id_to_start = self.sentence.sorted_tokens
        token_to_notes = self.sentence.token_to_note_map
        idiom_token_ids = self._get_idiom_token_ids()

        last_pos = 0
        text = self.sentence.text_oe
        for token in tokens:
            token_id = cast("int", token.id)
            token_start = token_id_to_start[token_id]
            token_end = token_start + len(token.surface)

            if token_start < last_pos:
                continue

            # Insert text before token
            if token_start > last_pos:
                cursor.insertText(text[last_pos:token_start], QTextCharFormat())

            # Render token
            self._render_single_token(
                cursor, token, token_start, token_end, idiom_token_ids, token_to_notes
            )
            last_pos = token_end

        # Insert remaining text
        if last_pos < len(text):
            cursor.insertText(text[last_pos:], QTextCharFormat())

        # Restore highlight if a token was selected
        if self.selected_token_index is not None:
            token = cast("Token", self.tokens_by_index.get(self.selected_token_index))
            if token:
                self._highlight_token_in_text(token)

    def _get_idiom_token_ids(self) -> set[int]:
        """
        Get set of token IDs that are part of an idiom.

        Returns:
            Set of token IDs that are part of an idiom

        """
        idiom_token_ids = set()
        for idiom in self.idioms:
            # We need to find all tokens between start and end
            start_token = idiom.start_token
            end_token = idiom.end_token
            if not start_token or not end_token:
                continue

            # Find tokens in this range by order_index
            start_order = start_token.order_index
            end_order = end_token.order_index
            for token in self.tokens:
                if start_order <= token.order_index <= end_order:
                    idiom_token_ids.add(cast("int", token.id))
        return idiom_token_ids

    def _render_single_token(  # noqa: PLR0913
        self,
        cursor: QTextCursor,
        token: Token,
        token_start: int,
        token_end: int,
        idiom_token_ids: set[int],
        token_to_notes: dict[int, list[int]],
    ) -> None:
        """
        Render a single token with its formatting and superscripts.

        Args:
            cursor: QTextCursor to render the token in
            token: Token to render
            token_start: Start position of the token in the text
            token_end: End position of the token in the text
            idiom_token_ids: Set of token IDs that are part of an idiom
            token_to_notes: Dictionary of token IDs to list of note IDs

        """
        token_id = cast("int", token.id)
        text = self.sentence.text_oe

        # Token format (italics if in idiom)
        token_format = QTextCharFormat()
        token_format.setProperty(self.TOKEN_INDEX_PROPERTY, token.order_index)
        if token_id in idiom_token_ids:
            token_format.setFontItalic(True)

        # Insert token text
        editor_token_start = cursor.position()
        cursor.insertText(text[token_start:token_end], token_format)
        self._token_positions[token_id] = (editor_token_start, cursor.position())

        # Insert superscripts
        if token_id in token_to_notes:
            self._render_superscripts(cursor, token_to_notes[token_id])

    def _render_superscripts(
        self, cursor: QTextCursor, note_numbers: list[int]
    ) -> None:
        """
        Render note superscripts.

        Args:
            cursor: QTextCursor to render the superscripts in
            note_numbers: List of note numbers to render

        """
        super_format = QTextCharFormat()
        super_format.setVerticalAlignment(
            QTextCharFormat.VerticalAlignment.AlignSuperScript
        )
        font = super_format.font()
        # font.setPointSize(int(font.pointSize())) # Keep same size or slightly smaller?
        # Original code had: font.setPointSize(int(font.pointSize())) which is redundant
        # but I'll keep it if it helps clarity
        super_format.setFont(font)
        cursor.insertText(",".join(map(str, note_numbers)), super_format)

    def _escape_html(self, text: str) -> str:
        """
        Escape HTML special characters.

        Args:
            text: Text to escape

        Returns:
            Escaped text

        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )

    def _on_merge_clicked(self) -> None:
        """
        Handle merge button click.

        - Queries for next sentence
        - Shows confirmation dialog
        - Executes merge command if confirmed
        - Emits signal to refresh UI
        """
        if not self.sentence.id:
            return

        next_sentence = Sentence.get_next_sentence(
            self.sentence.project_id, self.sentence.display_order + 1
        )
        if next_sentence is None:
            QMessageBox.warning(
                self,
                "No Next Sentence",
                "There is no next sentence to merge with.",
            )
            return

        # Show confirmation dialog
        message = (
            f"Merge sentence {self.sentence.display_order} "
            f"with sentence {next_sentence.display_order}?\n\n"
            f"This will combine the Old English text, Modern English translation, "
            f"tokens, annotations, and notes from both sentences."
        )
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Merge",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        # Set custom icon
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        reply = msg_box.exec()

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Create and execute merge command
        if not self.command_manager:
            QMessageBox.warning(
                self,
                "Error",
                "Command manager not available. Cannot perform merge.",
            )
            return

        # Store before state
        before_text_oe = self.sentence.text_oe
        before_text_modern = self.sentence.text_modern

        command = MergeSentenceCommand(
            current_sentence_id=self.sentence.id,
            next_sentence_id=next_sentence.id,
            before_text_oe=before_text_oe,
            before_text_modern=before_text_modern,
        )

        if self.command_manager.execute(command):
            # Emit signal to refresh UI
            if self.sentence.id:
                self.sentence_merged.emit(self.sentence.id)
        else:
            QMessageBox.warning(
                self,
                "Merge Failed",
                "Failed to merge sentences. Please try again.",
            )

    def _on_add_sentence_before_clicked(self) -> None:
        """
        Handle "Add Sentence: Before" button click.

        Creates a new empty sentence before the current sentence.
        """
        if not self.sentence.id or not self.command_manager:
            return

        command = AddSentenceCommand(
            project_id=self.sentence.project_id,
            reference_sentence_id=self.sentence.id,
            position="before",
        )

        if self.command_manager.execute(command):
            if command.new_sentence_id:
                self.sentence_added.emit(command.new_sentence_id)
        else:
            QMessageBox.warning(
                self,
                "Add Sentence Failed",
                "Failed to add sentence. Please try again.",
            )

    def _on_add_sentence_after_clicked(self) -> None:
        """
        Handle "Add Sentence: After" button click.

        Creates a new empty sentence after the current sentence.
        """
        if not self.sentence.id or not self.command_manager:
            return

        command = AddSentenceCommand(
            project_id=self.sentence.project_id,
            reference_sentence_id=self.sentence.id,
            position="after",
        )

        if self.command_manager.execute(command):
            if command.new_sentence_id:
                self.sentence_added.emit(command.new_sentence_id)
        else:
            QMessageBox.warning(
                self,
                "Add Sentence Failed",
                "Failed to add sentence. Please try again.",
            )

    def _on_toggle_paragraph_clicked(self) -> None:
        """
        Handle Toggle Paragraph Start button click.

        Toggles the is_paragraph_start flag and recalculates paragraph numbers.
        """
        if not self.sentence.id or not self.command_manager:
            return

        # Create and execute toggle command
        command = ToggleParagraphStartCommand(
            sentence_id=self.sentence.id,
        )

        if self.command_manager.execute(command):
            # Refresh sentence from database
            self.session.refresh(self.sentence)
            # Update UI
            self._update_paragraph_button_state()
            paragraph_num = self.sentence.paragraph_number
            sentence_num = self.sentence.sentence_number_in_paragraph
            self.sentence_number_label.setText(f"¶.{paragraph_num} S.{sentence_num}")
            # Emit signal to refresh all cards (paragraph numbers may have changed)
            # We'll use sentence_added signal as a refresh trigger
            if self.sentence.id:
                self.sentence_added.emit(self.sentence.id)
        else:
            QMessageBox.warning(
                self,
                "Toggle Failed",
                "Failed to toggle paragraph start. Please try again.",
            )

    def _update_paragraph_button_state(self) -> None:
        """
        Update the toggle paragraph button text and visibility based on current state.
        """
        # Hide button for first sentence (must always be paragraph start)
        if self.sentence.display_order == 1:
            self.toggle_paragraph_button.setVisible(False)
        else:
            self.toggle_paragraph_button.setVisible(True)
            if self.sentence.is_paragraph_start:
                self.toggle_paragraph_button.setText("Remove Paragraph Start")
            else:
                self.toggle_paragraph_button.setText("Mark as Paragraph Start")

    def _on_delete_clicked(self) -> None:
        """
        Handle Delete button click.

        Shows confirmation dialog and deletes the sentence if confirmed.
        """
        if not self.sentence.id or not self.command_manager:
            return

        # Show confirmation dialog
        message = (
            f"Delete sentence {self.sentence.display_order}?\n\n"
            f"This will permanently delete the sentence, including its "
            f"Old English text, Modern English translation, tokens, "
            f"annotations, and notes. This action can be undone."
        )
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Delete",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self,
        )
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        # Set custom icon
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        reply = msg_box.exec()

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Create and execute delete command
        command = DeleteSentenceCommand(
            sentence_id=self.sentence.id,
        )

        if self.command_manager.execute(command):
            # Emit signal to refresh UI
            if self.sentence.id:
                self.sentence_deleted.emit(self.sentence.id)
        else:
            QMessageBox.warning(
                self,
                "Delete Failed",
                "Failed to delete sentence. Please try again.",
            )

    def get_oe_text(self) -> str:
        """
        Get Old English text.

        Returns:
            Old English text string

        """
        return self.oe_text_edit.toPlainText()

    def get_translation(self) -> str:
        """
        Get Modern English translation.

        Returns:
            Translation text string

        """
        return self.translation_edit.toPlainText()

    def update_sentence(self, sentence: Sentence) -> None:
        """
        Update sentence data.

        Args:
            sentence: Updated sentence model

        """
        self.sentence = sentence
        paragraph_num = sentence.paragraph_number
        sentence_num = sentence.sentence_number_in_paragraph
        self.sentence_number_label.setText(
            f"[{sentence.display_order}] ¶:{paragraph_num} S:{sentence_num}"
        )
        self._update_paragraph_button_state()
        # If we're in edit mode, exit it first
        if self._oe_edit_mode:
            # Restore read-only state
            self.oe_text_edit.setReadOnly(True)
            # Hide Save/Cancel buttons
            self.save_oe_button.setVisible(False)
            self.cancel_edit_button.setVisible(False)
            # Show Edit OE button and Add Note button
            self.edit_oe_button.setVisible(True)
            self.add_note_button.setVisible(True)
            # Reconnect textChanged signal if it was disconnected
            with suppress(RuntimeError):
                self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)
            # Reset edit mode state
            self._oe_edit_mode = False
            self._original_oe_text = None
        self.oe_text_edit.setText(sentence.text_oe)
        self.translation_edit.setPlainText(sentence.text_modern or "")

    def focus(self) -> None:
        """
        Focus this sentence card.
        """
        self.token_table.table.setFocus()
        self.token_table.select_token(0)

    def focus_translation(self) -> None:
        """
        Focus translation field.
        """
        self.translation_edit.setFocus()

    def unfocus(self) -> None:
        """
        Unfocus this sentence card.
        """
        self.token_table.table.clearFocus()
        self.token_table.select_token(0)

    def _perform_deselection(self) -> None:
        """
        Perform deselection if still pending. Called by timer after delay.

        This means:

        - Deselect the token if the selected token index still matches
        - Clear the selected token range if it exists and the click was inside it
        - Clear the highlight
        - Disable the add note button
        - Emit signal to clear sidebar (main window will handle it)
        """
        if self._pending_deselect_token_index is not None:
            order_index = self._pending_deselect_token_index
            # Only deselect if the token index still matches or click was in range
            # Case 1: Single token selection matches
            if self.selected_token_index == order_index:
                self.selected_token_index = None
                self._selected_token_range = None
                self._clear_highlight()
                self.add_note_button.setEnabled(False)
                # Emit signal to clear sidebar
                token = self.tokens_by_index.get(order_index)
                if token:
                    self.token_selected_for_details.emit(token, self.sentence, self)

            # Case 2: Range selection exists and click was inside it
            elif self._selected_token_range:
                start, end = self._selected_token_range
                if start <= order_index <= end:
                    self._selected_token_range = None
                    self.selected_token_index = None
                    self._clear_highlight()
                    self.add_note_button.setEnabled(False)
                    # Emit signal to clear sidebar
                    token = self.tokens_by_index.get(order_index)
                    if token:
                        self.token_selected_for_details.emit(token, self.sentence, self)

            self._pending_deselect_token_index = None

    def _clear_token_selection(self) -> None:
        """
        Clear token selection and highlight.

        This means:

        - Cancel any pending deselection timer
        - Clear the selected token index
        - Clear the selected token range
        - Clear the highlight
        - Disable the add note button
        - Emit signal to clear sidebar (main window will handle it)
        """
        # Cancel any pending deselection timer
        if self._deselect_timer.isActive():
            self._deselect_timer.stop()
        self._pending_deselect_token_index = None
        self.selected_token_index = None
        self._selected_token_range = None
        self._clear_highlight()
        self.add_note_button.setEnabled(False)
        # Emit signal with None to clear sidebar (main window will handle it)
        # We'll emit with the sentence but no token to indicate clearing
        # Actually, let's emit a special signal or the main window can check
        # selected_token_index For now, the main window will check if
        # selected_token_index is None

    def _toggle_token_table(self) -> None:
        """Toggle token table visibility."""
        is_visible = self.token_table.isVisible()
        self.token_table.setVisible(not is_visible)
        self.token_table_toggle_button.setText(
            "Hide Token Table" if not is_visible else "Show Token Table"
        )

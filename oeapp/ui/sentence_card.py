"""Sentence card UI component."""

from contextlib import suppress
from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtCore import QPoint, QTimer, Signal
from PySide6.QtGui import (
    QFont,
    QKeyEvent,
    QKeySequence,
    Qt,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
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
    NoteDialog,
)
from oeapp.ui.highlighting import SingleInstanceHighligher, WholeSentenceHighligher
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.ui.notes_panel import NotesPanel
from oeapp.ui.token_table import TokenTable
from oeapp.ui.widgets import OldEnglishTextEdit
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
    from oeapp.models.note import Note
    from oeapp.models.token import Token
    from oeapp.ui.main_window import MainWindow


class SentenceCard(AnnotationLookupsMixin, TokenOccurrenceMixin, SessionMixin, QWidget):
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
        self.sentence_highlighter: WholeSentenceHighligher = WholeSentenceHighligher(
            self
        )
        self.build()
        # This has to happen after build() because it needs to access the OE text edit
        self.span_highlighter: SingleInstanceHighligher = SingleInstanceHighligher(self)

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
        self.span_highlighter.highlight(token.order_index)
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
        self.span_highlighter.highlight(token.order_index)
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

    def build_sentence_actions(self) -> QHBoxLayout:
        """
        Add the sentence actions (menus and buttons) to the layout and return
        the layout.

        - Add Sentence Button with menu for adding a sentence before or after
        - Toggle Paragraph Start button with menu for toggling the paragraph start
        - Merge with next button
        - Delete button

        Returns:
            Layout with the sentence actions (menus and buttons)

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
            - Idioms

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
        highlighter = cast("WholeSentenceHighligher", self.sentence_highlighter)
        self.highlighting_combo = highlighter.build_combo_box()
        layout.addWidget(self.highlighting_combo)

        return layout

    def build_oe_text_edit(self) -> OldEnglishTextEdit:
        """
        Build the OE text edit widget.

        Returns:
            OE text edit widget

        """
        oe_text_edit = OldEnglishTextEdit()
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
        Build the notes panel widget.  This is the panel below the translation edit
        that shows the notes for the sentence.

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
        - Sentence actions (menus and buttons):

            - Add Sentence Button with menu for adding a sentence before or after
            - Toggle Paragraph Start button with menu for toggling the paragraph start
            - Merge with next button
            - Delete button

        - The label for the Old English text edit, and related buttons and
          highlighting options:

            - Old English: label
            - Add Note button: button to add a note to the sentence
            - Edit OE button: button to edit the Old English text
            - Save OE button: button to save the Old English text
            - Cancel Edit button: button to cancel the edit of the Old English text
            - Dropdown for highlighting options: Part of Speech, Case, Number, Idioms

        - Old English text edit itself
        - Token annotation grid (hidden by default)
        - Modern English translation edit with toggle button for token table
        - Notes panel

        Returns:
            Sentence card widget

        """
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Add paragraph header: [Display Order] ¶:Paragraph Number S:Sentence Number
        layout.addWidget(self.build_paragraph_header())
        # Action buttons
        layout.addLayout(self.build_sentence_actions())
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
        cast("WholeSentenceHighligher", self.sentence_highlighter).highlight()

    def reset_selected_token(self) -> None:
        """
        - Clear the selected token index
        - Show the empty state in the sidebar
        - Clear the highlight
        - Disable the add note button
        """
        if self.main_window is not None:
            self.main_window.token_details_sidebar.show_empty()
        self.selected_token_index = None
        self.span_highlighter.unhighlight()
        self.add_note_button.setEnabled(False)

    def _open_annotation_modal(self) -> None:
        """
        Open annotation modal for selected token or idiom.

        This is a bit complicated because we need to handle both single token
        and idiom selections. And we need to handle both existing idioms and new
        idioms.

        Processing order:

        1. If the selection is a token range:

            a. If a token range is selected, and that range matches an existing idiom,
               we need to open the idiom annotation modal with the existing
               idiom annotation.
            b. If a token range is selected, and that range does not match an
               existing idiom, we need to open the idiom modal and create the new
               idiom and annotation on apply.

        2. If the selection is a single token:

            a. If a single token is selected that is not part of an idiom, we
               need to open the token annotation modal.  All individual tokens
               always have an annotation, so we can just open the token
               annotation modal and save the annotation on apply.
            b. If a single token is selected that is part of an idiom, we need to
               open the idiom annotation modal.  This can happen if the user is
               using arrow keys to navigate through the text.

        4. Open normal token modal: if no idiom or token is selected, we need to
           is selected that is part of an idiom, we need to open the idiom modal.  This
           can happen if the user is using arrow keys to navigate through the text.

        """
        # 1. If the selection is a token range:
        if self._selected_token_range:
            start_order, end_order = self._selected_token_range
            idiom = self._find_matching_idiom(start_order, end_order)
            if idiom:
                # Open the idiom annotation modal with the existing idiom annotation
                self._open_idiom_modal(idiom)
                return

            # Open the idiom modal and create the new idiom and annotation on apply
            self._open_new_idiom_modal(start_order, end_order)
            return

        # 2. If the selection is a single token:
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
        """
        Find an idiom that exactly matches the given range of tokens.

        Args:
            start_order: Start token order index
            end_order: End token order index

        Returns:
            Idiom that exactly matches the given range of tokens

        """
        for idiom in self.idioms:
            if (
                idiom.start_token.order_index == start_order
                and idiom.end_token.order_index == end_order
            ):
                return idiom
        return None

    def _open_idiom_modal(self, idiom: Idiom) -> None:
        """
        Open annotation modal for an existing idiom.

        Args:
            idiom: Idiom to open the annotation modal for

        """
        annotation = idiom.annotation
        if annotation is None:
            annotation = Annotation(idiom_id=idiom.id)

        # We'll need to update AnnotationModal to take a list of tokens or an Idiom
        modal = AnnotationModal(idiom=idiom, annotation=annotation, parent=self)
        modal.annotation_applied.connect(self._on_annotation_applied)
        modal.exec()

    def _open_new_idiom_modal(self, start_order: int, end_order: int) -> None:
        """
        Open annotation modal for a new idiom.

        Args:
            start_order: Start token order index
            end_order: End token order index

        """
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
        """
        Open annotation modal for a single token.

        Args:
            token: Token to open the annotation modal for

        """
        annotation = token.annotation
        if annotation is None and token.id:
            annotation = Annotation.get_by_token(token.id)

        modal = AnnotationModal(token=token, annotation=annotation, parent=self)
        modal.annotation_applied.connect(self._on_annotation_applied)
        modal.exec()

    def _on_idiom_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied for a new idiom (needs creation).

        Args:
            annotation: Annotation applied for the new idiom

        """
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
        """
        Handle annotation applied signal.

        Args:
            annotation: Annotation applied

        """
        before_state = self._get_annotation_state(annotation)
        after_state = self._extract_annotation_state(annotation)

        if self.command_manager:
            self._execute_annotate_command(annotation, before_state, after_state)
        else:
            self._save_annotation(annotation)

        self._finalize_annotation_update(annotation)

    def _get_annotation_state(self, annotation: Annotation) -> dict:
        """
        Get the current state of an annotation before updates.

        Args:
            annotation: Annotation to get the state of

        Returns:
            State of the annotation

        """
        token_id = annotation.token_id
        idiom_id = annotation.idiom_id

        existing = None
        if token_id:
            existing = self.annotations.get(token_id)
        elif idiom_id:
            existing = Annotation.get_by_idiom(idiom_id)

        return self._extract_annotation_state(existing) if existing else {}

    def _extract_annotation_state(self, annotation: Annotation) -> dict:
        """
        Extract morphological state from an annotation object.

        Args:
            annotation: Annotation to extract the state from

        Returns:
            State of the annotation

        """
        # TODO: can't we just use annotation.to_json() here?
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
        """
        Execute the annotate command via command manager.  This will handle the
        actual save or update of the annotation and also handle the undo/redo
        operations.

        Args:
            annotation: Annotation to execute the command for
            before: Before state of the annotation
            after: After state of the annotation

        """
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
        """
        Update local caches and UI after annotation is applied.

        Args:
            annotation: Annotation that was applied

        """
        if annotation.token_id:
            self.annotations[annotation.token_id] = annotation
            self.token_table.update_annotation(annotation)

        self.annotation_applied.emit(annotation)
        self.sentence_highlighter.highlight()

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
        self.span_highlighter.highlight(token.order_index)
        self.token_selected_for_details.emit(token, self.sentence, self)

    def _on_oe_text_clicked(
        self, position: QPoint, modifiers: Qt.KeyboardModifier
    ) -> None:
        """
        Handle click on Old English text to select corresponding token.

        Args:
            position: Position of the click in the Old English text edit
            modifiers: Modifiers pressed (Ctrl, Shift, etc.)

        """
        # If in edit mode, don't handle clicks for selection
        if self._oe_edit_mode:
            return

        # Get the cursor position from the click position
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
        """
        Handle Cmd/Ctrl+Click for idiom selection.  This will start a new idiom
        selection or extend the existing idiom selection.

        Args:
            order_index: Order index of the token that was clicked

        """
        # Un-highlight and deselect any currently selected or highlighted tokens
        # if we are starting a new idiom selection or if it's already selected
        # Check if we are starting a new idiom selection
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
            self.reset_selected_token()

        self.span_highlighter.highlight(
            self._selected_token_range[0],
            self._selected_token_range[1],
            color_name="idiom",
        )
        self.add_note_button.setEnabled(False)

    def _handle_range_selection_click(self, order_index: int) -> None:
        """
        Handle Shift+Click for range selection for Note creation and management.
        This will start a new range selection or extend the existing range
        selection.

        Args:
            order_index: Order index of the token that was clicked

        """
        # Clear any active idiom selection/highlight
        self._selected_token_range = None
        self.span_highlighter.unhighlight()

        if self.selected_token_index is not None:
            start_order = min(self.selected_token_index, order_index)
            end_order = max(self.selected_token_index, order_index)
            self._selected_token_range = (start_order, end_order)
            self.reset_selected_token()
            self.span_highlighter.highlight(start_order, end_order)
        else:
            self._handle_single_selection_click(order_index)

        self.add_note_button.setEnabled(True)

    def _handle_single_selection_click(self, order_index: int) -> None:
        """
        Handle normal click for single token selection.  This will select a
        single token.

        Processing order:

        1. If click is within existing range selection, don't clear it yet.
           This allows double-click to work on the selection.
        2. Check if clicking a SAVED idiom token.  If so, select the whole idiom.
        3. Standard single token selection

           a. If the clicked token is already selected, start deselection timer
              so double-click can cancel it.
           b. If the clicked token is not selected, select it and highlight it
              in the text.
           c. Emit the token selected signal.
           d. Enable the add note button.

        Args:
            order_index: Order index of the token that was clicked

        """
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
            self.reset_selected_token()
            # Select the whole idiom
            self._selected_token_range = (
                idiom.start_token.order_index,
                idiom.end_token.order_index,
            )
            self.span_highlighter.highlight(
                self._selected_token_range[0],
                self._selected_token_range[1],
                color_name="idiom",
            )
            self.idiom_selected_for_details.emit(idiom, self.sentence, self)
            return

        # 3. Standard single token selection
        if self.selected_token_index == order_index:
            self._pending_deselect_token_index = order_index
            self._deselect_timer.start(300)
        else:
            self.selected_token_index = order_index
            token = self.tokens_by_index.get(order_index)
            if token:
                self.span_highlighter.highlight(token.order_index)
                self.token_selected_for_details.emit(token, self.sentence, self)
                list_index = self.order_to_list_index.get(order_index)
                if list_index is not None:
                    self.token_table.select_token(list_index)
            self.add_note_button.setEnabled(False)

    def _find_idiom_at_order_index(self, order_index: int) -> Idiom | None:
        """
        Find if an idiom covers the given token order index.

        Args:
            order_index: Order index of the token to check

        Returns:
            Idiom that covers the given token order index

        """
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
            position: Mouse double-click position in the Old English text edit
                widget coordinates

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
        """
        Handle Old English text change.

        This will clear the temporary selection highlight and re-apply the
        highlighting mode if active.  This is called when the user saves or
        cancels the edit of the Old English text in the text edit widget.

        """
        # Don't process changes if not in edit mode (shouldn't happen if signal
        # is disconnected)
        if not self._oe_edit_mode:
            return

        # Clear temporary selection highlight when text is edited
        self.span_highlighter.unhighlight()
        # Re-apply highlighting mode if active (though highlights will be
        # cleared when entering edit mode)
        self.sentence_highlighter.highlight()

    def _on_edit_oe_clicked(self) -> None:
        """
        Handle Edit OE button click - enter edit mode.

        This will enter edit mode and clear the temporary selection highlight
        and re-apply the highlighting mode if active.

        What this does:

        1. Set edit mode
        2. Clear any active idiom or single token selection
        3. Save original text (plain text without superscripts) so we can restore it
           if the user cancels the edit.
        4. Set the text edit to the original text (remove superscripts)
        5. Clear all highlighting
        6. Clear token selection highlight
        7. Reset highlighting dropdown to None (index 0)
        8. Hide any open filter dialogs
        9. Hide Edit OE button and Add Note button
        10. Show Save OE and Cancel Edit buttons
        11. Enable editing
        12. Disconnect textChanged signal to prevent auto-tokenization while editing

        """
        # Set edit mode
        self._oe_edit_mode = True
        # Clear any active idiom or single token selection
        self.reset_selected_token()
        self._selected_token_range = None
        # Store original text (plain text without superscripts)
        self._original_oe_text = self.sentence.text_oe
        # Set plain text (remove superscripts)
        self.oe_text_edit.setPlainText(self._original_oe_text)
        # Clear all highlighting
        self.sentence_highlighter.unhighlight()
        # Hide any open filter dialogs
        self.sentence_highlighter.hide_filter_dialog()
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
        """
        Handle Save OE button click - save changes and exit edit mode.

        This will save the changes to the Old English text and exit edit mode.
        What this does:

        1. Exit edit mode
        2. Make read-only again
        3. Hide Save OE and Cancel Edit buttons
        4. Show Edit OE button
        5. Show Add Note button
        6. Reconnect textChanged signal
        7. Get new text from the text edit and save it to the sentence
        8. Re-render the text with Note superscripts and idiom italics
        9. Clear original text saved in this instance
        """
        # Exit edit mode
        self._oe_edit_mode = False
        # Make read-only again
        self.oe_text_edit.setReadOnly(True)
        # Hide Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        # Show Edit OE button
        self.edit_oe_button.setVisible(True)
        # Show Add Note button
        self.add_note_button.setVisible(True)
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
                self.sentence_highlighter.highlight()
                self.sentence_highlighter.show_filter_dialog()

        # Re-render with superscripts
        self._render_oe_text_with_superscripts()
        # Clear original text
        self._original_oe_text = None

    def _on_cancel_edit_clicked(self) -> None:
        """
        Handle "Cancel Edit" button click - discard changes and exit edit mode.

        What this does:

        1. Exit edit mode
        2. Restore original text (plain text without superscripts) to the text edit
        3. Make the text edit read-only again so the user can't edit it
        4. Hide Save OE and Cancel Edit buttons
        5. Show Edit OE button and Add Note button
        6. Reconnect textChanged signal so that the text edit will be auto-tokenized
           once the user is done editing.
        7. Re-render the text with Note superscripts and idiom italics
        8. Clear original text

        """
        # Exit edit mode
        self._oe_edit_mode = False
        # Restore original text
        # TODO: seems like we're doing this twice.  Here and in
        # _render_oe_text_with_superscripts().
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
        """
        Handle translation text change.

        This will save the changes to the Modern English text and exit edit mode.
        What this does:

        1. Get new text from the translation text edit
        2. Get old text from the :class:`~oeapp.models.sentence.Sentence` model
        3. If new text is different from old text, create an
           :class:`~oeapp.commands.sentence.EditSentenceCommand`
        4. Execute the command so that undo/redo operations are available for the
           new text.  If the command is successful, the sentence model will be
           updated with the new text.  If the command is not successful, the new
           text will not be saved.
        """
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
        self.reset_selected_token()
        self._selected_token_range = None
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
            self.span_highlighter.highlight(start_order, end_order)

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
                self.span_highlighter.highlight(token.order_index)

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
                self._selected_token_range = None
                self.reset_selected_token()
                # Emit signal to clear sidebar
                token = self.tokens_by_index.get(order_index)
                if token:
                    self.token_selected_for_details.emit(token, self.sentence, self)

            # Case 2: Range selection exists and click was inside it
            elif self._selected_token_range:
                start, end = self._selected_token_range
                if start <= order_index <= end:
                    self._selected_token_range = None
                    self.reset_selected_token()
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
        """
        # Cancel any pending deselection timer
        if self._deselect_timer.isActive():
            self._deselect_timer.stop()
        self._pending_deselect_token_index = None
        self.reset_selected_token()

    def _toggle_token_table(self) -> None:
        """Toggle token table visibility."""
        is_visible = self.token_table.isVisible()
        self.token_table.setVisible(not is_visible)
        self.token_table_toggle_button.setText(
            "Hide Token Table" if not is_visible else "Show Token Table"
        )

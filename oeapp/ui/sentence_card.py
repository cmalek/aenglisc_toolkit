"""Sentence card UI component."""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import Signal
from PySide6.QtGui import (
    QFont,
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
from oeapp.ui.highlighting import WholeSentenceHighlighter
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.ui.notes_panel import NotesPanel
from oeapp.ui.oe_text_edit import OldEnglishTextEdit
from oeapp.ui.token_table import TokenTable
from oeapp.utils import get_logo_pixmap

if TYPE_CHECKING:
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
        self.sentence_highlighter: WholeSentenceHighlighter = WholeSentenceHighlighter()
        self.build()
        self.set_tokens()
        # We need to do this here because it has to come after
        # :meth:`set_tokens()` is called to set up all the lookups
        # and mappings for the tokens on OldEnglishTextEdit.
        self.sentence_highlighter.sentence_card = self

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

    def clear_token_selection(self) -> None:
        """
        Clear token selection and highlight.

        This means:

        - Cancel any pending deselection timer
        - Clear the selected token index
        - Clear the selected token range
        """
        self.oe_text_edit.reset_selection()

    def set_tokens(self) -> None:
        """
        Set tokens for this sentence card.  This will also load the annotations
        for the tokens.

        Args:
            _tokens: List of tokens (optional, ignored in favor of
                self.sentence.sorted_tokens)

        """
        self.oe_text_edit.set_tokens()
        self.token_table.set_tokens(self.oe_text_edit.tokens)

    def reset_selected_token(self) -> None:
        """
        Disable the add note button when we have deselected tokens.
        """
        self.add_note_button.setEnabled(False)

    def enter_edit_mode(self) -> bool:
        """
        Programmatically enter edit mode and focus the Old English text box.

        Returns:
            True if successful, False otherwise

        """
        if self.oe_text_edit.in_edit_mode:
            # Already in edit mode, just focus
            self.oe_text_edit.setFocus()
            return True

        # Enter edit mode
        self._on_edit_oe_clicked()
        # Set focus on OE text edit
        self.oe_text_edit.setFocus()
        return True

    # -------------------------------------------------------------------------
    # Build methods
    # -------------------------------------------------------------------------

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
        highlighter = cast("WholeSentenceHighlighter", self.sentence_highlighter)
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
        self.set_tokens()
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
        self.oe_text_edit.sentence_card = self
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
        self.notes_panel.update_notes()

        layout.addStretch()

    # ========================================================================
    # Annotation related methods
    # ========================================================================

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
        current_range = self.oe_text_edit.current_range()
        if current_range:
            start_order, end_order = current_range
            idiom = self.oe_text_edit.find_idiom(start_order, end_order)
            if idiom:
                # Open the idiom annotation modal with the existing idiom annotation
                self._open_idiom_modal(idiom)
                return

            # Open the idiom modal and create the new idiom and annotation on apply
            self._open_new_idiom_modal(start_order, end_order)
            return

        # 2. If the selection is a single token:
        token: Token | None = self.token_table.get_selected_token()
        selected_token_index = self.oe_text_edit.current_token_index()
        if not token and selected_token_index is not None:
            token = self.oe_text_edit.get_selected_token()

        if not token:
            # Select first token if none selected
            if self.oe_text_edit.tokens:
                token = self.oe_text_edit.tokens[0]
                self.token_table.select_token(0)
            else:
                return

        # Check if this token is part of an idiom
        idiom = self.oe_text_edit.find_idiom(token.order_index)
        if idiom:
            self._open_idiom_modal(idiom)
            return

        # Open normal token modal
        self._open_token_modal(token)

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
        start_token = self.oe_text_edit.get_token(start_order)
        end_token = self.oe_text_edit.get_token(end_order)
        if not start_token or not end_token:
            return
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
            self.oe_text_edit.annotations[annotation.token_id] = annotation
            self.token_table.update_annotation(annotation)

        self.annotation_applied.emit(annotation)
        self.sentence_highlighter.highlight()

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
            existing.from_annotation(annotation)
        else:
            # Insert new annotation
            annotation.save()

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
            existing = self.oe_text_edit.annotations.get(token_id)
        elif idiom_id:
            existing = Annotation.get_by_idiom(idiom_id)

        return self._extract_annotation_state(existing) if existing else {}

    # -------------------------------------------------------------------------
    # Annotation related event handlers
    # -------------------------------------------------------------------------

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
        self.oe_text_edit.sentence_card = self

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

    # -------------------------------------------------------------------------
    # Note related event handlers
    # -------------------------------------------------------------------------

    def _on_add_note_clicked(self) -> None:
        """
        Handle Add Note button click - open note dialog.

        """
        if not self.sentence.id:
            return

        try:
            selected_tokens = self.oe_text_edit.selected_tokens
        except ValueError:
            return
        if selected_tokens is None:
            return
        start_token, end_token = selected_tokens
        # Open dialog for creating new note
        dialog = NoteDialog(
            sentence=self.sentence,
            start_token_id=start_token.id,
            end_token_id=end_token.id,
            parent=self,
        )
        dialog.note_saved.connect(self.notes_panel._on_note_saved)
        dialog.note_saved.connect(self._on_note_saved)
        dialog.exec()

    def _on_note_saved(self, note_id: int) -> None:  # noqa: ARG002
        """
        Handle note saved signal - re-render OE text.

        :class:`~oeapp.ui.notes_panel.NotesPanel` will re-render the notes display.

        Args:
            note_id: ID of saved/deleted note (may be deleted note ID)

        """
        # Re-render OE text with updated note numbers in superscripts
        self.oe_text_edit.render_readonly_text()

    # ========================================================================
    # Token table related methods
    # ========================================================================

    def _toggle_token_table(self) -> None:
        """Toggle token table visibility."""
        is_visible = self.token_table.isVisible()
        self.token_table.setVisible(not is_visible)
        self.token_table_toggle_button.setText(
            "Hide Token Table" if not is_visible else "Show Token Table"
        )

    # -------------------------------------------------------------------------
    # Token table related event handlers
    # -------------------------------------------------------------------------

    def _on_token_table_token_selected(self, token: Token) -> None:
        """
        Handle token selection from the token table.

        Args:
            token: Selected token

        """
        # Cancel any pending deselection timer
        self.oe_text_edit.set_selected_token_index(token.order_index, emit=False)
        self.token_selected_for_details.emit(token, self.sentence, self)

    # ========================================================================
    # Paragraph related methods
    # ========================================================================

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

    # -------------------------------------------------------------------------
    # Paragraph related event handlers
    # -------------------------------------------------------------------------

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

    # ========================================================================
    # Event handlers
    # ========================================================================

    def _on_idiom_selection(self, start_order: int, end_order: int) -> None:  # noqa: ARG002
        """
        Event handler for idiom selection.

        Args:
            start_order: Start order index of the idiom
            end_order: End order index of the idiom

        """
        self.add_note_button.setEnabled(False)

    def _on_range_selection(self, start_order: int, end_order: int) -> None:  # noqa: ARG002
        """
        Event handler for range selection.

        Args:
            start_order: Start order index of the range
            end_order: End order index of the range

        """
        self.add_note_button.setEnabled(True)

    def _on_token_selection(self, token: Token) -> None:
        """
        Event handler for single token selection.

        Args:
            token: Token that was selected

        """
        self.token_table.select_token(token.order_index)
        self.add_note_button.setEnabled(False)

    # -------------------------------------------------------------------------
    # Edit mode related event handlers
    # -------------------------------------------------------------------------

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
        # Clear all highlighting
        self.sentence_highlighter.unhighlight()
        self.sentence_highlighter.hide_filter_dialog()
        self.sentence_highlighter.clear_active_command()
        # Hide Edit OE button and Add Note button
        self.edit_oe_button.setVisible(False)
        self.add_note_button.setVisible(False)
        # Show Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(True)
        self.cancel_edit_button.setVisible(True)
        # Set edit mode
        self.oe_text_edit.in_edit_mode = True

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
        # Get new text and save
        if not self.command_manager or not self.sentence.id:
            self.oe_text_edit.render_readonly_text()
            return

        new_text = self.oe_text_edit.live_text
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
                self.oe_text_edit.set_tokens()
                # Update notes display
                self.notes_panel.update_notes()

        # Make read-only again
        self.oe_text_edit.in_edit_mode = False
        # Hide Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        # Show Edit OE button
        self.edit_oe_button.setVisible(True)
        # Show Add Note button
        self.add_note_button.setVisible(True)

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
        # Restore original text
        self.oe_text_edit.restore_original_text()
        # Exit edit mode
        self.oe_text_edit.in_edit_mode = False
        # Hide Save OE and Cancel Edit buttons
        self.save_oe_button.setVisible(False)
        self.cancel_edit_button.setVisible(False)
        # Show Edit OE button and Add Note button
        self.edit_oe_button.setVisible(True)
        self.add_note_button.setVisible(True)

    # -------------------------------------------------------------------------
    # Translation text edit related event handlers
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Sentence related event handlers
    # -------------------------------------------------------------------------

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

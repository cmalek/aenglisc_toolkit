"""Sentence card UI component."""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import (
    QSettings,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import (
    QFont,
    QPalette,
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
    AnnotateTokenCommand,
    CommandManager,
)
from oeapp.commands.hierarchy import (
    MergeChapterCommand,
    MergeSectionCommand,
    SplitChapterCommand,
    SplitSectionCommand,
)
from oeapp.commands.paragraph import MergeParagraphCommand, SplitParagraphCommand
from oeapp.mixins import TokenOccurrenceMixin
from oeapp.models import Annotation, Idiom
from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence
from oeapp.ui.dialogs import NoteDialog
from oeapp.ui.highlighting import SearchHighlighter, WholeSentenceHighlighter
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.ui.notes_panel import NotesPanel
from oeapp.ui.oe_text_edit import OldEnglishTextEdit
from oeapp.ui.sentence_card_controller import SentenceCardController
from oeapp.ui.token_table import TokenTable

if TYPE_CHECKING:
    from oeapp.models.token import Token
    from oeapp.ui.main_window import MainWindow

THEME_DARK_LIGHTNESS_THRESHOLD = 128


class SentenceCard(AnnotationLookupsMixin, TokenOccurrenceMixin, SessionMixin, QWidget):
    """
    Widget representing a sentence card with annotations.

    Args:
        sentence: Sentence model instance

    Keyword Args:
        command_manager: Command manager for undo/redo
        main_window: Main window this card belongs to
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
    #: Signal emitted when an annotation is applied
    annotation_applied = Signal(Annotation)
    #: Signal emitted when entering edit mode
    edit_mode_started = Signal()
    #: Signal emitted when exiting edit mode
    edit_mode_finished = Signal()

    def __init__(
        self,
        sentence: Sentence,
        command_manager: CommandManager | None = None,
        main_window: "MainWindow | None" = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        #: The sentence this card represents
        self.sentence = sentence
        #: The session this card belongs to
        self.session = self._get_session()
        #: The command manager for this card
        self.command_manager = command_manager
        #: The main window this card belongs to
        self.main_window = main_window
        #: The token table for this card
        self.token_table = TokenTable()
        #: The sentence highlighter for this card
        self.sentence_highlighter: WholeSentenceHighlighter = WholeSentenceHighlighter()
        #: The base stylesheet for the card
        self._flash_base_stylesheet: str | None = None
        #: The timer for the flash restore after a new sentence is added
        self._flash_restore_timer = QTimer(self)
        self._flash_restore_timer.setSingleShot(True)
        self._flash_restore_timer.timeout.connect(self._clear_added_flash)
        self.setObjectName("sentence-card")
        self.build()
        #: Controller for command execution and annotation modal routing.
        self.controller = SentenceCardController(self)
        self.edit_oe_button.clicked.connect(
            self.sentence_highlighter._on_edit_oe_clicked
        )
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

    def flash_added(self) -> None:
        """
        Briefly flash the card background to indicate a new sentence was added.
        """
        if self._flash_base_stylesheet is None:
            self._flash_base_stylesheet = self.styleSheet()

        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)  # noqa: FBT003
        # get settings from QSettings to see what theme is being used
        settings = QSettings()
        theme = settings.value("theme/name", "nord")
        flash_rule = "QWidget#sentence-card { "
        if theme == "dark":
            flash_rule += "background-color: rgba(140, 160, 206, 205); "
        else:
            flash_rule += "background-color: rgba(255, 244, 185, 150); "
        flash_rule += "border-radius: 6px; "
        flash_rule += "}"
        base = self._flash_base_stylesheet
        combined = f"{base}\n{flash_rule}" if base else flash_rule
        self.setStyleSheet(combined)
        self._flash_restore_timer.start(550)

    def _clear_added_flash(self) -> None:
        """
        Restore card stylesheet after temporary add flash.
        """
        if self._flash_base_stylesheet is None:
            return
        self.setStyleSheet(self._flash_base_stylesheet)
        self._flash_base_stylesheet = None

    def highlight_search(
        self,
        pattern: str,
        scope: str,
        normalized_oe: str | None = None,
        oe_token_ids: set[int] | None = None,
    ) -> int:
        """
        Highlight matches in OE text, translation, and notes.

        Args:
            pattern: Search pattern
            scope: Search scope ("OE Text", "ModE text", "Notes", "All")
            normalized_oe: Normalized OE query for token/root matching.
            oe_token_ids: Optional precomputed token ids to highlight.

        Returns:
            int: Number of matches found

        """
        total_matches = 0

        # OE Text scope
        if scope in ["OE Text", "Notes", "All"]:
            total_matches += self._highlight_oe_search(
                pattern, normalized_oe, oe_token_ids
            )
        else:
            SearchHighlighter.clear_highlight(self.oe_text_edit)

        # ModE text scope
        if scope in ["ModE text", "All"]:
            total_matches += SearchHighlighter.highlight_text(
                self.translation_edit, pattern
            )
        else:
            SearchHighlighter.clear_highlight(self.translation_edit)

        # Notes scope
        if scope in ["Notes", "All"]:
            total_matches += self.notes_panel.highlight_search(pattern)
        else:
            self.notes_panel.highlight_search("")

        # Make translation_edit read-only when search is active to allow
        # N/Shift-N shortcuts
        self.translation_edit.setReadOnly(bool(pattern))

        return total_matches

    def _highlight_oe_search(
        self,
        pattern: str,
        normalized_oe: str | None,
        oe_token_ids: set[int] | None,
    ) -> int:
        """
        Highlight OE token matches for search.

        Args:
            pattern: Raw search query.
            normalized_oe: Normalized OE query, if enabled.
            oe_token_ids: Optional precomputed token id set.

        Returns:
            Number of OE matches highlighted.

        """
        if not pattern:
            return SearchHighlighter.highlight_text(self.oe_text_edit, pattern)
        token_ids = oe_token_ids if oe_token_ids is not None else set()
        if not token_ids and normalized_oe:
            token_ids = self._matching_oe_token_ids(normalized_oe)
        if token_ids:
            ranges = self._token_ranges_for_ids(token_ids)
            return SearchHighlighter.highlight_token_ranges(self.oe_text_edit, ranges)
        return SearchHighlighter.highlight_text(self.oe_text_edit, pattern)

    def _matching_oe_token_ids(self, normalized_oe: str) -> set[int]:
        """
        Return token ids that match normalized surface/root fields.

        Args:
            normalized_oe: Normalized OE query.

        Returns:
            Set of matching token ids.

        """
        token_ids: set[int] = set()
        for token in self.oe_text_edit.tokens:
            if token.id is None:
                continue
            if normalized_oe in (token.surface_normalized or ""):
                token_ids.add(token.id)
                continue
            root = token.annotation.root_normalized if token.annotation else None
            if root and normalized_oe in root:
                token_ids.add(token.id)
        return token_ids

    def _token_ranges_for_ids(self, token_ids: set[int]) -> list[tuple[int, int]]:
        """
        Convert token ids to character ranges in the OE text editor.

        Args:
            token_ids: Token ids to map.

        Returns:
            Ordered list of ``(start, end)`` positions.

        """
        ranges = [
            self.oe_text_edit.token_to_position[token_id]
            for token_id in token_ids
            if token_id in self.oe_text_edit.token_to_position
        ]
        return sorted(ranges, key=lambda item: item[0])

    def focus_token_by_id(self, token_id: int | None) -> None:
        """
        Focus a token selection by token id.

        Args:
            token_id: Token id to focus.

        """
        if token_id is None:
            self.oe_text_edit.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        token = next(
            (item for item in self.oe_text_edit.tokens if item.id == token_id), None
        )
        if token is None:
            self.oe_text_edit.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        self.oe_text_edit.set_selected_token_index(token.order_index)
        self.oe_text_edit.setFocus(Qt.FocusReason.OtherFocusReason)

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
        self.sentence_number_label = QLabel(self._line_reference_text())
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
        self.toggle_paragraph_button = QPushButton("Mark as ...")
        self.paragraph_menu = QMenu(self)
        self.toggle_paragraph_button.setMenu(self.paragraph_menu)
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
        self._apply_verse_background_style()

    def _line_reference_text(self) -> str:
        """
        Build the sentence/verse reference label used in card headers.

        Returns:
            The formatted reference label.

        """
        paragraph_order = (
            self.sentence.paragraph.order if self.sentence.paragraph else 0
        )
        return (
            f"[{self.sentence.display_order}] ¶:{paragraph_order} "
            f"{self.sentence.reference_label}"
        )

    def _apply_verse_background_style(self) -> None:
        """
        Apply theme-relative verse card background for stanza sentences.
        """
        if not self.sentence.is_verse:
            return
        base = self.palette().color(QPalette.ColorRole.Base)
        verse_bg = (
            base.lighter(110)
            if base.lightness() < THEME_DARK_LIGHTNESS_THRESHOLD
            else base.darker(110)
        )
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)  # noqa: FBT003
        self.setStyleSheet(
            "QWidget#sentence-card { "
            f"background-color: {verse_bg.name()}; "
            "border-radius: 6px; "
            "}"
        )

    def refresh_theme(self) -> None:
        """
        Recompute theme-derived styling after the application palette changes.

        Two things about this card bake a concrete palette-derived color at
        build time rather than following the palette automatically: the verse
        background style (a literal hex color) and any active token
        highlighting command (POS/case/number/idiom colors computed from the
        palette). Neither updates on its own when the theme changes, so this
        must be called explicitly by whatever drives a live theme switch.

        Returns:
            None

        """
        self._apply_verse_background_style()
        self.sentence_highlighter.highlight()

    # ========================================================================
    # Annotation related methods
    # ========================================================================

    def _open_annotation_modal(self) -> None:
        """
        Open annotation modal for selected token or idiom.

        Delegates routing to
        :class:`~oeapp.ui.sentence_card_controller.SentenceCardController`.
        """
        self.controller.open_annotation_modal()

    def _open_idiom_modal(self, idiom: Idiom) -> None:
        """
        Open annotation modal for an existing idiom.

        Args:
            idiom: Idiom to open the annotation modal for

        """
        self.controller.open_idiom_modal(idiom)

    def _open_new_idiom_modal(self, start_order: int, end_order: int) -> None:
        """
        Open annotation modal for a new idiom.

        Args:
            start_order: Start token order index
            end_order: End token order index

        """
        self.controller.open_new_idiom_modal(start_order, end_order)

    def _open_token_modal(self, token: "Token") -> None:
        """
        Open annotation modal for a single token.

        Args:
            token: "Token" to open the annotation modal for

        """
        self.controller.open_token_modal(token)

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
            "article_type": annotation.article_type,
            "pronoun_type": annotation.pronoun_type,
            "pronoun_number": annotation.pronoun_number,
            "verb_class": annotation.verb_class,
            "verb_tense": annotation.verb_tense,
            "verb_person": annotation.verb_person,
            "verb_mood": annotation.verb_mood,
            "verb_aspect": annotation.verb_aspect,
            "verb_form": annotation.verb_form,
            "verb_direct_object_case": annotation.verb_direct_object_case,
            "verb_requires_infinitive": annotation.verb_requires_infinitive,
            "verb_impersonal": annotation.verb_impersonal,
            "verb_transitivity": annotation.verb_transitivity,
            "prep_case": annotation.prep_case,
            "adverb_degree": annotation.adverb_degree,
            "adjective_inflection": annotation.adjective_inflection,
            "adjective_degree": annotation.adjective_degree,
            "conjunction_type": annotation.conjunction_type,
            "confidence": annotation.confidence,
            "modern_english_meaning": annotation.modern_english_meaning,
            "sense": annotation.sense,
            "root": annotation.root,
            "root_normalized": annotation.root_normalized,
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
        elif annotation.idiom_id:
            # For idiom annotations, we need to refresh the sentence relationships
            # to pick up the new idiom and its annotation, then update the tokens
            # in the text edit so it knows which tokens are now part of an idiom.
            self.session.refresh(self.sentence, ["tokens", "idioms"])
            self.oe_text_edit.set_tokens()
            self.oe_text_edit.render_readonly_text()

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

    def _on_token_table_token_selected(self, token: "Token") -> None:
        """
        Handle token selection from the token table.

        Args:
            token: Selected token

        """
        # Resolve against live token mappings in case token table row still
        # references a stale token instance from before retokenization.
        current = self.oe_text_edit.tokens_by_id.get(token.id) if token.id else None
        selected = current or token
        if selected.order_index < 0:
            return
        self.oe_text_edit.set_selected_token_index(selected.order_index, emit=False)
        self.token_selected_for_details.emit(selected, self.sentence, self)

    # ========================================================================
    # Paragraph related methods
    # ========================================================================

    def _update_paragraph_button_state(self) -> None:
        """
        Update the toggle paragraph button text and visibility based on current state.
        """
        if not self.sentence.paragraph:
            self.toggle_paragraph_button.setVisible(False)
            return

        # Clear existing menu
        self.paragraph_menu.clear()

        # Check hierarchy state
        sentences = sorted(
            self.sentence.paragraph.sentences, key=lambda s: s.display_order
        )
        is_paragraph_start: bool = sentences and sentences[0].id == self.sentence.id  # type: ignore[assignment]

        is_section_start = False
        if is_paragraph_start:
            paragraphs = sorted(
                self.sentence.paragraph.section.paragraphs, key=lambda p: p.order
            )
            is_section_start = (
                paragraphs and paragraphs[0].id == self.sentence.paragraph.id  # type: ignore[assignment]
            )

        is_chapter_start = False
        if is_section_start:
            sections = sorted(
                self.sentence.paragraph.section.chapter.sections, key=lambda s: s.number
            )
            is_chapter_start = (
                sections and sections[0].id == self.sentence.paragraph.section.id  # type: ignore[assignment]
            )

        # Hide button for first sentence of project
        if self.sentence.display_order == 1:
            self.toggle_paragraph_button.setVisible(False)
            return

        self.toggle_paragraph_button.setVisible(True)

        if not is_paragraph_start:
            # Case A: Middle of paragraph
            action = self.paragraph_menu.addAction("Paragraph Start")
            action.triggered.connect(self._on_split_paragraph_clicked)
        elif not is_section_start:
            # Case B: Paragraph start, but not section start
            action_not_p = self.paragraph_menu.addAction("Not Paragraph Start")
            action_not_p.triggered.connect(self._on_merge_paragraph_clicked)
            action_section = self.paragraph_menu.addAction("Section Start")
            action_section.triggered.connect(self._on_split_section_clicked)
        elif not is_chapter_start:
            # Case C: Section start, but not chapter start
            action_not_p = self.paragraph_menu.addAction("Not Paragraph Start")
            action_not_p.triggered.connect(self._on_merge_paragraph_clicked)
            action_not_s = self.paragraph_menu.addAction("Not Section Start")
            action_not_s.triggered.connect(self._on_merge_section_clicked)
            action_chapter = self.paragraph_menu.addAction("Chapter Start")
            action_chapter.triggered.connect(self._on_split_chapter_clicked)
        else:
            # Case D: Chapter start
            action_not_p = self.paragraph_menu.addAction("Not Paragraph Start")
            action_not_p.triggered.connect(self._on_merge_paragraph_clicked)
            action_not_s = self.paragraph_menu.addAction("Not Section Start")
            action_not_s.triggered.connect(self._on_merge_section_clicked)
            action_not_c = self.paragraph_menu.addAction("Not Chapter Start")
            action_not_c.triggered.connect(self._on_merge_chapter_clicked)

    # -------------------------------------------------------------------------
    # Paragraph related event handlers
    # -------------------------------------------------------------------------

    def _on_split_paragraph_clicked(self) -> None:
        """Handle Split Paragraph action."""
        self._execute_hierarchy_command(
            SplitParagraphCommand(sentence_id=self.sentence.id)
        )

    def _on_merge_paragraph_clicked(self) -> None:
        """Handle Merge Paragraph action."""
        self._execute_hierarchy_command(
            MergeParagraphCommand(sentence_id=self.sentence.id)
        )

    def _on_split_section_clicked(self) -> None:
        """Handle Split Section action."""
        if self.sentence.paragraph:
            self._execute_hierarchy_command(
                SplitSectionCommand(paragraph_id=self.sentence.paragraph.id)
            )

    def _on_merge_section_clicked(self) -> None:
        """Handle Merge Section action."""
        if self.sentence.paragraph:
            self._execute_hierarchy_command(
                MergeSectionCommand(paragraph_id=self.sentence.paragraph.id)
            )

    def _on_split_chapter_clicked(self) -> None:
        """Handle Split Chapter action."""
        if self.sentence.paragraph and self.sentence.paragraph.section:
            self._execute_hierarchy_command(
                SplitChapterCommand(section_id=self.sentence.paragraph.section.id)
            )

    def _on_merge_chapter_clicked(self) -> None:
        """Handle Merge Chapter action."""
        if self.sentence.paragraph and self.sentence.paragraph.section:
            self._execute_hierarchy_command(
                MergeChapterCommand(section_id=self.sentence.paragraph.section.id)
            )

    def _execute_hierarchy_command(self, command) -> None:
        """Execute a hierarchy command and update UI."""
        if not self.command_manager:
            return

        if self.command_manager.execute(command):
            # Refresh sentence from database
            self.session.refresh(self.sentence)
            # Update UI
            self._update_paragraph_button_state()

            self.sentence_number_label.setText(self._line_reference_text())

            # Emit signal to refresh all cards
            if self.sentence.id:
                self.sentence_added.emit(self.sentence.id)
        else:
            QMessageBox.warning(
                self,
                "Action Failed",
                "Failed to perform hierarchy action. Please try again.",
            )

    # ========================================================================
    # Event handlers
    # ========================================================================

    def _on_idiom_selection(self, *args) -> None:  # noqa: ARG002
        """
        Event handler for idiom selection.
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

    def _on_token_selection(self, token: "Token") -> None:
        """
        Event handler for single token selection.

        Args:
            token: Token that was selected

        """
        self.token_table.select_token_by_id(token.id)
        self.add_note_button.setEnabled(False)

    # -------------------------------------------------------------------------
    # Edit mode related event handlers
    # -------------------------------------------------------------------------

    def _on_edit_oe_clicked(self) -> None:
        """
        Handle Edit OE button click - enter edit mode.
        """
        self.controller.on_edit_oe_clicked()

    def _on_save_oe_clicked(self) -> None:
        """
        Handle Save OE button click - save changes and exit edit mode.
        """
        self.controller.on_save_oe_clicked()

    def _on_cancel_edit_clicked(self) -> None:
        """
        Handle "Cancel Edit" button click - discard changes and exit edit mode.
        """
        self.controller.on_cancel_edit_clicked()

    # -------------------------------------------------------------------------
    # Translation text edit related event handlers
    # -------------------------------------------------------------------------

    def _on_translation_changed(self) -> None:
        """
        Handle translation text change.
        """
        self.controller.on_translation_changed()

    # -------------------------------------------------------------------------
    # Sentence related event handlers
    # -------------------------------------------------------------------------

    def _on_merge_clicked(self) -> None:
        """
        Handle merge button click.
        """
        self.controller.on_merge_clicked()

    def _on_add_sentence_before_clicked(self) -> None:
        """
        Handle "Add Sentence: Before" button click.
        """
        self.controller.on_add_sentence_before_clicked()

    def _on_add_sentence_after_clicked(self) -> None:
        """
        Handle "Add Sentence: After" button click.
        """
        self.controller.on_add_sentence_after_clicked()

    def _on_delete_clicked(self) -> None:
        """
        Handle Delete button click.
        """
        self.controller.on_delete_clicked()

"""Sentence card UI component."""

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QPoint, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeySequence,
    QMouseEvent,
    QShortcut,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from oeapp.services.commands import (
    AnnotateTokenCommand,
    CommandManager,
    EditSentenceCommand,
)
from oeapp.ui.annotation_modal import AnnotationModal
from oeapp.ui.token_table import TokenTable

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token
    from oeapp.services.db import Database


class ClickableTextEdit(QTextEdit):
    """QTextEdit that emits a signal when clicked."""

    clicked = Signal(QPoint)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse press event and emit clicked signal."""
        super().mousePressEvent(event)
        self.clicked.emit(event.position().toPoint())


class SentenceCard(QWidget):
    """
    Widget representing a sentence card with annotations.

    Args:
        sentence: Sentence model instance

    Keyword Args:
        db: Database connection
        command_manager: Command manager for undo/redo
        parent: Parent widget

    """

    def __init__(
        self,
        sentence: Sentence,
        db: Database | None = None,
        command_manager: CommandManager | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.sentence = sentence
        self.db = db
        self.command_manager = command_manager
        self.token_table = TokenTable()
        self.tokens: list[Token] = sentence.tokens
        self.annotations: dict[int, Annotation] = {
            cast("int", token.id): token.annotation for token in self.tokens
        }
        # Track current highlight position to clear it later
        self._current_highlight_start: int | None = None
        self._current_highlight_length: int | None = None
        self._setup_ui()
        self._setup_shortcuts()

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

    def _setup_shortcuts(self):
        """
        Set up keyboard shortcuts.

        The following shortcuts are set up:
        - 'A' key to annotate selected token
        - Arrow keys for token navigation
        - 'Ctrl+Enter' to split sentence
        - 'Ctrl+M' to merge sentence
        - 'Ctrl+Delete' to delete sentence
        """
        # 'A' key to annotate selected token
        annotate_shortcut = QShortcut(QKeySequence("A"), self)
        annotate_shortcut.activated.connect(self._open_annotation_modal)

        # Arrow keys for token navigation
        next_token_shortcut = QShortcut(QKeySequence("Right"), self)
        next_token_shortcut.activated.connect(self._next_token)
        prev_token_shortcut = QShortcut(QKeySequence("Left"), self)
        prev_token_shortcut.activated.connect(self._prev_token)

    def _next_token(self) -> None:
        """Navigate to next token."""
        current_row = self.token_table.current_row
        if current_row < len(self.tokens) - 1:
            self.token_table.select_token(current_row + 1)

    def _prev_token(self):
        """Navigate to previous token."""
        current_row = self.token_table.current_row
        if current_row > 1 and self.tokens:
            self.token_table.select_token(current_row - 1)

    def _setup_ui(self):
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header with sentence number and actions
        header_layout = QHBoxLayout()
        self.sentence_number_label = QLabel(f"[{self.sentence.display_order}]")
        self.sentence_number_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.sentence_number_label)

        # Action buttons
        self.split_button = QPushButton("Split")
        self.merge_button = QPushButton("Merge")
        self.delete_button = QPushButton("Delete")
        header_layout.addStretch()
        header_layout.addWidget(self.split_button)
        header_layout.addWidget(self.merge_button)
        header_layout.addWidget(self.delete_button)
        layout.addLayout(header_layout)

        # Old English text line (editable)
        oe_label = QLabel("Old English:")
        oe_label.setFont(QFont("Arial", 14))
        layout.addWidget(oe_label)

        self.oe_text_edit = ClickableTextEdit()
        self.oe_text_edit.setText(self.sentence.text_oe)
        self.oe_text_edit.setFont(QFont("Times New Roman", 18))
        self.oe_text_edit.setPlaceholderText("Enter Old English text...")
        self.oe_text_edit.textChanged.connect(self._on_oe_text_changed)
        self.oe_text_edit.clicked.connect(self._on_oe_text_clicked)
        layout.addWidget(self.oe_text_edit)

        # Token annotation grid
        self.token_table.annotation_requested.connect(self._open_annotation_modal)
        self.token_table.token_selected.connect(self._highlight_token_in_text)
        layout.addWidget(self.token_table)
        self.set_tokens(self.tokens)

        # Modern English translation
        translation_label = QLabel("Modern English Translation:")
        translation_label.setFont(QFont("Arial", 18))
        layout.addWidget(translation_label)

        self.translation_edit = QTextEdit()
        self.translation_edit.setPlainText(self.sentence.text_modern or "")
        self.translation_edit.setPlaceholderText("Enter Modern English translation...")
        self.translation_edit.setMaximumHeight(100)
        self.translation_edit.textChanged.connect(self._on_translation_changed)
        layout.addWidget(self.translation_edit)

        # Notes section placeholder
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont("Arial", 10))
        layout.addWidget(notes_label)

        self.notes_label = QLabel("(No notes yet)")
        self.notes_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.notes_label)

        layout.addStretch()

    def set_tokens(self, tokens: list[Token]):
        """
        Set tokens for this sentence card.  This will also load the annotations
        for the tokens.

        Args:
            tokens: List of tokens

        """
        self.token_table.set_tokens(tokens, self.annotations)

    def _open_annotation_modal(self) -> None:
        """
        Open annotation modal for selected token.
        """
        token: Token | None = self.token_table.get_selected_token()
        if not token:
            # Select first token if none selected
            if self.tokens:
                token = self.tokens[0]
                self.token_table.select_token(0)
            else:
                return

        # Open modal
        modal = AnnotationModal(token, token.annotation, self)
        modal.annotation_applied.connect(self._on_annotation_applied)
        modal.exec()

    def _on_annotation_applied(self, annotation: Annotation) -> None:
        """
        Handle annotation applied signal.

        Args:
            annotation: Applied annotation

        """
        # Get before state
        before_annotation = self.annotations.get(annotation.token_id)
        before_state = {}
        if before_annotation:
            before_state = {
                "pos": before_annotation.pos,
                "gender": before_annotation.gender,
                "number": before_annotation.number,
                "case": before_annotation.case,
                "declension": before_annotation.declension,
                "pronoun_type": before_annotation.pronoun_type,
                "verb_class": before_annotation.verb_class,
                "verb_tense": before_annotation.verb_tense,
                "verb_person": before_annotation.verb_person,
                "verb_mood": before_annotation.verb_mood,
                "verb_aspect": before_annotation.verb_aspect,
                "verb_form": before_annotation.verb_form,
                "prep_case": before_annotation.prep_case,
                "uncertain": before_annotation.uncertain,
                "alternatives_json": before_annotation.alternatives_json,
                "confidence": before_annotation.confidence,
            }

        after_state = {
            "pos": annotation.pos,
            "gender": annotation.gender,
            "number": annotation.number,
            "case": annotation.case,
            "declension": annotation.declension,
            "pronoun_type": annotation.pronoun_type,
            "verb_class": annotation.verb_class,
            "verb_tense": annotation.verb_tense,
            "verb_person": annotation.verb_person,
            "verb_mood": annotation.verb_mood,
            "verb_aspect": annotation.verb_aspect,
            "verb_form": annotation.verb_form,
            "prep_case": annotation.prep_case,
            "uncertain": annotation.uncertain,
            "alternatives_json": annotation.alternatives_json,
            "confidence": annotation.confidence,
        }

        # Create command for undo/redo
        if self.command_manager and self.db:
            assert self.command_manager is not None  # noqa: S101
            assert self.db is not None  # noqa: S101
            command = AnnotateTokenCommand(
                db=self.db,
                token_id=annotation.token_id,
                before=before_state,
                after=after_state,
            )
            if self.command_manager.execute(command):
                # Update local cache
                self.annotations[annotation.token_id] = annotation
                # Update token table display
                self.token_table.update_annotation(annotation)
                return

        # Fallback: direct save if command manager not available
        if self.db:
            self._save_annotation(annotation)

        # Update local cache
        self.annotations[annotation.token_id] = annotation

        # Update token table display
        self.token_table.update_annotation(annotation)

    def _on_oe_text_clicked(self, position: QPoint) -> None:
        """
        Handle click on Old English text to select corresponding token.

        Args:
            position: Mouse click position in widget coordinates

        """
        # Get cursor at click position
        cursor = self.oe_text_edit.cursorForPosition(position)
        cursor_pos = cursor.position()

        # Get the plain text
        text = self.oe_text_edit.toPlainText()
        if not text or not self.tokens:
            return

        # Find which token contains this cursor position
        # We need to map cursor position to token by finding which token's
        # surface text spans that position
        token_index = self._find_token_at_position(text, cursor_pos)
        if token_index is not None:
            self.token_table.select_token(token_index)

    def _find_token_at_position(self, text: str, position: int) -> int | None:
        """
        Find the token index that contains the given character position.

        Args:
            text: The full sentence text
            position: Character position in the text

        Returns:
            Token index if found, None otherwise

        """
        if not self.tokens:
            return None

        # Build a mapping of token positions in the text
        token_positions: list[tuple[int, int, int]] = []  # (start, end, token_index)

        for token_idx, token in enumerate(self.tokens):
            surface = token.surface
            if not surface:
                continue

            token_start = self._find_token_occurrence(text, token, surface)
            if token_start is None:
                continue

            token_end = token_start + len(surface)
            token_positions.append((token_start, token_end, token_idx))

        # Find which token contains the position
        for start, end, token_idx in token_positions:
            if start <= position < end:
                return token_idx

        # If position is not within any token, find the nearest token
        # (useful for whitespace between tokens)
        return self._find_nearest_token(token_positions, position)

    def _find_token_occurrence(
        self, text: str, token: Token, surface: str
    ) -> int | None:
        """
        Find the occurrence position of a token's surface text in the sentence.

        Args:
            text: The full sentence text
            token: The token to find
            surface: The surface text of the token

        Returns:
            Character position of the token occurrence, or None if not found

        """
        # Find all occurrences of this surface text
        occurrences = []
        start = 0
        while True:
            pos = text.find(surface, start)
            if pos == -1:
                break
            occurrences.append(pos)
            start = pos + 1

        if not occurrences:
            return None

        # Use order_index to determine which occurrence this token represents
        # Count how many tokens with the same surface appear before this one
        same_surface_count = 0
        for t in self.tokens:
            if t.order_index >= token.order_index:
                break
            if t.surface == surface:
                same_surface_count += 1

        # Select the occurrence at the same_surface_count index
        if same_surface_count < len(occurrences):
            return occurrences[same_surface_count]
        # Fallback to first occurrence if index is out of range
        return occurrences[0]

    def _find_nearest_token(
        self, token_positions: list[tuple[int, int, int]], position: int
    ) -> int | None:
        """
        Find the nearest token to the given position.

        Args:
            token_positions: List of (start, end, token_index) tuples
            position: Character position in the text

        Returns:
            Token index of nearest token, or None if no tokens found

        """
        nearest_token = None
        min_distance = float("inf")
        for start, end, token_idx in token_positions:
            # Check distance to start and end of token
            if position < start:
                distance = start - position
            elif position >= end:
                distance = position - end + 1
            else:
                # Position is within token (shouldn't happen here, but handle it)
                return token_idx

            if distance < min_distance:
                min_distance = distance
                nearest_token = token_idx

        return nearest_token

    def _on_oe_text_changed(self) -> None:
        """Handle Old English text change."""
        # Clear highlights when text is edited
        self._clear_highlight()

        if not self.db or not self.command_manager or not self.sentence.id:
            return

        new_text = self.oe_text_edit.text()
        old_text = self.sentence.text_oe

        if new_text != old_text:
            command = EditSentenceCommand(
                db=self.db,
                sentence_id=self.sentence.id,
                field="text_oe",
                before=old_text,
                after=new_text,
            )
            if self.command_manager.execute(command):
                self.sentence.text_oe = new_text

    def _on_translation_changed(self) -> None:
        """Handle translation text change."""
        if not self.db or not self.command_manager or not self.sentence.id:
            return

        new_text = self.translation_edit.toPlainText()
        old_text = self.sentence.text_modern or ""

        if new_text != old_text:
            command = EditSentenceCommand(
                db=self.db,
                sentence_id=self.sentence.id,
                field="text_modern",
                before=old_text,
                after=new_text,
            )
            if self.command_manager.execute(command):
                self.sentence.text_modern = new_text

    def _clear_highlight(self) -> None:
        """
        Clear any existing highlight in the oe_text_edit.
        """
        # Clear extra selections (temporary highlights)
        self.oe_text_edit.setExtraSelections([])
        self._current_highlight_start = None
        self._current_highlight_length = None

    def _highlight_token_in_text(self, token: Token) -> None:
        """
        Highlight the corresponding token in the oe_text_edit.

        Args:
            token: Token to highlight

        """
        # Clear any existing highlight first
        self._clear_highlight()

        # Get the text from the editor
        text = self.oe_text_edit.toPlainText()
        if not text:
            return

        # Get the token surface text
        surface = token.surface
        if not surface:
            return

        # Find all occurrences of the surface text
        occurrences = []
        start = 0
        while True:
            pos = text.find(surface, start)
            if pos == -1:
                break
            occurrences.append(pos)
            start = pos + 1

        # If no occurrences found, return
        if not occurrences:
            return

        # Use order_index to determine which occurrence to highlight
        # Count how many tokens with the same surface appear before this one
        same_surface_count = 0
        for t in self.tokens:
            if t.order_index >= token.order_index:
                break
            if t.surface == surface:
                same_surface_count += 1

        # Select the occurrence at the same_surface_count index
        if same_surface_count < len(occurrences):
            highlight_pos = occurrences[same_surface_count]
        else:
            # Fallback to first occurrence if index is out of range
            highlight_pos = occurrences[0]

        # Create cursor and highlight the text using extraSelections
        cursor = QTextCursor(self.oe_text_edit.document())
        cursor.setPosition(highlight_pos)
        cursor.movePosition(
            QTextCursor.MoveOperation.Right,
            QTextCursor.MoveMode.KeepAnchor,
            len(surface),
        )

        # Apply highlight format
        char_format = QTextCharFormat()
        # Use a yellow background color
        char_format.setBackground(QColor(200, 200, 0, 100))

        # Use extraSelections for temporary highlighting
        extra_selection = QTextEdit.ExtraSelection()
        extra_selection.cursor = cursor  # type: ignore[attr-defined]
        extra_selection.format = char_format  # type: ignore[attr-defined]

        self.oe_text_edit.setExtraSelections([extra_selection])

        # Store position for reference
        self._current_highlight_start = highlight_pos
        self._current_highlight_length = len(surface)

    def _save_annotation(self, annotation: Annotation) -> None:
        """
        Save annotation to database.

        Args:
            annotation: Annotation to save

        """
        if not self.db:
            return

        cursor = self.db.conn.cursor()

        # Check if annotation exists
        cursor.execute(
            "SELECT token_id FROM annotations WHERE token_id = ?",
            (annotation.token_id,),
        )
        exists = cursor.fetchone()

        if exists:
            # Update existing annotation
            cursor.execute(
                """
                UPDATE annotations SET
                    pos = ?, gender = ?, number = ?, "case" = ?, declension = ?,
                    pronoun_type = ?, verb_class = ?, verb_tense = ?, verb_person = ?,
                    verb_mood = ?, verb_aspect = ?, verb_form = ?, prep_case = ?,
                    uncertain = ?, alternatives_json = ?, confidence = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE token_id = ?
            """,
                (
                    annotation.pos,
                    annotation.gender,
                    annotation.number,
                    annotation.case,
                    annotation.declension,
                    annotation.pronoun_type,
                    annotation.verb_class,
                    annotation.verb_tense,
                    annotation.verb_person,
                    annotation.verb_mood,
                    annotation.verb_aspect,
                    annotation.verb_form,
                    annotation.prep_case,
                    annotation.uncertain,
                    annotation.alternatives_json,
                    annotation.confidence,
                    annotation.token_id,
                ),
            )
        else:
            # Insert new annotation
            cursor.execute(
                """
                INSERT INTO annotations (
                    token_id, pos, gender, number, "case", declension,
                    pronoun_type, verb_class, verb_tense, verb_person,
                    verb_mood, verb_aspect, verb_form, prep_case,
                    uncertain, alternatives_json, confidence
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    annotation.token_id,
                    annotation.pos,
                    annotation.gender,
                    annotation.number,
                    annotation.case,
                    annotation.declension,
                    annotation.pronoun_type,
                    annotation.verb_class,
                    annotation.verb_tense,
                    annotation.verb_person,
                    annotation.verb_mood,
                    annotation.verb_aspect,
                    annotation.verb_form,
                    annotation.prep_case,
                    annotation.uncertain,
                    annotation.alternatives_json,
                    annotation.confidence,
                ),
            )

        self.db.conn.commit()

    def get_oe_text(self) -> str:
        """
        Get Old English text.

        Returns:
            Old English text string

        """
        return self.oe_text_edit.text()

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
        self.sentence_number_label.setText(f"[{sentence.display_order}]")
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

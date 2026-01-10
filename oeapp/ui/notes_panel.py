"""Notes panel UI component."""

from typing import TYPE_CHECKING, Final, cast

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QMouseEvent
from PySide6.QtWidgets import (
    QLabel,
    QLayout,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from oeapp.state import ApplicationState
from oeapp.ui.dialogs.note_dialog import NoteDialog
from oeapp.utils import clear_layout

if TYPE_CHECKING:
    from oeapp.models.note import Note
    from oeapp.models.sentence import Sentence
    from oeapp.ui.sentence_card import SentenceCard


class ClickableNoteLabel(QLabel):
    """
    QLabel that emits signals when clicked or double-clicked.

    Args:
        note: Note to display
        parent: Parent widget

    """

    #: Signal emitted when the note is clicked (emits Note)
    clicked = Signal(object)
    #: Signal emitted when the note is double-clicked (emits Note)
    double_clicked = Signal(object)

    def __init__(self, note: Note, parent: QWidget | None = None):
        super().__init__(parent)
        self.note = note
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle mouse left button press event by emitting the :attr:`clicked`
        signal.

        Args:
            event: Mouse press event

        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.note)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """
        Handle mouse double-click event by emitting the :attr:`double_clicked` signal.

        Args:
            event: Mouse double-click event

        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.note)
        super().mouseDoubleClickEvent(event)


class NotesPanel(QWidget):
    """
    Widget displaying notes panel.

    Keyword Args:
        sentence: Sentence to display notes for
        parent: Parent widget

    """

    # -------------------------------------------------------------------------
    # Signals
    # -------------------------------------------------------------------------

    #: Signal emitted when a note is clicked.
    note_clicked = Signal(object)
    #: Signal emitted when a note is double-clicked.
    note_double_clicked = Signal(object)

    # -------------------------------------------------------------------------
    # Constants
    # -------------------------------------------------------------------------

    #: Font size in points for note labels.
    FONT_SIZE_IN_POINTS: Final[int] = 12
    #: Font family for note labels.
    FONT_FAMILY: Final[str] = "Helvetica"
    #: Font style for note labels.
    NOTE_STYLE: Final[str] = "color: #666; font-style: italic;"

    def __init__(
        self,
        sentence: Sentence | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        assert sentence is not None, "Sentence must be provided"  # noqa: S101
        self.sentence = cast("Sentence", sentence)
        self.card = cast("SentenceCard", parent)
        self.state = ApplicationState()
        self.build()

    def build(self) -> None:
        """Set up the UI layout."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Will be populated by update_notes()
        self.note_labels: list[ClickableNoteLabel] = []

    def empty_state(self) -> QLabel:
        """Show empty state for the notes panel."""
        empty_label = QLabel("(No notes yet)")
        empty_label.setStyleSheet(self.NOTE_STYLE)
        empty_label.setFont(QFont("Helvetica", 10))
        return empty_label

    def note_line(self, note_index: int, note: Note) -> ClickableNoteLabel:
        """
        Show a single note.

        Args:
            note_index: Note index (1-based)
            note: Note to display

        Returns:
            Note label

        """
        note_text = self.build_note(note_index, note)
        note_label = ClickableNoteLabel(note, self)
        note_label.setText(note_text)
        note_label.setFont(QFont(self.FONT_FAMILY, self.FONT_SIZE_IN_POINTS))
        note_label.setWordWrap(True)
        note_label.clicked.connect(self.note_clicked.emit)
        note_label.double_clicked.connect(self.note_double_clicked.emit)
        note_label.clicked.connect(self._on_note_clicked)
        note_label.double_clicked.connect(self._on_note_double_clicked)
        return note_label

    def clear_notes(self) -> None:
        """Clear all notes."""
        for label in self.note_labels:
            label.deleteLater()
        self.note_labels.clear()

    def clear_layout(self) -> None:
        """Clear the layout and notes."""
        self.clear_notes()
        layout = self.layout()
        if layout is None:
            return
        clear_layout(cast("QLayout", layout))

    def update_notes(self, sentence: Sentence | None = None) -> None:
        """
        Update notes display.

        Note:
            You can't name this method "update" because it conflicts with the
            built-in method `update` in QWidget.

        Keyword Args:
            sentence: Sentence to display notes for (optional, uses
                :attr:`sentence` if ``None``)

        """
        if sentence is not None:
            self.sentence = sentence
        self.state.session.refresh(self.sentence, ["notes"])

        layout = self.layout()
        if layout is None:
            return
        self.clear_layout()

        if not self.sentence:
            # Show empty state
            layout.addWidget(self.empty_state())
            return

        notes_list = list(self.sentence.notes) if self.sentence.notes else []
        if not notes_list:
            # Show empty state
            layout.addWidget(self.empty_state())
            return

        # Display each note with dynamic numbering (1-based index)
        for note_idx, note in enumerate(self.sentence.sorted_notes, start=1):
            note_label = self.note_line(note_idx, note)
            layout.addWidget(note_label)
            self.note_labels.append(note_label)

        # Add spacer at the end
        spacer = QSpacerItem(
            20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding
        )
        layout.addItem(spacer)

    def build_note(self, note_number: int, note: Note) -> str:
        """
        Format note for display.

        Format:

            .. code-block:: text

                <note number>. "<quoted tokens (italics)>" - <note text>

        Args:
            note_number: Note number (1-based)
            note: Note to format

        Returns:
            Formatted note string

        """
        # Get token text
        token_text = self.sentence.get_token_surfaces(note.start_token, note.end_token)

        if token_text:
            return f'{note_number}. <i>"{token_text}"</i> - {note.note_text_md}'
        return f"{note_number}. {note.note_text_md}"

    # ========================================================================
    # Event handlers
    # ========================================================================

    def _on_note_clicked(self, note: Note) -> None:
        """
        Handle note clicked.

        - Reset the current active selection in the OE text edit
        - Highlight the note
        """
        self.card.reset_selected_token()
        self.card.oe_text_edit.highlight_note(note)

    def _on_note_double_clicked(self, note: Note) -> None:
        """
        Handle note double-clicked.

        - Open the note edit dialog
        """
        if not note.start_token or not note.end_token:
            return

        # Open dialog for editing note
        dialog = NoteDialog(
            sentence=self.sentence,
            start_token_id=note.start_token,
            end_token_id=note.end_token,
            note=note,
            parent=self.card,
        )
        dialog.note_saved.connect(self._on_note_saved)
        dialog.note_saved.connect(self.card._on_note_saved)
        dialog.exec()

    def _on_note_saved(self, note_id: int) -> None:  # noqa: ARG002
        """
        Handle note saved signal - refresh the notes display.

        :class:`~oeapp.ui.sentence_card.SentenceCard` will re-render the OE text.
        """
        self.state.session.refresh(self.card.sentence)
        self.update_notes()

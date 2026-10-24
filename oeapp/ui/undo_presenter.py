"""Show the result of an application undo or redo in the main window."""

from typing import TYPE_CHECKING, Final

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPalette

from oeapp.commands import EditSentenceCommand, UndoCommand
from oeapp.models.sentence import Sentence

if TYPE_CHECKING:
    from collections.abc import Callable

    from PySide6.QtGui import QUndoCommand
    from PySide6.QtWidgets import QTextEdit

    from oeapp.ui.main_window import MainWindow
    from oeapp.ui.sentence_card import SentenceCard

#: How long a translation editor stays highlighted after an undo, in ms.
BLINK_MS: Final[int] = 550


def blink_translation(editor: "QTextEdit") -> None:
    """
    Flash a Modern English editor's background, then restore it.

    Args:
        editor: Editor to flash.

    Side Effects:
        Changes the editor's stylesheet and restores it after
        :data:`BLINK_MS`. The text is not touched, so no command is pushed.

    """
    base = editor.styleSheet()
    color = editor.palette().color(QPalette.ColorRole.Highlight)
    color.setAlpha(90)
    rule = f"QTextEdit {{ background-color: {color.name(color.NameFormat.HexArgb)}; }}"
    editor.setStyleSheet(f"{base}\n{rule}" if base else rule)
    QTimer.singleShot(BLINK_MS, editor, lambda: editor.setStyleSheet(base))


class UndoPresenter:
    """
    Bring the main window up to date around an undo or redo step.

    A translation edit is shown on its own sentence card. When that card is
    not loaded, its section is loaded and the card scrolled into view before
    the stack moves, and the editor blinks after the text is written. Every
    other step reloads the project when the command needs a full reload, and
    refreshes it otherwise.

    Args:
        main_window: Main window whose sentence cards show the result.

    """

    def __init__(self, main_window: "MainWindow") -> None:
        """
        Initialize the presenter.

        Args:
            main_window: Main window whose sentence cards show the result.

        """
        #: Main window whose sentence cards show the result.
        self.main_window = main_window

    def run_step(
        self, command: "QUndoCommand | None", step: "Callable[[], bool]"
    ) -> None:
        """
        Move the stack with ``step`` and show the result of ``command``.

        Args:
            command: The stack entry that ``step`` will undo or redo.
            step: Moves the stack; returns ``False`` when the step failed.

        Side Effects:
            Calls ``step``, may load another section, and updates the main
            window as described in :meth:`undo_translation` and
            :meth:`show_step`.

        """
        sentence_id = self._translation_sentence_id(command)
        if sentence_id is not None:
            self.undo_translation(sentence_id, step)
        elif step():
            self.show_step(command)

    def undo_translation(self, sentence_id: int, step: "Callable[[], bool]") -> None:
        """
        Undo or redo a translation edit on the sentence it changed.

        Args:
            sentence_id: Sentence whose translation the step changes.
            step: Moves the stack; returns ``False`` when the step failed.

        Side Effects:
            When the sentence's card is not loaded, loads its section and
            scrolls the card into view before calling ``step``. After a
            successful step, writes the translation into the card, blinking
            it when the section was just loaded.

        """
        if self._card_for(sentence_id) is not None:
            if step():
                self.apply_translation(sentence_id, blink=False)
            return
        sentence = Sentence.get(sentence_id)
        card = None
        if sentence is not None:
            card = self.main_window.project_ui.show_section_of(sentence)
        if card is None:
            if step():
                self.main_window.refresh_project()
            return
        self.main_window.ensure_visible(card)
        # The new cards are not laid out yet; scroll again once they are.
        QTimer.singleShot(0, card, lambda: self.main_window.ensure_visible(card))
        if step():
            self.apply_translation(sentence_id, blink=True)

    def show_step(self, command: "QUndoCommand | None") -> None:
        """
        Show the result of a stack entry that is not a translation edit.

        Args:
            command: The stack entry that was just undone or redone.

        Side Effects:
            Calls ``reload_project`` or ``refresh_project`` on the main window.

        """
        inner = command.command if isinstance(command, UndoCommand) else None
        if inner is not None and inner.needs_full_reload:
            self.main_window.reload_project()
        else:
            self.main_window.refresh_project()

    def apply_translation(self, sentence_id: int, *, blink: bool) -> None:
        """
        Write the stored translation into that sentence's card editor.

        Args:
            sentence_id: Sentence whose card shows the translation.

        Keyword Args:
            blink: Whether to flash the editor after writing.

        Side Effects:
            Replaces the card's Modern English text without pushing an edit,
            and flashes the editor when ``blink`` is set.

        """
        card = self._card_for(sentence_id)
        sentence = Sentence.get(sentence_id)
        if card is None or sentence is None:
            return
        card.set_translation_text(sentence.text_modern or "")
        if blink:
            blink_translation(card.translation_edit)

    def _translation_sentence_id(self, command: "QUndoCommand | None") -> int | None:
        """
        Get the sentence a translation edit changes.

        Args:
            command: Stack entry to inspect.

        Returns:
            The sentence id, or ``None`` when ``command`` is not a translation
            edit.

        """
        inner = command.command if isinstance(command, UndoCommand) else None
        if isinstance(inner, EditSentenceCommand) and inner.field == "text_modern":
            return inner.sentence_id
        return None

    def _card_for(self, sentence_id: int) -> "SentenceCard | None":
        """
        Find the loaded card for a sentence.

        Args:
            sentence_id: Sentence to look up.

        Returns:
            The loaded sentence card, or ``None`` when it is not loaded.

        """
        return next(
            (
                card
                for card in self.main_window.sentence_cards
                if card.sentence.id == sentence_id
            ),
            None,
        )

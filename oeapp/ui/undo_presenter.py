"""Show the result of an application undo or redo in the main window."""

from typing import TYPE_CHECKING

from oeapp.commands import EditSentenceCommand, UndoCommand
from oeapp.models.sentence import Sentence

if TYPE_CHECKING:
    from PySide6.QtGui import QUndoCommand

    from oeapp.ui.main_window import MainWindow
    from oeapp.ui.sentence_card import SentenceCard


class UndoPresenter:
    """
    Bring the main window up to date after an undo or redo step.

    A translation edit on a sentence card that is on screen is written into
    that card's Modern English editor in place. Every other step reloads the
    project when the command needs a full reload, and refreshes it otherwise.

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

    def show_step(self, command: "QUndoCommand | None") -> None:
        """
        Show the result of the stack entry that was just undone or redone.

        Args:
            command: The stack entry that was just undone or redone.

        Side Effects:
            Writes a visible card's translation, or calls ``reload_project`` or
            ``refresh_project`` on the main window.

        """
        inner = command.command if isinstance(command, UndoCommand) else None
        if (
            isinstance(inner, EditSentenceCommand)
            and inner.field == "text_modern"
            and self._card_for(inner.sentence_id) is not None
        ):
            self.apply_translation(inner.sentence_id, blink=False)
        elif inner is not None and inner.needs_full_reload:
            self.main_window.reload_project()
        else:
            self.main_window.refresh_project()

    def apply_translation(self, sentence_id: int, *, blink: bool) -> None:
        """
        Write the stored translation into that sentence's card editor.

        Args:
            sentence_id: Sentence whose card shows the translation.

        Keyword Args:
            blink: Whether to flash the card after writing. Not used yet.

        Side Effects:
            Replaces the card's Modern English text without pushing an edit.

        """
        del blink
        card = self._card_for(sentence_id)
        sentence = Sentence.get(sentence_id)
        if card is None or sentence is None:
            return
        card.set_translation_text(sentence.text_modern or "")

    def _card_for(self, sentence_id: int) -> "SentenceCard | None":
        """
        Find the on-screen card for a sentence.

        Args:
            sentence_id: Sentence to look up.

        Returns:
            The loaded sentence card, or ``None`` when it is not on screen.

        """
        return next(
            (
                card
                for card in self.main_window.sentence_cards
                if card.sentence.id == sentence_id
            ),
            None,
        )

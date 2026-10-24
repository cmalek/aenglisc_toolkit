"""Track the open Typed Run in the Modern English editor."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtGui import QUndoCommand

    from oeapp.commands import UndoCommand


class TypedRun:
    """
    The one open run of typing in a sentence's Modern English editor.

    While a run is open, each further translation edit of the same sentence
    merges into :attr:`open_command`, so the whole run is one undo step.
    Gestures that leave the editor's typing context call :meth:`end`.
    """

    def __init__(self) -> None:
        """Initialize with no open run."""
        #: Sentence whose translation is being typed, or ``None`` when closed.
        self.sentence_id: int | None = None
        #: Stack entry that later keystrokes merge into, or ``None`` when closed.
        self.open_command: UndoCommand | None = None

    def open_for(self, command: UndoCommand) -> None:
        """
        Start a run whose later edits merge into ``command``.

        Args:
            command: The translation edit just pushed onto the stack.

        Side Effects:
            Ends any previous run and marks ``command`` open.

        """
        self.end()
        command.run_open = True
        self.open_command = command
        self.sentence_id = getattr(command.command, "sentence_id", None)

    def end(self) -> None:
        """
        Close the open run, if any.

        Side Effects:
            Marks :attr:`open_command` closed and clears both fields.

        """
        if self.open_command is not None:
            self.open_command.run_open = False
        self.open_command = None
        self.sentence_id = None

    def end_for(self, sentence_id: int) -> None:
        """
        Close the run when it belongs to ``sentence_id``.

        Args:
            sentence_id: Sentence whose run should close.

        Side Effects:
            Calls :meth:`end` when the open run is for ``sentence_id``.

        """
        if self.sentence_id == sentence_id:
            self.end()

    def end_unless(self, sentence_id: int | None) -> None:
        """
        Close the run when it belongs to a sentence other than ``sentence_id``.

        Args:
            sentence_id: Sentence whose run may stay open.

        Side Effects:
            Calls :meth:`end` when the open run is for another sentence.

        """
        if self.sentence_id is not None and self.sentence_id != sentence_id:
            self.end()

    def continues(self, sentence_id: int, top: QUndoCommand | None) -> bool:
        """
        Report whether an edit of ``sentence_id`` continues the open run.

        Args:
            sentence_id: Sentence being edited.
            top: The command at the top of the undo stack.

        Returns:
            ``True`` when the run is open for ``sentence_id`` and its command is
            still the top of the stack.

        """
        return (
            self.open_command is not None
            and self.sentence_id == sentence_id
            and top is self.open_command
        )

"""Adapter that lets a :class:`Command` live on a ``QUndoStack``."""

from typing import cast

from PySide6.QtGui import QUndoCommand, QUndoStack

from .abstract import Command
from .sentence import EditSentenceCommand
from .stack_maintenance import maintain_stack, settle


class UndoCommand(QUndoCommand):
    """
    A ``QUndoCommand`` that delegates to a :class:`Command`.

    ``redo`` runs ``Command.execute`` and ``undo`` runs ``Command.undo``. When
    ``execute`` fails the command marks itself obsolete so the stack drops it.
    When ``undo`` fails the next ``redo`` is skipped, so the caller can step the
    stack index back without running ``execute`` again.

    Args:
        command: The command to wrap.
        outcome: Dict owned by the caller. ``redo`` stores the result of
            ``execute`` under the ``"ok"`` key and ``undo`` stores the result of
            ``Command.undo`` under ``"undo_ok"``, so the caller can read them
            even after Qt has deleted this object.

    """

    def __init__(self, command: Command, outcome: dict[str, bool]) -> None:
        """
        Initialize with the wrapped command and the caller's outcome dict.

        Args:
            command: The command to wrap.
            outcome: Caller-owned dict that receives the result of ``execute``.

        """
        super().__init__(command.menu_text())
        #: The wrapped command.
        self.command: Command = command
        #: Whether this command is part of an open run of mergeable commands.
        self._run_open: bool = False
        #: Caller-owned dict that receives the results of ``execute`` and ``undo``.
        self._outcome: dict[str, bool] = outcome
        #: Whether the next ``redo`` only restores the index after a failed undo.
        self._skip_next_redo: bool = False

    @property
    def outcome(self) -> dict[str, bool]:
        """
        Get the caller-owned outcome dict.

        Returns:
            The dict holding the latest ``"ok"`` and ``"undo_ok"`` results.

        """
        return self._outcome

    def redo(self) -> None:
        """
        Execute the wrapped command.

        Side Effects:
            Marks this command obsolete when ``execute`` returns ``False``.
            Does nothing when the previous ``undo`` failed.

        """
        if self._skip_next_redo:
            self._skip_next_redo = False
            return
        ok = self.command.execute()
        self._outcome["ok"] = ok
        if not ok:
            self.setObsolete(True)

    def undo(self) -> None:
        """
        Undo the wrapped command.

        Side Effects:
            Stores the result under ``"undo_ok"`` and, on failure, arms a skip of
            the next ``redo``.

        """
        ok = self.command.undo()
        self._outcome["undo_ok"] = ok
        self._skip_next_redo = not ok

    @property
    def run_open(self) -> bool:
        """
        Get whether this command is the open command of a Typed Run.

        Returns:
            ``True`` while later translation edits may merge into this command.

        """
        return self._run_open

    @run_open.setter
    def run_open(self, value: bool) -> None:
        """
        Open or close this command's Typed Run.

        Args:
            value: ``True`` to accept merges, ``False`` to refuse them.

        """
        self._run_open = value

    def id(self) -> int:
        """
        Get the merge id.

        Qt only calls :meth:`mergeWith` when both commands share an id other
        than ``-1``, so every translation edit shares one id whether or not
        its run is open.

        Returns:
            ``1`` for a Modern English translation edit, otherwise ``-1``.

        """
        return 1 if _translation_sentence_id(self.command) is not None else -1

    def mergeWith(self, other: QUndoCommand) -> bool:  # noqa: N802
        """
        Absorb a later translation edit of the same sentence into an open run.

        Args:
            other: The command just pushed onto the stack.

        Side Effects:
            On merge, sets this command's ``after`` to ``other``'s ``after``.
            ``before`` is kept.

        Returns:
            ``True`` when this command's run is open, ``other`` succeeded (is
            not obsolete), and both commands edit the translation of the same
            sentence.

        """
        if (
            not self._run_open
            or not isinstance(other, UndoCommand)
            or other.isObsolete()
        ):
            return False
        sentence_id = _translation_sentence_id(self.command)
        if sentence_id is None or sentence_id != _translation_sentence_id(
            other.command
        ):
            return False
        cast("EditSentenceCommand", self.command).after = cast(
            "EditSentenceCommand", other.command
        ).after
        return True


def _translation_sentence_id(command: Command) -> int | None:
    """
    Get the sentence id of a Modern English translation edit.

    Args:
        command: Any wrapped command.

    Returns:
        The edited sentence's id, or ``None`` when ``command`` is not a
        ``text_modern`` :class:`EditSentenceCommand`.

    """
    if isinstance(command, EditSentenceCommand) and command.field == "text_modern":
        return command.sentence_id
    return None


def push_command(stack: QUndoStack, command: Command) -> bool:
    """
    Wrap ``command`` and push it onto ``stack``.

    The stack takes ownership of the wrapper. If ``execute`` fails, Qt discards
    the wrapper, so the result is read from a dict held here rather than from
    the wrapper.

    Args:
        stack: The stack to push onto.
        command: The command to run and record.

    Side Effects:
        Runs ``command.execute`` and, on success, adds it to ``stack`` and
        then has :func:`maintain_stack` let the other entries follow what
        ``command`` removed or moved.

    Returns:
        ``True`` if ``execute`` succeeded, ``False`` otherwise.

    """
    outcome: dict[str, bool] = {"ok": False}
    stack.push(UndoCommand(command, outcome))
    if outcome["ok"]:
        maintain_stack(stack, command)
    return outcome["ok"]


def undo_step(stack: QUndoStack) -> bool:
    """
    Undo the top of ``stack`` and let the other entries follow.

    Args:
        stack: The stack to move.

    Side Effects:
        Calls ``stack.undo()``. When the command's ``undo`` fails, calls
        ``stack.redo()`` to put the index back without running ``execute``
        again. After a successful undo, has :func:`maintain_stack` walk the
        stack. An entry already marked obsolete is skipped by Qt and dropped;
        nothing is walked for it. Every path ends by settling the stack, so
        no obsolete entry is left next to the index.

    Returns:
        ``True`` only when a command was undone; ``False`` when its ``undo``
        failed or the entry was merely dropped as obsolete.

    """
    entry = stack.command(stack.index() - 1)
    if not isinstance(entry, UndoCommand):
        stack.undo()
        return True
    command, outcome, dropped = entry.command, entry.outcome, entry.isObsolete()
    stack.undo()
    if dropped:
        settle(stack)
        return False
    if not outcome.get("undo_ok", True):
        stack.redo()
        settle(stack)
        return False
    maintain_stack(stack, command)
    return True


def redo_step(stack: QUndoStack) -> bool:
    """
    Redo the next entry on ``stack`` and let the other entries follow.

    Args:
        stack: The stack to move.

    Side Effects:
        Calls ``stack.redo()``. When ``execute`` fails, Qt drops the entry.
        After a successful redo, has :func:`maintain_stack` walk the stack. An
        entry already marked obsolete is skipped by Qt and dropped; nothing is
        walked for it. Every path ends by settling the stack, so no obsolete
        entry is left next to the index.

    Returns:
        ``True`` only when a command was redone; ``False`` when ``execute``
        failed or the entry was merely dropped as obsolete.

    """
    entry = stack.command(stack.index())
    if not isinstance(entry, UndoCommand):
        stack.redo()
        return True
    command, outcome, dropped = entry.command, entry.outcome, entry.isObsolete()
    stack.redo()
    if dropped or not outcome.get("ok", True):
        settle(stack)
        return False
    maintain_stack(stack, command)
    return True

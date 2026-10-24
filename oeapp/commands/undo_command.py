"""Adapter that lets a :class:`Command` live on a ``QUndoStack``."""

from PySide6.QtGui import QUndoCommand, QUndoStack

from .abstract import Command


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

    def id(self) -> int:
        """
        Get the merge id.

        Returns:
            ``1`` while a run is open, otherwise ``-1`` (never merge).

        """
        return 1 if self._run_open else -1

    def mergeWith(self, other: QUndoCommand) -> bool:  # noqa: N802, ARG002
        """
        Decline to merge with another command.

        Args:
            other: The command that would be merged in.

        Returns:
            Always ``False``.

        """
        return False


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
        Runs ``command.execute`` and, on success, adds it to ``stack``.

    Returns:
        ``True`` if ``execute`` succeeded, ``False`` otherwise.

    """
    outcome: dict[str, bool] = {"ok": False}
    stack.push(UndoCommand(command, outcome))
    return outcome["ok"]

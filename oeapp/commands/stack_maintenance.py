"""Keep every stack entry pointed at rows that still exist."""

from PySide6.QtGui import QUndoCommand, QUndoStack

from .abstract import Command, CommandLocators, StackAdjustment


def maintain_stack(stack: QUndoStack, source: Command) -> None:
    """
    Walk ``stack`` after ``source`` ran and let every entry follow its rows.

    Each entry is asked for its :meth:`~Command.locators`. An entry whose
    rows are all in ``source.last_adjustment``'s obsolete sets is marked
    obsolete, unless it is the removal of that sentence. Every other entry
    is told to :meth:`~Command.relocate`, so a token that moved carries its
    sentence locator with it and dead token or idiom ids are dropped.
    Afterwards, whether or not anything was marked this time, the obsolete
    entries next to the stack index are stepped over, which lets Qt delete
    them without running their ``undo`` or ``redo``.

    Args:
        stack: The stack to walk.
        source: The command whose ``execute`` or ``undo`` just returned.

    Side Effects:
        Marks entries obsolete, updates their locator ids, and may move the
        stack index past obsolete entries.

    """
    adjustment = source.last_adjustment
    if not adjustment.is_empty():
        for index in range(stack.count()):
            entry = stack.command(index)
            command = getattr(entry, "command", None)
            if entry is None or entry.isObsolete() or not isinstance(command, Command):
                continue
            if is_orphaned(command, adjustment):
                entry.setObsolete(True)
            else:
                command.relocate(adjustment)
    settle(stack)


def is_orphaned(command: Command, adjustment: StackAdjustment) -> bool:
    """
    Whether ``adjustment`` removed everything ``command`` acts on.

    A command that annotates tokens or idioms is judged by those: it is
    orphaned when every one of them is gone, whatever happened to the
    sentence that held them. A command with only sentence locators is
    orphaned when every sentence it does not itself remove is gone; the
    sentence a removal names is its own to take away, so it never counts
    against it.

    Args:
        command: The stack entry's command.
        adjustment: What the source command removed or moved.

    Returns:
        ``True`` when the command has nothing left to undo or redo.

    """
    locators = command.locators()
    if locators.token_ids or locators.idiom_ids:
        return (
            locators.token_ids <= adjustment.obsolete_token_ids
            and locators.idiom_ids <= adjustment.obsolete_idiom_ids
        )
    kept = {s for s in locators.sentence_ids if not command.is_removal_of(s)}
    return bool(kept) and kept <= adjustment.obsolete_sentence_ids


def settle(stack: QUndoStack) -> None:
    """
    Step the stack index over the obsolete entries next to it.

    Qt deletes an obsolete entry when it is undone or redone and skips the
    entry's own ``undo`` and ``redo``, so this removes dead entries without
    running any command code.

    Args:
        stack: The stack to settle.

    Side Effects:
        Calls ``stack.undo()`` and ``stack.redo()`` on obsolete entries only.

    """
    while stack.index() > 0 and _is_obsolete(stack.command(stack.index() - 1)):
        stack.undo()
    while stack.index() < stack.count() and _is_obsolete(stack.command(stack.index())):
        stack.redo()


def _is_obsolete(entry: QUndoCommand | None) -> bool:
    """
    Whether a stack entry is marked obsolete.

    Args:
        entry: The entry, or ``None`` past the end of the stack.

    Returns:
        ``True`` when the entry exists and is obsolete.

    """
    return entry is not None and entry.isObsolete()


__all__ = [
    "CommandLocators",
    "StackAdjustment",
    "is_orphaned",
    "maintain_stack",
    "settle",
]

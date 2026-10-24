"""Tests for the QUndoCommand wrapper around ``Command``."""

import gc

from oeapp.commands.abstract import Command
from oeapp.commands.undo_command import UndoCommand, push_command
from PySide6.QtGui import QUndoStack


class FailCommand(Command):
    """Command whose ``execute`` always fails."""

    def execute(self) -> bool:
        """Fail."""
        return False

    def undo(self) -> bool:
        """Undo nothing."""
        return True

    def get_description(self) -> str:
        """Describe the command."""
        return "Fail"


class LogCommand(Command):
    """
    Command that records ``execute`` and ``undo`` calls.

    Args:
        log: List that receives ``"redo"`` and ``"undo"`` entries.

    """

    def __init__(self, log: list[str]) -> None:
        """Store the log list."""
        self.log = log

    def execute(self) -> bool:
        """Record a redo."""
        self.log.append("redo")
        return True

    def undo(self) -> bool:
        """Record an undo."""
        self.log.append("undo")
        return True

    def get_description(self) -> str:
        """Describe the command."""
        return "Log"


def test_failed_execute_is_not_kept(qapp):
    stack = QUndoStack()
    assert push_command(stack, FailCommand()) is False
    assert stack.count() == 0
    assert stack.canUndo() is False


def test_stack_owns_the_command_after_the_name_is_dropped(qapp):
    stack = QUndoStack()
    log: list[str] = []
    push_command(stack, LogCommand(log))
    gc.collect()
    stack.undo()
    stack.redo()
    assert log == ["redo", "undo", "redo"]


def test_successful_push_returns_true_and_is_on_stack(qapp):
    stack = QUndoStack()
    assert push_command(stack, LogCommand([])) is True
    assert stack.count() == 1
    assert stack.undoText() == "Log"


def test_id_and_merge_defaults(qapp):
    wrapper = UndoCommand(LogCommand([]), {})
    assert wrapper.id() == -1
    wrapper._run_open = True
    assert wrapper.id() == 1
    assert wrapper.mergeWith(UndoCommand(LogCommand([]), {})) is False

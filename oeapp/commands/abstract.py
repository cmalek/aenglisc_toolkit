"""Command pattern for undo/redo functionality."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class Command(ABC):
    """Base class for undoable commands."""

    @abstractmethod
    def execute(self) -> bool:
        """
        Execute the command.

        Returns:
            True if successful, False otherwise

        """

    @abstractmethod
    def undo(self) -> bool:
        """
        Undo the command.

        Returns:
            True if successful, False otherwise

        """

    @abstractmethod
    def get_description(self) -> str:
        """
        Get human-readable description of the command.

        Returns:
            Description string

        """

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the command needs a full reload of the project structure.

        Returns:
            True if the command needs a full reload, False otherwise

        """
        return False


class CommandManager:
    """Manages undo/redo command stack."""

    def __init__(self, session: "Session", max_commands: int = 50) -> None:
        """
        Initialize command manager.

        Args:
            session: SQLAlchemy session

        Keyword Args:
            max_commands: Maximum number of commands to keep in memory

        """
        #: The SQLAlchemy session.
        self.session = session
        #: The maximum number of commands to keep in memory.
        self.max_commands = max_commands
        #: The undo stack.
        self.undo_stack: list[Command] = []
        #: The redo stack.
        self.redo_stack: list[Command] = []
        #: Whether a command is currently being executed.
        self._executing = False

    def execute(self, command: Command) -> bool:
        """
        Execute a command and add to undo stack.

        Args:
            command: Command to execute

        Returns:
            True if successful, False otherwise

        """
        if self._executing:
            return False

        self._executing = True
        try:
            if command.execute():
                self.undo_stack.append(command)
                # Limit stack size
                if len(self.undo_stack) > self.max_commands:
                    self.undo_stack.pop(0)
                # Clear redo stack when new action performed
                self.redo_stack.clear()
                return True
            return False
        finally:
            self._executing = False

    def undo(self) -> bool:
        """
        Undo last command.

        Returns:
            True if successful, False otherwise

        """
        if not self.undo_stack or self._executing:
            return False

        self._executing = True
        try:
            command = self.undo_stack.pop()
            if command.undo():
                self.redo_stack.append(command)
                # Limit redo stack size
                if len(self.redo_stack) > self.max_commands:
                    self.redo_stack.pop(0)
                return True
            # If undo failed, put command back
            self.undo_stack.append(command)
            return False
        finally:
            self._executing = False

    def redo(self) -> bool:
        """
        Redo last undone command.

        Returns:
            True if successful, False otherwise

        """
        if not self.redo_stack or self._executing:
            return False

        self._executing = True
        try:
            command = self.redo_stack.pop()
            if command.execute():
                self.undo_stack.append(command)
                # Limit stack size
                if len(self.undo_stack) > self.max_commands:
                    self.undo_stack.pop(0)
                return True
            # If redo failed, put command back
            self.redo_stack.append(command)
            return False
        finally:
            self._executing = False

    def can_undo(self) -> bool:
        """
        Check if undo is possible.

        Returns:
            True if undo is available

        """
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """
        Check if redo is possible.

        Returns:
            True if redo is available

        """
        return len(self.redo_stack) > 0

    def clear(self) -> None:
        """Clear all command stacks."""
        self.undo_stack.clear()
        self.redo_stack.clear()

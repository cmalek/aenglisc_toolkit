"""Command pattern for undo/redo functionality."""

from abc import ABC, abstractmethod


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
    def menu_text(self) -> str:
        """
        Get the plain-language name of the command.

        Returns:
            Short action name with no database ids, such as ``Add note``

        """

    def get_description(self) -> str:
        """
        Get human-readable description of the command, for logs.

        Returns:
            The same text as :meth:`menu_text`

        """
        return self.menu_text()

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the command needs a full reload of the project structure.

        Returns:
            True if the command needs a full reload, False otherwise

        """
        return False

"""Command pattern for undo/redo functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class CommandLocators:
    """
    The database rows a command acts on, by id.

    Locators say where a command's work lives *now*. They are not the
    command's undo snapshot: a command's ``before`` state and
    ``display_order_changes`` are never read from here.

    Args:
        sentence_ids: Sentences the command edits, removes, or restores.
        token_ids: Tokens the command annotates.
        idiom_ids: Idioms the command annotates.

    """

    #: Sentences the command edits, removes, or restores.
    sentence_ids: set[int] = field(default_factory=set)
    #: Tokens the command annotates.
    token_ids: set[int] = field(default_factory=set)
    #: Idioms the command annotates.
    idiom_ids: set[int] = field(default_factory=set)


@dataclass
class StackAdjustment:
    """
    What one ``execute`` or ``undo`` did to the rows other commands locate.

    Args:
        obsolete_sentence_ids: Sentences that no longer exist.
        token_sentence: Tokens that moved, mapped to the sentence they now
            belong to. Token ids themselves never change.
        obsolete_token_ids: Tokens that no longer exist.
        obsolete_idiom_ids: Idioms that no longer exist.

    """

    #: Sentences that no longer exist.
    obsolete_sentence_ids: set[int] = field(default_factory=set)
    #: Tokens that moved, mapped to the sentence they now belong to.
    token_sentence: dict[int, int] = field(default_factory=dict)
    #: Tokens that no longer exist.
    obsolete_token_ids: set[int] = field(default_factory=set)
    #: Idioms that no longer exist.
    obsolete_idiom_ids: set[int] = field(default_factory=set)

    def is_empty(self) -> bool:
        """
        Whether this adjustment changes nothing for other commands.

        Returns:
            ``True`` when no row was removed or moved.

        """
        return not (
            self.obsolete_sentence_ids
            or self.token_sentence
            or self.obsolete_token_ids
            or self.obsolete_idiom_ids
        )


class Command(ABC):
    """
    Base class for undoable commands.

    Besides ``execute`` and ``undo``, a command reports where its work lives
    (:meth:`locators`), what its last step removed or moved
    (:attr:`last_adjustment`), and follows rows that another command moved
    (:meth:`relocate`). Subclasses that keep the defaults are never dropped
    from the stack by :func:`~oeapp.commands.stack_maintenance.maintain_stack`.
    """

    #: Adjustment recorded by the most recent ``execute`` or ``undo``; ``None``
    #: until one is recorded.
    _last_adjustment: StackAdjustment | None = None

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

    def locators(self) -> CommandLocators:
        """
        Get the rows this command acts on.

        Returns:
            Empty locators; a command with no locators is never dropped.

        """
        return CommandLocators()

    @property
    def last_adjustment(self) -> StackAdjustment:
        """
        Get what the most recent ``execute`` or ``undo`` removed or moved.

        Returns:
            The recorded adjustment, or an empty one when nothing was recorded.

        """
        if self._last_adjustment is None:
            self._last_adjustment = StackAdjustment()
        return self._last_adjustment

    @last_adjustment.setter
    def last_adjustment(self, adjustment: StackAdjustment) -> None:
        """
        Record what the step that just ran removed or moved.

        Args:
            adjustment: The adjustment for the step that just ran.

        """
        self._last_adjustment = adjustment

    def is_removal_of(self, sentence_id: int) -> bool:  # noqa: ARG002
        """
        Whether this command is the one that removes ``sentence_id``.

        A removal names the sentence it removes, so it must not be dropped
        when that sentence becomes obsolete.

        Args:
            sentence_id: Sentence to check.

        Returns:
            ``False``; only sentence removals override this.

        """
        return False

    def relocate(self, adjustment: StackAdjustment) -> None:  # noqa: B027
        """
        Follow rows that another command moved or removed.

        This is an optional hook, not an abstract method: a command with no
        locators has nothing to follow.

        Args:
            adjustment: What that command removed or moved.

        Side Effects:
            Subclasses update their own locator ids. Undo snapshots are left
            alone. The default does nothing.

        """

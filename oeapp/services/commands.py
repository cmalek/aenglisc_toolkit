"""Command pattern for undo/redo functionality."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from oeapp.models.annotation import Annotation
from oeapp.models.sentence import Sentence

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


@dataclass
class AnnotateTokenCommand(Command):
    """Command for annotating a token."""

    #: The SQLAlchemy session.
    session: Session
    #: The token ID.
    token_id: int
    #: The before state of the annotation.
    before: dict[str, Any]
    #: The after state of the annotation.
    after: dict[str, Any]

    def _update_annotation(self, annotation: Annotation, state: dict[str, Any]) -> None:
        """
        Update an annotation with a new state.

        This method updates an annotation with a new state.  The state is a
        dictionary of key-value pairs.  The keys are the fields of the annotation
        and the values are the new values for the fields.

        Args:
            annotation: Annotation to update
            state: New state of the annotation

        """
        annotation.pos = state.get("pos")
        annotation.gender = state.get("gender")
        annotation.number = state.get("number")
        annotation.case = state.get("case")
        annotation.declension = state.get("declension")
        annotation.pronoun_type = state.get("pronoun_type")
        annotation.verb_class = state.get("verb_class")
        annotation.verb_tense = state.get("verb_tense")
        annotation.verb_person = state.get("verb_person")
        annotation.verb_mood = state.get("verb_mood")
        annotation.verb_aspect = state.get("verb_aspect")
        annotation.verb_form = state.get("verb_form")
        annotation.prep_case = state.get("prep_case")
        annotation.uncertain = state.get("uncertain", False)
        annotation.alternatives_json = state.get("alternatives_json")
        annotation.confidence = state.get("confidence")
        self.session.add(annotation)
        self.session.commit()

    def execute(self) -> bool:
        """
        Execute annotation update.

        Returns:
            True if successful

        """
        annotation = self.session.get(Annotation, self.token_id)
        if annotation is None:
            # Create annotation if it doesn't exist
            annotation = Annotation(token_id=self.token_id)
            self.session.add(annotation)
            self.session.flush()
        self._update_annotation(annotation, self.after)
        return True

    def undo(self) -> bool:
        """
        Undo annotation update.

        Returns:
            True if successful

        """
        annotation = self.session.get(Annotation, self.token_id)
        if annotation is None:
            return False
        self._update_annotation(annotation, self.before)
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Annotate token {self.token_id}"


@dataclass
class EditSentenceCommand(Command):
    """Command for editing sentence text or translation."""

    #: The SQLAlchemy session.
    session: Session
    #: The sentence ID.
    sentence_id: int
    #: The field to edit.
    field: Literal["text_oe", "text_modern"]
    #: The before state of the sentence.
    before: str
    #: The after state of the sentence.
    after: str

    def execute(self) -> bool:
        """
        Execute sentence edit.

        - If the field is "text_oe", update the sentence text, and re-tokenize
          the sentence, updating the tokens in the sentence.
        - If the field is "text_modern", update the sentence translation.

        Returns:
            True if successful

        """
        sentence = self.session.get(Sentence, self.sentence_id)
        if sentence is None:
            return False

        if self.field == "text_oe":
            sentence.update(self.session, self.after)
        elif self.field == "text_modern":
            sentence.text_modern = self.after
            self.session.add(sentence)
            self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo sentence edit.

        Returns:
            True if successful, False otherwise

        """
        sentence = self.session.get(Sentence, self.sentence_id)
        if sentence is None:
            return False

        if self.field == "text_oe":
            sentence.update(self.session, self.before)
        elif self.field == "text_modern":
            sentence.text_modern = self.before
            self.session.add(sentence)
            self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Edit sentence {self.sentence_id} {self.field}"


class CommandManager:
    """Manages undo/redo command stack."""

    def __init__(self, session: Session, max_commands: int = 50) -> None:
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

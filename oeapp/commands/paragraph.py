"""Paragraph related commands."""

from dataclasses import dataclass, field
from typing import Any

from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence

from .abstract import Command


@dataclass
class ToggleParagraphStartCommand(SessionMixin, Command):
    """Command for toggling paragraph start flag on a sentence."""

    #: The sentence ID.
    sentence_id: int
    #: Before state: is_paragraph_start value
    before_is_paragraph_start: bool = False
    #: After state: is_paragraph_start value
    after_is_paragraph_start: bool = False
    #: Before state: paragraph and sentence numbers for all affected sentences
    before_numbers: list[dict[str, Any]] = field(default_factory=list)
    #: After state: paragraph and sentence numbers for all affected sentences
    after_numbers: list[dict[str, Any]] = field(default_factory=list)

    def execute(self) -> bool:
        """
        Execute toggle paragraph start operation.

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        sentence = Sentence.get(self.sentence_id)
        if sentence is None:
            return False

        # Store before state
        self.before_is_paragraph_start = sentence.is_paragraph_start
        self.after_is_paragraph_start = not sentence.is_paragraph_start

        # Get all sentences in the project, ordered by display_order
        all_sentences = Sentence.list(sentence.project_id)

        # Store before paragraph and sentence numbers
        self.before_numbers = [
            {
                "id": s.id,
                "paragraph_number": s.paragraph_number,
                "sentence_number_in_paragraph": s.sentence_number_in_paragraph,
                "is_paragraph_start": s.is_paragraph_start,
            }
            for s in all_sentences
        ]

        # Toggle the flag
        sentence.is_paragraph_start = self.after_is_paragraph_start
        session.add(sentence)
        session.flush()

        # Recalculate paragraph and sentence numbers for all sentences
        Sentence.recalculate_project_structure(sentence.project_id)

        # Re-fetch all sentences to store after state
        all_sentences = Sentence.list(sentence.project_id)

        # Store after paragraph and sentence numbers
        self.after_numbers = [
            {
                "id": s.id,
                "paragraph_number": s.paragraph_number,
                "sentence_number_in_paragraph": s.sentence_number_in_paragraph,
                "is_paragraph_start": s.is_paragraph_start,
            }
            for s in all_sentences
        ]

        session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo toggle paragraph start operation.

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        sentence = Sentence.get(self.sentence_id)
        if sentence is None:
            return False

        # Restore before state
        sentence.is_paragraph_start = self.before_is_paragraph_start
        session.add(sentence)
        session.flush()

        # Recalculate project structure after restoration
        Sentence.recalculate_project_structure(sentence.project_id)

        session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        action = "Start paragraph" if self.after_is_paragraph_start else "End paragraph"
        return f"{action} for sentence {self.sentence_id}"

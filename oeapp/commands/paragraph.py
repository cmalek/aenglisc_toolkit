"""Paragraph related commands."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from oeapp.models.sentence import Sentence

from .abstract import Command

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class ToggleParagraphStartCommand(Command):
    """Command for toggling paragraph start flag on a sentence."""

    #: The SQLAlchemy session.
    session: Session
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
        sentence = Sentence.get(self.session, self.sentence_id)
        if sentence is None:
            return False

        # Store before state
        self.before_is_paragraph_start = sentence.is_paragraph_start
        self.after_is_paragraph_start = not sentence.is_paragraph_start

        # Get all sentences in the project, ordered by display_order
        all_sentences = Sentence.list(self.session, sentence.project_id)

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
        self.session.add(sentence)
        self.session.flush()

        # Recalculate paragraph and sentence numbers for all sentences
        self._recalculate_paragraph_numbers(all_sentences)

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

        self.session.commit()
        return True

    def _recalculate_paragraph_numbers(self, sentences: list[Sentence]) -> None:
        """
        Recalculate paragraph and sentence numbers for all sentences.

        Args:
            sentences: List of all sentences in project, ordered by display_order

        """
        if not sentences:
            return

        paragraph_number = 1
        sentence_number_in_paragraph = 0

        for sentence in sentences:
            if sentence.is_paragraph_start:
                if sentence_number_in_paragraph > 0:
                    # Starting a new paragraph (but not the first sentence)
                    paragraph_number += 1
                sentence_number_in_paragraph = 1
            else:
                sentence_number_in_paragraph += 1

            sentence.paragraph_number = paragraph_number
            sentence.sentence_number_in_paragraph = sentence_number_in_paragraph
            self.session.add(sentence)

    def undo(self) -> bool:
        """
        Undo toggle paragraph start operation.

        Returns:
            True if successful, False otherwise

        """
        sentence = Sentence.get(self.session, self.sentence_id)
        if sentence is None:
            return False

        # Restore before state
        sentence.is_paragraph_start = self.before_is_paragraph_start
        self.session.add(sentence)

        # Restore paragraph and sentence numbers
        for before_data in self.before_numbers:
            s = Sentence.get(self.session, before_data["id"])
            if s:
                s.paragraph_number = before_data["paragraph_number"]
                s.sentence_number_in_paragraph = before_data[
                    "sentence_number_in_paragraph"
                ]
                s.is_paragraph_start = before_data["is_paragraph_start"]
                self.session.add(s)

        self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        action = "Start paragraph" if self.after_is_paragraph_start else "End paragraph"
        return f"{action} for sentence {self.sentence_id}"

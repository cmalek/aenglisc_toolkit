"""Paragraph related commands."""

from dataclasses import dataclass, field
from typing import Any

from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence
from oeapp.models.paragraph import Paragraph

from .abstract import Command


@dataclass
class SplitParagraphCommand(SessionMixin, Command):
    """Command for splitting a paragraph at a specific sentence."""

    #: The sentence ID that will start the new paragraph.
    sentence_id: int
    #: The new paragraph ID (stored for undo).
    new_paragraph_id: int | None = None
    #: The original paragraph ID (stored for undo).
    original_paragraph_id: int | None = None
    #: List of sentence IDs that were moved to the new paragraph.
    moved_sentence_ids: list[int] = field(default_factory=list)

    @property
    def needs_full_reload(self) -> bool:
        return True

    def execute(self) -> bool:
        """
        Execute split paragraph operation.
        """
        session = self._get_session()
        sentence = session.get(Sentence, self.sentence_id)
        if sentence is None or sentence.paragraph_id is None:
            return False

        original_paragraph = session.get(Paragraph, sentence.paragraph_id)
        if not original_paragraph:
            return False
        
        self.original_paragraph_id = original_paragraph.id
        section_id = original_paragraph.section_id

        # Get all sentences in the original paragraph, ordered by display_order
        # Use sorted() to ensure correct order
        sentences = sorted(original_paragraph.sentences, key=lambda s: s.display_order)
        
        # Find the index of the sentence to split at
        split_index = -1
        for i, s in enumerate(sentences):
            if s.id == self.sentence_id:
                split_index = i
                break
        
        if split_index <= 0:
            # Not found or already at start
            return False

        # Sentences to move
        sentences_to_move = sentences[split_index:]
        self.moved_sentence_ids = [s.id for s in sentences_to_move]

        # Create new paragraph
        new_paragraph = Paragraph(section_id=section_id, order=original_paragraph.order + 1)
        session.add(new_paragraph)
        session.flush()
        self.new_paragraph_id = new_paragraph.id

        # Shift subsequent paragraphs in the same section
        from sqlalchemy import select
        subsequent_paragraphs = session.scalars(
            select(Paragraph)
            .where(Paragraph.section_id == section_id, Paragraph.order > original_paragraph.order, Paragraph.id != self.new_paragraph_id)
        ).all()
        for p in subsequent_paragraphs:
            p.order += 1

        # Move sentences to new paragraph
        for s in sentences_to_move:
            s.paragraph_id = new_paragraph.id
        
        session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo split paragraph operation.
        """
        session = self._get_session()
        if not self.new_paragraph_id or not self.original_paragraph_id:
            return False

        # Re-fetch new_paragraph from session
        new_paragraph = session.get(Paragraph, self.new_paragraph_id)
        if not new_paragraph:
            return False

        # Move sentences back to original paragraph
        for s_id in self.moved_sentence_ids:
            s = session.get(Sentence, s_id)
            if s:
                s.paragraph_id = self.original_paragraph_id
                session.add(s)
        
        # Flush moves before deleting paragraph
        session.flush()
        
        section_id = new_paragraph.section_id
        order_to_remove = new_paragraph.order

        # Delete the new paragraph
        session.delete(new_paragraph)

        # Shift subsequent paragraphs back
        from sqlalchemy import select
        subsequent_paragraphs = session.scalars(
            select(Paragraph)
            .where(Paragraph.section_id == section_id, Paragraph.order > order_to_remove)
        ).all()
        for p in subsequent_paragraphs:
            p.order -= 1

        session.commit()
        return True

    def get_description(self) -> str:
        return f"Split paragraph at sentence {self.sentence_id}"


@dataclass
class MergeParagraphCommand(SessionMixin, Command):
    """Command for merging a paragraph with the previous one."""

    #: The sentence ID that is currently the start of a paragraph.
    sentence_id: int
    #: The paragraph ID that was removed.
    removed_paragraph_id: int | None = None
    #: The original paragraph ID sentences were moved to.
    target_paragraph_id: int | None = None
    #: List of sentence IDs that were moved.
    moved_sentence_ids: list[int] = field(default_factory=list)
    #: Original order of the removed paragraph.
    original_order: int | None = None

    @property
    def needs_full_reload(self) -> bool:
        return True

    def execute(self) -> bool:
        """
        Execute merge paragraph operation.
        """
        session = self._get_session()
        sentence = Sentence.get(self.sentence_id)
        if sentence is None or sentence.paragraph_id is None:
            return False

        current_paragraph = Paragraph.get(sentence.paragraph_id)
        if not current_paragraph or current_paragraph.order == 1:
            # Cannot merge first paragraph of section
            return False
        
        self.removed_paragraph_id = current_paragraph.id
        self.original_order = current_paragraph.order
        section_id = current_paragraph.section_id

        # Find previous paragraph in the same section
        from sqlalchemy import select
        prev_paragraph = session.scalar(
            select(Paragraph)
            .where(Paragraph.section_id == section_id, Paragraph.order == current_paragraph.order - 1)
        )
        if not prev_paragraph:
            return False
        
        self.target_paragraph_id = prev_paragraph.id

        # Move all sentences from current to previous paragraph
        sentences_to_move = list(current_paragraph.sentences)
        self.moved_sentence_ids = [s.id for s in sentences_to_move]
        for s in sentences_to_move:
            s.paragraph_id = prev_paragraph.id
        
        # Delete current paragraph
        session.delete(current_paragraph)
        session.flush()

        # Shift subsequent paragraphs back
        subsequent_paragraphs = session.scalars(
            select(Paragraph)
            .where(Paragraph.section_id == section_id, Paragraph.order > self.original_order)
        ).all()
        for p in subsequent_paragraphs:
            p.order -= 1

        session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo merge paragraph operation.
        """
        session = self._get_session()
        if not self.removed_paragraph_id or not self.target_paragraph_id or self.original_order is None:
            return False

        target_paragraph = Paragraph.get(self.target_paragraph_id)
        if not target_paragraph:
            return False
        
        section_id = target_paragraph.section_id

        # Shift subsequent paragraphs forward
        from sqlalchemy import select
        subsequent_paragraphs = session.scalars(
            select(Paragraph)
            .where(Paragraph.section_id == section_id, Paragraph.order >= self.original_order)
        ).all()
        for p in subsequent_paragraphs:
            p.order += 1

        # Re-create the removed paragraph
        new_p = Paragraph(id=self.removed_paragraph_id, section_id=section_id, order=self.original_order)
        session.add(new_p)
        session.flush()

        # Move sentences back
        for s_id in self.moved_sentence_ids:
            s = Sentence.get(s_id)
            if s:
                s.paragraph_id = new_p.id
        
        session.commit()
        return True

    def get_description(self) -> str:
        return f"Merge paragraph at sentence {self.sentence_id} with previous"

"""Paragraph related commands."""

from dataclasses import dataclass, field

from oeapp.models.mixins import SessionMixin
from oeapp.models.paragraph import Paragraph
from oeapp.models.sentence import Sentence

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
        """
        Needs full reload.

        Returns:
            The computed value.

        """
        return True

    def execute(self) -> bool:
        """
        Execute split paragraph operation.

        Returns:
            The computed value.

        """
        session = self._get_session()
        sentence = Sentence.get(self.sentence_id)
        if sentence is None or sentence.paragraph_id is None:
            return False

        if sentence is None or sentence.paragraph_id is None:
            return False

        original_paragraph = Paragraph.get(sentence.paragraph_id)
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
        new_paragraph = Paragraph(
            section_id=section_id, order=original_paragraph.order + 1
        )
        new_paragraph.save(commit=False)
        self.new_paragraph_id = new_paragraph.id

        # Shift subsequent paragraphs in the same section
        subsequent_paragraphs = Paragraph.get_paragraphs_after(
            section_id=section_id,
            order=original_paragraph.order,
            exclude_paragraph_id=self.new_paragraph_id,
        )
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

        Returns:
            The computed value.

        """
        session = self._get_session()
        if not self.new_paragraph_id or not self.original_paragraph_id:
            return False

        # Re-fetch new_paragraph from session
        new_paragraph = Paragraph.get(self.new_paragraph_id)
        if not new_paragraph:
            return False

        # Move sentences back to original paragraph
        for s_id in self.moved_sentence_ids:
            s = Sentence.get(s_id)
            if s:
                s.paragraph_id = self.original_paragraph_id
                s.save(commit=False)

        # The last save did a flush, so we can now delete the paragraph
        section_id = new_paragraph.section_id
        order_to_remove = new_paragraph.order

        # Delete the new paragraph
        new_paragraph.delete(commit=False)

        # Shift subsequent paragraphs back
        subsequent_paragraphs = Paragraph.get_paragraphs_after(
            section_id=section_id,
            order=order_to_remove,
        )
        for p in subsequent_paragraphs:
            p.order -= 1
            p.save(commit=False)

        session.commit()
        return True

    def get_description(self) -> str:
        """
        Get description.

        Returns:
            The computed value.

        """
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
        """
        Needs full reload.

        Returns:
            The computed value.

        """
        return True

    def execute(self) -> bool:
        """
        Execute merge paragraph operation.

        Returns:
            The computed value.

        """
        session = self._get_session()
        sentence = Sentence.get(self.sentence_id)
        if sentence is None or sentence.paragraph_id is None:
            return False

        current_paragraph = Paragraph.get(sentence.paragraph_id)
        if not current_paragraph or current_paragraph.order == 1:
            # Cannot merge first paragraph of section
            return False

        first_sentence = min(
            current_paragraph.sentences,
            key=lambda current_sentence: current_sentence.display_order,
            default=None,
        )
        if first_sentence is None or first_sentence.id != sentence.id:
            return False

        self.removed_paragraph_id = current_paragraph.id
        self.original_order = current_paragraph.order
        section_id = current_paragraph.section_id

        # Find previous paragraph in the same section
        prev_paragraph = Paragraph.previous_paragraph(
            section_id=section_id, order=current_paragraph.order
        )
        if not prev_paragraph:
            return False

        self.target_paragraph_id = prev_paragraph.id

        # Move all sentences from current to previous paragraph
        sentences_to_move = list(current_paragraph.sentences)
        self.moved_sentence_ids = [s.id for s in sentences_to_move]
        for s in sentences_to_move:
            s.paragraph_id = prev_paragraph.id
            s.save(commit=False)

        session.flush()
        session.refresh(current_paragraph, attribute_names=["sentences"])

        # Delete current paragraph
        current_paragraph.delete(commit=False)

        # Shift subsequent paragraphs back
        subsequent_paragraphs = Paragraph.get_paragraphs_after(
            section_id=section_id,
            order=self.original_order,
        )
        for p in subsequent_paragraphs:
            p.order -= 1
            p.save(commit=False)

        session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo merge paragraph operation.

        Returns:
            The computed value.

        """
        session = self._get_session()
        if (
            not self.removed_paragraph_id
            or not self.target_paragraph_id
            or self.original_order is None
        ):
            return False

        target_paragraph = Paragraph.get(self.target_paragraph_id)
        if not target_paragraph:
            return False

        section_id = target_paragraph.section_id

        # Shift subsequent paragraphs forward
        subsequent_paragraphs = Paragraph.get_paragraphs_after(
            section_id=section_id,
            order=self.original_order,
        )
        for p in subsequent_paragraphs:
            p.order += 1
            p.save(commit=False)

        # Re-create the removed paragraph
        new_p = Paragraph(
            id=self.removed_paragraph_id,
            section_id=section_id,
            order=self.original_order,
        )
        new_p.save(commit=False)

        # Move sentences back
        for s_id in self.moved_sentence_ids:
            s = Sentence.get(s_id)
            if s:
                s.paragraph_id = new_p.id
                s.save(commit=False)

        session.commit()
        return True

    def get_description(self) -> str:
        """
        Get description.

        Returns:
            The computed value.

        """
        return f"Merge paragraph at sentence {self.sentence_id} with previous"

"""Sentence related commands."""

from dataclasses import dataclass, field
from typing import Any, Literal

from sqlalchemy import select

from oeapp.models.annotation import Annotation
from oeapp.models.mixins import SessionMixin
from oeapp.models.note import Note
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token

from .abstract import Command


@dataclass
class EditSentenceCommand(SessionMixin, Command):
    """Command for editing sentence text or translation."""

    #: The sentence ID.
    sentence_id: int
    #: The field to edit.
    field: Literal["text_oe", "text_modern"]
    #: The before state of the sentence.
    before: str
    #: The after state of the sentence.
    after: str
    #: Messages from the update (e.g. deleted idioms)
    messages: list[str] = field(default_factory=list)

    def execute(self) -> bool:
        """
        Execute sentence edit.

        - If the field is "text_oe", update the sentence text, and re-tokenize
          the sentence, updating the tokens in the sentence.
        - If the field is "text_modern", update the sentence translation.

        Returns:
            True if successful

        """
        sentence = Sentence.get(self.sentence_id)
        if sentence is None:
            return False

        if self.field == "text_oe":
            self.messages = sentence.update(self.after)
        elif self.field == "text_modern":
            sentence.text_modern = self.after
            sentence.save()
        return True

    def undo(self) -> bool:
        """
        Undo sentence edit.

        Returns:
            True if successful, False otherwise

        """
        sentence = Sentence.get(self.sentence_id)
        if sentence is None:
            return False

        if self.field == "text_oe":
            sentence.update(self.before)
        elif self.field == "text_modern":
            sentence.text_modern = self.before
            sentence.save()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Edit sentence {self.sentence_id} {self.field}"

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the command needs a full reload of the project structure after
        execution.

        Returns:
            True if the command needs a full reload, False otherwise

        """
        return True


@dataclass
class MergeSentenceCommand(SessionMixin, Command):
    """Command for merging a sentence with the next sentence."""

    #: The current sentence ID.
    current_sentence_id: int
    #: The next sentence ID.
    next_sentence_id: int
    #: Before state: current sentence text_oe
    before_text_oe: str
    #: Before state: current sentence text_modern
    before_text_modern: str | None
    #: Before state: next sentence data for restoration
    next_sentence_data: dict[str, Any] = field(default_factory=dict)
    #: Before state: tokens from next sentence (token_id, sentence_id,
    #: order_index, surface)
    next_sentence_tokens: list[dict[str, Any]] = field(default_factory=list)
    #: Before state: notes from next sentence
    next_sentence_notes: list[dict[str, Any]] = field(default_factory=list)
    #: Before state: idioms from next sentence
    next_sentence_idioms: list[dict[str, Any]] = field(default_factory=list)
    #: Before state: display order changes (sentence_id, old_order, new_order)
    display_order_changes: list[tuple[int, int, int]] = field(default_factory=list)

    def execute(self) -> bool:
        """
        Execute merge operation.

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        current_sentence = Sentence.get(self.current_sentence_id)
        next_sentence = Sentence.get(self.next_sentence_id)

        if current_sentence is None or next_sentence is None:
            return False

        # Store next sentence data for undo
        self.next_sentence_data = {
            "id": next_sentence.id,
            "project_id": next_sentence.project_id,
            "display_order": next_sentence.display_order,
            "text_oe": next_sentence.text_oe,
            "text_modern": next_sentence.text_modern,
        }

        # Store tokens from next sentence (before moving them)
        next_tokens = list(next_sentence.tokens)
        self.next_sentence_tokens = [
            {
                "id": token.id,
                "sentence_id": token.sentence_id,
                "order_index": token.order_index,
                "surface": token.surface,
                "lemma": token.lemma,
            }
            for token in next_tokens
        ]

        # Store notes from next sentence
        next_notes = list(next_sentence.notes)
        self.next_sentence_notes = [
            {
                "id": note.id,
                "sentence_id": note.sentence_id,
                "start_token": note.start_token,
                "end_token": note.end_token,
                "note_text_md": note.note_text_md,
                "note_type": note.note_type,
            }
            for note in next_notes
        ]

        # Store idioms from next sentence
        self.next_sentence_idioms = [
            {
                "id": idiom.id,
                "sentence_id": idiom.sentence_id,
                "start_token_id": idiom.start_token_id,
                "end_token_id": idiom.end_token_id,
            }
            for idiom in next_sentence.idioms
        ]

        # Get current sentence token count
        current_token_count = len(current_sentence.tokens)

        # Move all tokens from next sentence to current sentence
        # CRITICAL: Update sentence_id and order_index, but keep token IDs the same
        # This preserves annotations which are linked by token_id
        for idx, token in enumerate(next_tokens):
            token.sentence_id = current_sentence.id
            token.order_index = current_token_count + idx
            session.add(token)

        session.flush()

        # Move all notes from next sentence to current sentence
        for note in next_notes:
            note.sentence_id = current_sentence.id
            session.add(note)

        # Move all idioms from next sentence to current sentence
        for idiom in next_sentence.idioms:
            idiom.sentence_id = current_sentence.id
            session.add(idiom)

        # Merge texts
        merged_text_oe = current_sentence.text_oe + " " + next_sentence.text_oe
        current_modern = current_sentence.text_modern or ""
        next_modern = next_sentence.text_modern or ""
        merged_text_modern = (current_modern + " " + next_modern).strip() or None

        # Update current sentence text (this will re-tokenize and match existing tokens)
        current_sentence.update(merged_text_oe)
        current_sentence.text_modern = merged_text_modern
        session.add(current_sentence)

        # Store next sentence's display_order before deletion
        next_display_order = next_sentence.display_order
        next_project_id = next_sentence.project_id

        # Delete next sentence FIRST to avoid unique constraint violation
        # when updating display_order of subsequent sentences
        next_sentence.delete(commit=False)

        # Update display_order for all subsequent sentences
        # Query using stored values since next_sentence is now deleted
        subsequent_sentences = Sentence.subsequent_sentences(
            next_project_id, next_display_order
        )
        for sentence in subsequent_sentences:
            old_order = sentence.display_order
            sentence.display_order -= 1
            self.display_order_changes.append(
                (sentence.id, old_order, sentence.display_order)
            )
            session.add(sentence)

        session.commit()

        # Recalculate project structure after merge
        Sentence.recalculate_project_structure(next_project_id)

        return True

    def undo(self) -> bool:
        """
        Undo merge operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order) and (project_id, paragraph_number,
        sentence_number_in_paragraph).

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        current_sentence = Sentence.get(self.current_sentence_id)
        if current_sentence is None:
            return False

        # CRITICAL: Restore display_order for subsequent sentences FIRST
        # This must happen before recreating the next sentence to avoid
        # unique constraint violations
        Sentence.restore_display_orders(self.display_order_changes)

        # Now recreate next sentence (will get a new ID, which is fine)
        # Use temporary paragraph/sentence numbers to avoid immediate conflicts
        next_sentence = Sentence(
            project_id=self.next_sentence_data["project_id"],
            display_order=self.next_sentence_data["display_order"],
            paragraph_number=-1,
            sentence_number_in_paragraph=-(self.next_sentence_data["display_order"] + 1000000),
            text_oe=self.next_sentence_data["text_oe"],
            text_modern=self.next_sentence_data["text_modern"],
        )
        session.add(next_sentence)
        session.flush()  # Get the new ID

        # Restore tokens to next sentence with original order_index
        # CRITICAL: Do this BEFORE updating current sentence text
        for token_data in self.next_sentence_tokens:
            token = Token.get(token_data["id"])
            if token:
                token.sentence_id = next_sentence.id  # Use the new sentence ID
                token.order_index = token_data["order_index"]
                session.add(token)

        session.flush()  # Ensure tokens are moved before updating current sentence

        # Now restore current sentence texts and update (re-tokenize)
        # This will only affect tokens that belong to current sentence
        current_sentence.text_oe = self.before_text_oe
        current_sentence.text_modern = self.before_text_modern
        current_sentence.update(self.before_text_oe)
        session.add(current_sentence)

        # Restore notes to next sentence
        for note_data in self.next_sentence_notes:
            note = Note.get(note_data["id"])
            if note:
                note.sentence_id = next_sentence.id  # Use the new sentence ID
                note.save()

        # Restore idioms to next sentence
        from oeapp.models.idiom import Idiom
        for idiom_data in self.next_sentence_idioms:
            idiom = Idiom.get(idiom_data["id"])
            if idiom:
                idiom.sentence_id = next_sentence.id
                idiom.save()

        # Recalculate project structure after undo
        Sentence.recalculate_project_structure(self.next_sentence_data["project_id"])

        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Merge sentence {self.current_sentence_id} with {self.next_sentence_id}"

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the command needs a full reload of the project structure after
        execution.

        Returns:
            True if the command needs a full reload, False otherwise

        """
        return True


@dataclass
class AddSentenceCommand(SessionMixin, Command):
    """Command for adding a new sentence before or after an existing sentence."""

    #: The project ID.
    project_id: int
    #: The reference sentence ID (sentence to insert before/after).
    reference_sentence_id: int
    #: The position relative to reference sentence.
    position: Literal["before", "after"]
    #: The new sentence ID (set after execution).
    new_sentence_id: int | None = None
    #: Display order changes (sentence_id, old_order, new_order).
    display_order_changes: list[tuple[int, int, int]] = field(default_factory=list)
    #: Whether the reference sentence was a paragraph start before being moved.
    reference_was_paragraph_start: bool | None = None

    def execute(self) -> bool:
        """
        Execute add sentence operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order) and (project_id, paragraph_number,
        sentence_number_in_paragraph).

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        reference_sentence = Sentence.get(self.reference_sentence_id)
        if reference_sentence is None:
            return False

        # Calculate target display_order
        if self.position == "before":
            target_order = reference_sentence.display_order
        else:  # "after"
            target_order = reference_sentence.display_order + 1

        # Get all sentences that need display_order updates
        if self.position == "before":
            # For "before", we need sentences with display_order >= target_order
            # Query sentences with display_order >= target_order
            affected_sentences = list(
                session.scalars(
                    select(Sentence)
                    .where(
                        Sentence.project_id == self.project_id,
                        Sentence.display_order >= target_order,
                    )
                    .order_by(Sentence.display_order.desc())
                ).all()
            )
        else:  # "after"
            # For "after", we need sentences with display_order > reference_order
            affected_sentences = Sentence.subsequent_sentences(
                self.project_id, reference_sentence.display_order
            )
            # Sort descending for processing
            affected_sentences = sorted(
                affected_sentences, key=lambda s: s.display_order, reverse=True
            )

        # Phase 1: Update display_orders safely
        if affected_sentences:
            self.display_order_changes = Sentence.renumber_sentences(
                affected_sentences,
                order_function=lambda s: s.display_order + 1,
            )

        # Handle is_paragraph_start for "before" position
        new_is_paragraph_start = False
        if self.position == "before":
            self.reference_was_paragraph_start = reference_sentence.is_paragraph_start
            if self.reference_was_paragraph_start:
                new_is_paragraph_start = True
                reference_sentence.is_paragraph_start = False
                session.add(reference_sentence)
        else:
            self.reference_was_paragraph_start = reference_sentence.is_paragraph_start

        # Create new sentence with temporary negative paragraph/sentence numbers
        # to avoid UNIQUE constraint violations before full recalculation.
        new_sentence = Sentence.create(
            project_id=self.project_id,
            display_order=target_order,
            text_oe="",
            is_paragraph_start=new_is_paragraph_start,
            paragraph_number=-1,
            # Use very large negative number to avoid conflicts with other temp sentences
            sentence_number_in_paragraph=-(target_order + 1000000),
        )
        self.new_sentence_id = new_sentence.id

        # Phase 2: Recalculate all paragraph and sentence numbers in the project
        Sentence.recalculate_project_structure(self.project_id)

        return True

    def undo(self) -> bool:
        """
        Undo add sentence operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order) and (project_id, paragraph_number,
        sentence_number_in_paragraph).

        Returns:
            True if successful, False otherwise

        """
        if self.new_sentence_id is None:
            return False

        # Delete the new sentence first
        new_sentence = Sentence.get(self.new_sentence_id)
        if new_sentence:
            new_sentence.delete()

        # Restore reference sentence paragraph start status
        if self.reference_was_paragraph_start is not None:
            reference_sentence = Sentence.get(self.reference_sentence_id)
            if reference_sentence:
                reference_sentence.is_paragraph_start = self.reference_was_paragraph_start
                session = self._get_session()
                session.add(reference_sentence)

        # Restore display_order using two-phase approach
        Sentence.restore_display_orders(self.display_order_changes)

        # Recalculate project structure after restoration
        Sentence.recalculate_project_structure(self.project_id)
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        position_str = "before" if self.position == "before" else "after"
        return f"Add sentence {position_str} sentence {self.reference_sentence_id}"


@dataclass
class DeleteSentenceCommand(SessionMixin, Command):
    """Command for deleting a sentence."""

    #: The sentence ID to delete.
    sentence_id: int
    #: Before state: sentence data for restoration
    sentence_data: dict[str, Any] = field(default_factory=dict)
    #: Before state: tokens from sentence
    sentence_tokens: list[dict[str, Any]] = field(default_factory=list)
    #: Before state: notes from sentence
    sentence_notes: list[dict[str, Any]] = field(default_factory=list)
    #: Before state: display order changes (sentence_id, old_order, new_order)
    display_order_changes: list[tuple[int, int, int]] = field(default_factory=list)
    #: Before state: idioms from sentence
    sentence_idioms: list[dict[str, Any]] = field(default_factory=list)

    def execute(self) -> bool:
        """
        Execute delete operation.

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        sentence = Sentence.get(self.sentence_id)
        if sentence is None:
            return False

        # Store sentence data for undo
        self.sentence_data = {
            "id": sentence.id,
            "project_id": sentence.project_id,
            "display_order": sentence.display_order,
            "text_oe": sentence.text_oe,
            "text_modern": sentence.text_modern,
        }

        # Store tokens from sentence (before deletion)
        sentence_tokens = list(sentence.tokens)
        self.sentence_tokens = [
            {
                "id": token.id,
                "sentence_id": token.sentence_id,
                "order_index": token.order_index,
                "surface": token.surface,
                "lemma": token.lemma,
                # Store annotation data by order_index (since token IDs will change)
                "annotation": token.annotation.to_json() if token.annotation else None,
            }
            for token in sentence_tokens
        ]

        # Store notes from sentence (store by order_index instead of token_id)
        sentence_notes = list(sentence.notes)
        self.sentence_notes = []
        for note in sentence_notes:
            # Find order_index for start and end tokens
            start_order = None
            end_order = None
            for token in sentence_tokens:
                if token.id == note.start_token:
                    start_order = token.order_index
                if token.id == note.end_token:
                    end_order = token.order_index
            self.sentence_notes.append(
                {
                    "id": note.id,
                    "sentence_id": note.sentence_id,
                    "start_token_order_index": start_order,
                    "end_token_order_index": end_order,
                    "note_text_md": note.note_text_md,
                    "note_type": note.note_type,
                }
            )

        # Store idioms from sentence
        self.sentence_idioms = []
        for idiom in sentence.idioms:
            self.sentence_idioms.append({
                "start_token_order_index": idiom.start_token.order_index,
                "end_token_order_index": idiom.end_token.order_index,
                "annotation": idiom.annotation.to_json() if idiom.annotation else None,
            })

        # Store sentence's display_order before deletion
        deleted_display_order = sentence.display_order
        project_id = sentence.project_id

        # Delete sentence (cascade will delete tokens and notes)
        sentence.delete()

        # Update display_order for all subsequent sentences (decrement by 1)
        # Use two-phase approach to avoid unique constraint violations
        subsequent_sentences = Sentence.subsequent_sentences(
            project_id, deleted_display_order
        )
        if subsequent_sentences:
            self.display_order_changes = Sentence.renumber_sentences(
                subsequent_sentences,
                order_function=lambda s: s.display_order - 1,
            )

        # Recalculate project structure after deletion
        Sentence.recalculate_project_structure(project_id)

        return True

    def undo(self) -> bool:
        """
        Undo delete operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order) and (project_id, paragraph_number,
        sentence_number_in_paragraph).

        Returns:
            True if successful, False otherwise

        """
        from oeapp.models.idiom import Idiom
        session = self._get_session()
        # CRITICAL: Restore display_order for subsequent sentences FIRST
        # This must happen before recreating the sentence to avoid
        # unique constraint violations
        Sentence.restore_display_orders(
            self.display_order_changes
        )  # Ensure display_order changes are applied

        # Recreate sentence (will get a new ID, which is fine)
        # Use temporary paragraph/sentence numbers to avoid immediate conflicts
        restored_sentence = Sentence(
            project_id=self.sentence_data["project_id"],
            display_order=self.sentence_data["display_order"],
            paragraph_number=-1,
            sentence_number_in_paragraph=-(self.sentence_data["display_order"] + 1000000),
            text_oe=self.sentence_data["text_oe"],
            text_modern=self.sentence_data["text_modern"],
        )
        session.add(restored_sentence)
        session.flush()  # Get the new ID

        # Update sentence text to trigger tokenization (creates new tokens with new IDs)
        restored_sentence.update(self.sentence_data["text_oe"])
        session.add(restored_sentence)
        session.flush()

        # Build mapping of order_index to new token IDs
        restored_tokens = list(restored_sentence.tokens)
        order_index_to_token_id: dict[int, int] = {}
        for token in restored_tokens:
            if token.id and token.order_index is not None:
                order_index_to_token_id[token.order_index] = token.id

        # Restore annotations using order_index mapping
        for token_data in self.sentence_tokens:
            order_index = token_data["order_index"]
            annotation_data = token_data.get("annotation")
            if annotation_data and order_index in order_index_to_token_id:
                new_token_id = order_index_to_token_id[order_index]
                # Create annotation with new token_id
                Annotation.from_json(new_token_id, annotation_data)

        # Restore notes using order_index mapping
        for note_data in self.sentence_notes:
            start_order = note_data.get("start_token_order_index")
            end_order = note_data.get("end_token_order_index")
            start_token_id = (
                order_index_to_token_id.get(start_order)
                if start_order is not None
                else None
            )
            end_token_id = (
                order_index_to_token_id.get(end_order)
                if end_order is not None
                else None
            )

            restored_note = Note(
                sentence_id=restored_sentence.id,
                start_token=start_token_id,
                end_token=end_token_id,
                note_text_md=note_data["note_text_md"],
                note_type=note_data["note_type"],
            )
            restored_note.save()

        # Restore idioms
        for idiom_data in self.sentence_idioms:
            start_order = idiom_data.get("start_token_order_index")
            end_order = idiom_data.get("end_token_order_index")
            start_token_id = order_index_to_token_id.get(start_order)
            end_token_id = order_index_to_token_id.get(end_order)

            if start_token_id and end_token_id:
                restored_idiom = Idiom(
                    sentence_id=restored_sentence.id,
                    start_token_id=start_token_id,
                    end_token_id=end_token_id,
                )
                restored_idiom.save()
                if idiom_data.get("annotation"):
                    Annotation.from_json(None, idiom_data["annotation"], idiom_id=restored_idiom.id)

        # Recalculate project structure after restoration
        Sentence.recalculate_project_structure(self.sentence_data["project_id"])

        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Delete sentence {self.sentence_id}"

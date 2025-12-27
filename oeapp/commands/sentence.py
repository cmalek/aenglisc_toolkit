"""Sentence related commands."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from sqlalchemy import select

from oeapp.models.annotation import Annotation
from oeapp.models.note import Note
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token

from .abstract import Command

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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
        sentence = Sentence.get(self.session, self.sentence_id)
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
        sentence = Sentence.get(self.session, self.sentence_id)
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
class MergeSentenceCommand(Command):
    """Command for merging a sentence with the next sentence."""

    #: The SQLAlchemy session.
    session: Session
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
    #: Before state: display order changes (sentence_id, old_order, new_order)
    display_order_changes: list[tuple[int, int, int]] = field(default_factory=list)

    def execute(self) -> bool:
        """
        Execute merge operation.

        Returns:
            True if successful, False otherwise

        """
        current_sentence = Sentence.get(self.session, self.current_sentence_id)
        next_sentence = Sentence.get(self.session, self.next_sentence_id)

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

        # Get current sentence token count
        current_token_count = len(current_sentence.tokens)

        # Move all tokens from next sentence to current sentence
        # CRITICAL: Update sentence_id and order_index, but keep token IDs the same
        # This preserves annotations which are linked by token_id
        for idx, token in enumerate(next_tokens):
            token.sentence_id = current_sentence.id
            token.order_index = current_token_count + idx
            self.session.add(token)

        self.session.flush()

        # Move all notes from next sentence to current sentence
        for note in next_notes:
            note.sentence_id = current_sentence.id
            self.session.add(note)

        # Merge texts
        merged_text_oe = current_sentence.text_oe + " " + next_sentence.text_oe
        current_modern = current_sentence.text_modern or ""
        next_modern = next_sentence.text_modern or ""
        merged_text_modern = (current_modern + " " + next_modern).strip() or None

        # Update current sentence text (this will re-tokenize and match existing tokens)
        current_sentence.update(self.session, merged_text_oe)
        current_sentence.text_modern = merged_text_modern
        self.session.add(current_sentence)

        # Store next sentence's display_order before deletion
        next_display_order = next_sentence.display_order
        next_project_id = next_sentence.project_id

        # Delete next sentence FIRST to avoid unique constraint violation
        # when updating display_order of subsequent sentences
        self.session.delete(next_sentence)
        self.session.flush()  # Flush to ensure deletion happens before updates

        # Update display_order for all subsequent sentences
        # Query using stored values since next_sentence is now deleted
        subsequent_sentences = Sentence.subsequent_sentences(
            self.session, next_project_id, next_display_order
        )
        for sentence in subsequent_sentences:
            old_order = sentence.display_order
            sentence.display_order -= 1
            self.display_order_changes.append(
                (sentence.id, old_order, sentence.display_order)
            )
            self.session.add(sentence)

        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo merge operation.

        Returns:
            True if successful, False otherwise

        """
        current_sentence = Sentence.get(self.session, self.current_sentence_id)
        if current_sentence is None:
            return False

        # CRITICAL: Restore display_order for subsequent sentences FIRST
        # This must happen before recreating the next sentence to avoid
        # unique constraint violations
        Sentence.restore_display_orders(self.session, self.display_order_changes)

        # Now recreate next sentence (will get a new ID, which is fine)
        next_sentence = Sentence(
            project_id=self.next_sentence_data["project_id"],
            display_order=self.next_sentence_data["display_order"],
            text_oe=self.next_sentence_data["text_oe"],
            text_modern=self.next_sentence_data["text_modern"],
        )
        self.session.add(next_sentence)
        self.session.flush()  # Get the new ID

        # Restore tokens to next sentence with original order_index
        # CRITICAL: Do this BEFORE updating current sentence text
        for token_data in self.next_sentence_tokens:
            token = Token.get(self.session, token_data["id"])
            if token:
                token.sentence_id = next_sentence.id  # Use the new sentence ID
                token.order_index = token_data["order_index"]
                self.session.add(token)

        self.session.flush()  # Ensure tokens are moved before updating current sentence

        # Now restore current sentence texts and update (re-tokenize)
        # This will only affect tokens that belong to current sentence
        current_sentence.text_oe = self.before_text_oe
        current_sentence.text_modern = self.before_text_modern
        current_sentence.update(self.session, self.before_text_oe)
        self.session.add(current_sentence)

        # Restore notes to next sentence
        for note_data in self.next_sentence_notes:
            note = self.session.get(Note, note_data["id"])
            if note:
                note.sentence_id = next_sentence.id  # Use the new sentence ID
                self.session.add(note)

        self.session.commit()
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
class AddSentenceCommand(Command):
    """Command for adding a new sentence before or after an existing sentence."""

    #: The SQLAlchemy session.
    session: Session
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

    def execute(self) -> bool:
        """
        Execute add sentence operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order).

        Returns:
            True if successful, False otherwise

        """
        reference_sentence = Sentence.get(self.session, self.reference_sentence_id)
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
                self.session.scalars(
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
                self.session, self.project_id, reference_sentence.display_order
            )
            # Sort descending for processing
            affected_sentences = sorted(
                affected_sentences, key=lambda s: s.display_order, reverse=True
            )

        # Two-phase approach to avoid constraint violations
        if affected_sentences:
            self.display_order_changes = Sentence.renumber_sentences(
                self.session,
                affected_sentences,
                order_function=lambda s: s.display_order + 1,
            )

        # Create new sentence with empty text_oe
        new_sentence = Sentence.create(
            session=self.session,
            project_id=self.project_id,
            display_order=target_order,
            text_oe="",
        )
        self.new_sentence_id = new_sentence.id

        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo add sentence operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order).

        Returns:
            True if successful, False otherwise

        """
        if self.new_sentence_id is None:
            return False

        # Delete the new sentence first
        new_sentence = Sentence.get(self.session, self.new_sentence_id)
        if new_sentence:
            self.session.delete(new_sentence)
            self.session.flush()

        # Restore display_order using two-phase approach
        Sentence.restore_display_orders(self.session, self.display_order_changes)

        self.session.commit()
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
class DeleteSentenceCommand(Command):
    """Command for deleting a sentence."""

    #: The SQLAlchemy session.
    session: Session
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

    def execute(self) -> bool:
        """
        Execute delete operation.

        Returns:
            True if successful, False otherwise

        """
        sentence = Sentence.get(self.session, self.sentence_id)
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

        # Store sentence's display_order before deletion
        deleted_display_order = sentence.display_order
        project_id = sentence.project_id

        # Delete sentence (cascade will delete tokens and notes)
        self.session.delete(sentence)
        self.session.flush()  # Flush to ensure deletion happens before updates

        # Update display_order for all subsequent sentences (decrement by 1)
        # Use two-phase approach to avoid unique constraint violations
        subsequent_sentences = Sentence.subsequent_sentences(
            self.session, project_id, deleted_display_order
        )
        if subsequent_sentences:
            self.display_order_changes = Sentence.renumber_sentences(
                self.session,
                subsequent_sentences,
                order_function=lambda s: s.display_order - 1,
            )

        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo delete operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order).

        Returns:
            True if successful, False otherwise

        """
        # CRITICAL: Restore display_order for subsequent sentences FIRST
        # This must happen before recreating the sentence to avoid
        # unique constraint violations
        Sentence.restore_display_orders(
            self.session, self.display_order_changes
        )  # Ensure display_order changes are applied

        # Recreate sentence (will get a new ID, which is fine)
        restored_sentence = Sentence(
            project_id=self.sentence_data["project_id"],
            display_order=self.sentence_data["display_order"],
            text_oe=self.sentence_data["text_oe"],
            text_modern=self.sentence_data["text_modern"],
        )
        self.session.add(restored_sentence)
        self.session.flush()  # Get the new ID

        # Update sentence text to trigger tokenization (creates new tokens with new IDs)
        restored_sentence.update(self.session, self.sentence_data["text_oe"])
        self.session.add(restored_sentence)
        self.session.flush()

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
                Annotation.from_json(self.session, new_token_id, annotation_data)

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
            self.session.add(restored_note)

        self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Delete sentence {self.sentence_id}"

"""Sentence related commands."""

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from oeapp.db import get_runtime_session
from oeapp.models.annotation import Annotation
from oeapp.models.headings import (
    HeadingMoveGuard,
    HeadingRole,
    RefusalMixin,
    apply_generated_title,
    apply_heading_title,
    headings_illegal_after,
)
from oeapp.models.idiom import Idiom
from oeapp.models.mixins import SessionMixin
from oeapp.models.note import Note
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token

from .abstract import Command, CommandLocators, StackAdjustment
from .heading import _restore_titles, _snapshot_titles


def _token_ids(sentence_id: int) -> set[int]:
    """
    Get the ids of a sentence's tokens as they are now.

    Args:
        sentence_id: The sentence.

    Returns:
        The token ids.

    """
    session = get_runtime_session()
    return {token.id for token in Token.list(sentence_id, session=session)}


def _idiom_ids(sentence: Sentence) -> set[int]:
    """
    Get the ids of a sentence's idioms as they are now.

    Args:
        sentence: The sentence.

    Returns:
        The idiom ids.

    """
    return {idiom.id for idiom in sentence.idioms}


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
    messages: list[str] = dataclass_field(default_factory=list)

    def execute(self) -> bool:
        """
        Execute sentence edit.

        - If the field is "text_oe", update the sentence text, and re-tokenize
          the sentence, updating the tokens in the sentence.
        - If the field is "text_modern", update the sentence translation.

        Returns:
            True if successful

        """
        session = get_runtime_session()
        sentence = Sentence.get(self.sentence_id, session=session)
        if sentence is None:
            return False

        if self.field == "text_oe":
            self.messages = self._retokenize(sentence, self.after)
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
        session = get_runtime_session()
        sentence = Sentence.get(self.sentence_id, session=session)
        if sentence is None:
            return False

        if self.field == "text_oe":
            self._retokenize(sentence, self.before)
        elif self.field == "text_modern":
            sentence.text_modern = self.before
            sentence.save()
        return True

    def _retokenize(self, sentence: Sentence, text_oe: str) -> list[str]:
        """
        Write ``text_oe`` onto the sentence and record the rows that vanished.

        Args:
            sentence: The sentence to re-tokenize.
            text_oe: The Old English text to write.

        Side Effects:
            Sets :attr:`last_adjustment` to the token and idiom ids that the
            re-tokenization deleted.

        Returns:
            Messages from the update (e.g. deleted idioms).

        """
        token_ids = _token_ids(sentence.id)
        idiom_ids = _idiom_ids(sentence)
        messages = sentence.update(text_oe)
        self._retitle_heading(sentence)
        self.last_adjustment = StackAdjustment(
            obsolete_token_ids=token_ids - _token_ids(sentence.id),
            obsolete_idiom_ids=idiom_ids - _idiom_ids(sentence),
        )
        return messages

    def _retitle_heading(self, sentence: Sentence) -> None:
        """
        Copy the sentence's text into its division's title when it is a heading.

        Args:
            sentence: The sentence whose text was just written.

        Side Effects:
            For a ``chapter`` or ``section`` heading, sets the chapter or
            section title and commits.

        """
        if sentence.heading_role not in (HeadingRole.CHAPTER, HeadingRole.SECTION):
            return
        apply_heading_title(sentence)
        sentence.save()

    def locators(self) -> CommandLocators:
        """
        Get the sentence this edit acts on.

        Returns:
            Locators naming :attr:`sentence_id`.

        """
        return CommandLocators(sentence_ids={self.sentence_id})

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Edit translation" if self.field == "text_modern" else "Edit Old English"

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the command needs a full reload of the project structure after
        execution.

        Returns:
            False for a translation edit, which the sentence card shows in
            place; True for an Old English edit, which re-tokenizes.

        """
        return self.field != "text_modern"


@dataclass
class MergeSentenceCommand(RefusalMixin, SessionMixin, Command):
    """
    Command for merging a sentence with the next sentence.

    The merge is refused, and nothing is written, when either sentence is a
    heading or when a later heading in the section would leave its legal slot.
    """

    #: The current sentence ID.
    current_sentence_id: int
    #: The next sentence ID.
    next_sentence_id: int
    #: Before state: current sentence text_oe
    before_text_oe: str
    #: Before state: current sentence text_modern
    before_text_modern: str | None
    #: Before state: next sentence data for restoration
    next_sentence_data: dict[str, Any] = dataclass_field(default_factory=dict)
    #: Before state: tokens from next sentence (token_id, sentence_id,
    #: order_index, surface)
    next_sentence_tokens: list[dict[str, Any]] = dataclass_field(default_factory=list)
    #: Before state: notes from next sentence
    next_sentence_notes: list[dict[str, Any]] = dataclass_field(default_factory=list)
    #: Before state: idioms from next sentence
    next_sentence_idioms: list[dict[str, Any]] = dataclass_field(default_factory=list)
    #: Before state: display order changes (sentence_id, old_order, new_order)
    display_order_changes: list[tuple[int, int, int]] = dataclass_field(
        default_factory=list
    )

    def execute(self) -> bool:
        """
        Execute merge operation.

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        current_sentence = Sentence.get(self.current_sentence_id, session=session)
        next_sentence = Sentence.get(self.next_sentence_id, session=session)

        if current_sentence is None or next_sentence is None:
            return False
        if self.refuse_unless(
            self._keeps_headings_legal(current_sentence, next_sentence)
        ):
            return False

        # Store next sentence data for undo
        self.next_sentence_data = {
            "id": next_sentence.id,
            "project_id": next_sentence.project_id,
            "display_order": next_sentence.display_order,
            "text_oe": next_sentence.text_oe,
            "text_modern": next_sentence.text_modern,
            "paragraph_id": next_sentence.paragraph_id,
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
        token_ids_before = _token_ids(current_sentence.id) | _token_ids(
            next_sentence.id
        )

        # Move all tokens from next sentence to current sentence
        # CRITICAL: Update sentence_id and order_index, but keep token IDs the same
        # This preserves annotations which are linked by token_id
        for idx, token in enumerate(next_tokens):
            token.sentence_id = current_sentence.id
            token.order_index = current_token_count + idx
            token.save(commit=False)

        # Move all notes from next sentence to current sentence
        for note in next_notes:
            note.sentence_id = current_sentence.id
            note.save(commit=False)

        # Move all idioms from next sentence to current sentence
        for idiom in next_sentence.idioms:
            idiom.sentence_id = current_sentence.id
            idiom.save(commit=False)

        # Merge texts
        merged_text_oe = current_sentence.text_oe + " " + next_sentence.text_oe
        current_modern = current_sentence.text_modern or ""
        next_modern = next_sentence.text_modern or ""
        merged_text_modern = (current_modern + " " + next_modern).strip() or None

        # Update current sentence text (this will re-tokenize and match existing tokens)
        current_sentence.update(merged_text_oe)
        current_sentence.text_modern = merged_text_modern
        current_sentence.save(commit=False)

        # Store next sentence's display_order before deletion
        next_display_order = next_sentence.display_order
        next_project_id = next_sentence.project_id

        # Delete next sentence FIRST to avoid unique constraint violation
        # when updating display_order of subsequent sentences
        next_sentence.delete(commit=False)

        # Update display_order for all subsequent sentences
        # Query using stored values since next_sentence is now deleted
        subsequent_sentences = Sentence.subsequent_sentences(
            next_project_id, next_display_order, session=session
        )
        for sentence in subsequent_sentences:
            old_order = sentence.display_order
            sentence.display_order -= 1
            self.display_order_changes.append(
                (sentence.id, old_order, sentence.display_order)
            )
            sentence.save(commit=False)

        session.commit()
        self.last_adjustment = StackAdjustment(
            obsolete_sentence_ids={self.next_sentence_id},
            token_sentence=self._moved_tokens(current_sentence.id),
            obsolete_token_ids=token_ids_before - _token_ids(current_sentence.id),
        )

        return True

    @staticmethod
    def _keeps_headings_legal(current: Sentence, following: Sentence) -> bool:
        """
        Check that merging two sentences leaves every heading legal.

        Args:
            current: The sentence that keeps its place
            following: The sentence that is folded into it

        Returns:
            ``False`` when either sentence is a heading, because the stored
            title would become the joined Old English, or when a later heading
            in the folded sentence's section would move out of its legal slot

        """
        if current.heading_role is not None or following.heading_role is not None:
            return False
        return HeadingMoveGuard.allows_removal(following)

    def undo(self) -> bool:
        """
        Undo merge operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order).

        Side Effects:
            The next sentence comes back under a new id, which is written onto
            :attr:`next_sentence_id` and recorded in :attr:`last_adjustment`
            for every token that moves back to it.

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        current_sentence = Sentence.get(self.current_sentence_id, session=session)
        if current_sentence is None:
            return False
        token_ids_before = _token_ids(current_sentence.id)

        # CRITICAL: Restore display_order for subsequent sentences FIRST
        # This must happen before recreating the next sentence to avoid
        # unique constraint violations
        Sentence.restore_display_orders(self.display_order_changes, session=session)

        # Now recreate next sentence (will get a new ID, which is fine)
        next_sentence = Sentence(
            project_id=self.next_sentence_data["project_id"],
            display_order=self.next_sentence_data["display_order"],
            paragraph_id=self.next_sentence_data["paragraph_id"],
            text_oe=self.next_sentence_data["text_oe"],
            text_modern=self.next_sentence_data["text_modern"],
        )
        next_sentence.save(commit=False)

        # Restore tokens to next sentence with original order_index
        # CRITICAL: Do this BEFORE updating current sentence text
        for token_data in self.next_sentence_tokens:
            token = Token.get(token_data["id"], session=session)
            if token:
                token.sentence_id = next_sentence.id  # Use the new sentence ID
                token.order_index = token_data["order_index"]
                token.save(commit=False)

        # Now restore current sentence texts and update (re-tokenize)
        # This will only affect tokens that belong to current sentence
        current_sentence.text_oe = self.before_text_oe
        current_sentence.text_modern = self.before_text_modern
        current_sentence.update(self.before_text_oe)
        current_sentence.save(commit=False)

        # Restore notes to next sentence
        for note_data in self.next_sentence_notes:
            note = Note.get(note_data["id"], session=session)
            if note:
                note.sentence_id = next_sentence.id  # Use the new sentence ID
                note.save()

        # Restore idioms to next sentence

        for idiom_data in self.next_sentence_idioms:
            idiom = Idiom.get(idiom_data["id"], session=session)
            if idiom:
                idiom.sentence_id = next_sentence.id
                idiom.save()

        session.commit()
        self.next_sentence_id = next_sentence.id
        surviving = _token_ids(current_sentence.id) | _token_ids(next_sentence.id)
        self.last_adjustment = StackAdjustment(
            token_sentence=self._moved_tokens(next_sentence.id),
            obsolete_token_ids=token_ids_before - surviving,
        )
        return True

    def _moved_tokens(self, sentence_id: int) -> dict[int, int]:
        """
        Map the next sentence's tokens to the sentence they were just moved to.

        Args:
            sentence_id: Sentence the tokens now belong to.

        Returns:
            ``token_id -> sentence_id`` for every token that came from the next
            sentence.

        """
        return {token["id"]: sentence_id for token in self.next_sentence_tokens}

    def locators(self) -> CommandLocators:
        """
        Get the two sentences this merge acts on.

        Returns:
            Locators naming :attr:`current_sentence_id` and
            :attr:`next_sentence_id`.

        """
        return CommandLocators(
            sentence_ids={self.current_sentence_id, self.next_sentence_id}
        )

    def is_removal_of(self, sentence_id: int) -> bool:
        """
        Whether this merge removes ``sentence_id``.

        Args:
            sentence_id: Sentence to check.

        Returns:
            ``True`` for the next sentence, which the merge folds away.

        """
        return sentence_id == self.next_sentence_id

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Merge sentences"

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
class AddSentenceCommand(RefusalMixin, SessionMixin, Command):
    """
    Command for adding a new sentence before or after an existing sentence.

    The insert is refused, and nothing is written, when it would push a
    heading out of its legal slot.
    """

    #: The project ID.
    project_id: int
    #: The reference sentence ID (sentence to insert before/after).
    reference_sentence_id: int
    #: The position relative to reference sentence.
    position: Literal["before", "after"]
    #: The new sentence ID (set after execution).
    new_sentence_id: int | None = None
    #: Display order changes (sentence_id, old_order, new_order).
    display_order_changes: list[tuple[int, int, int]] = dataclass_field(
        default_factory=list
    )
    #: Whether the reference sentence was a paragraph start before being moved.
    reference_was_paragraph_start: bool | None = None

    def execute(self) -> bool:
        """
        Execute add sentence operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order).

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        reference_sentence = Sentence.get(self.reference_sentence_id, session=session)
        if reference_sentence is None:
            return False
        if self.refuse_unless(
            HeadingMoveGuard.allows_insert(reference_sentence, self.position)
        ):
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
            affected_sentences = list(
                Sentence.subsequent_sentences(
                    self.project_id, reference_sentence.display_order, session=session
                )
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
                session=session,
            )

        # Create new sentence in the same paragraph as the reference sentence
        new_sentence = Sentence.create(
            project_id=self.project_id,
            display_order=target_order,
            text_oe="",
            paragraph_id=reference_sentence.paragraph_id,
            session=session,
        )
        self.new_sentence_id = new_sentence.id
        self.last_adjustment = StackAdjustment()

        return True

    def undo(self) -> bool:
        """
        Undo add sentence operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order).

        Side Effects:
            Records the removed sentence in :attr:`last_adjustment`, so steps
            that edited it are dropped; a redo creates the sentence afresh.

        Returns:
            True if successful, False otherwise

        """
        session = get_runtime_session()
        if self.new_sentence_id is None:
            return False

        # Delete the new sentence first
        new_sentence = Sentence.get(self.new_sentence_id, session=session)
        if new_sentence:
            new_sentence.delete()

        # Restore display_order using two-phase approach
        Sentence.restore_display_orders(self.display_order_changes, session=session)
        self.last_adjustment = StackAdjustment(
            obsolete_sentence_ids={self.new_sentence_id}
        )

        return True

    def locators(self) -> CommandLocators:
        """
        Get the sentences this insert acts on.

        Returns:
            Locators naming the reference sentence and, once created, the new
            sentence. ``display_order_changes`` is a snapshot, not a locator.

        """
        sentence_ids = {self.reference_sentence_id}
        if self.new_sentence_id is not None:
            sentence_ids.add(self.new_sentence_id)
        return CommandLocators(sentence_ids=sentence_ids)

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Add sentence"


def _revert_heading(sentence: Sentence) -> None:
    """
    Give a ``chapter`` or ``section`` heading's division its generated title.

    Args:
        sentence: The sentence about to be deleted or cleared

    Side Effects:
        Sets the chapter or section title to ``Chapter {n}`` or
        ``Section {n}``. Other roles do nothing.

    """
    if sentence.heading_role in (HeadingRole.CHAPTER, HeadingRole.SECTION):
        apply_generated_title(sentence)


def _clear_illegal_headings(section: Section) -> list[tuple[int, str, str]]:
    """
    Clear every heading in a section that no longer sits in a legal slot.

    Args:
        section: The section a sentence was just deleted from

    Side Effects:
        Reverts the generated title of each cleared ``chapter`` or ``section``
        heading and sets its ``heading_role`` to ``None``.

    Returns:
        The id, role, and Old English text of each cleared heading, in display
        order

    """
    cleared: list[tuple[int, str, str]] = []
    for sentence in headings_illegal_after(section):
        role = sentence.heading_role
        if role is None:
            continue
        cleared.append((sentence.id, role, sentence.text_oe))
        _revert_heading(sentence)
        sentence.heading_role = None
    return cleared


@dataclass
class DeleteSentenceCommand(SessionMixin, Command):
    """
    Command for deleting a sentence.

    Deleting a heading reverts its division title. Headings in the same section
    that the delete leaves outside their legal slot are cleared, and undo
    restores them along with the sentence.
    """

    #: The sentence ID to delete.
    sentence_id: int
    #: Before state: sentence data for restoration
    sentence_data: dict[str, Any] = dataclass_field(default_factory=dict)
    #: Before state: tokens from sentence
    sentence_tokens: list[dict[str, Any]] = dataclass_field(default_factory=list)
    #: Before state: notes from sentence
    sentence_notes: list[dict[str, Any]] = dataclass_field(default_factory=list)
    #: Before state: display order changes (sentence_id, old_order, new_order)
    display_order_changes: list[tuple[int, int, int]] = dataclass_field(
        default_factory=list
    )
    #: Before state: idioms from sentence
    sentence_idioms: list[dict[str, Any]] = dataclass_field(default_factory=list)
    #: Before state: the chapter and section titles, with their ``title_auto``.
    previous_titles: tuple[str | None, bool, str | None, bool] | None = None
    #: After state: the id, role, and Old English text of each heading cleared
    #: because the delete moved it out of its legal slot, in display order.
    cleared_headings: list[tuple[int, str, str]] = dataclass_field(default_factory=list)

    @property
    def needs_full_reload(self) -> bool:
        """
        Whether the project structure must be reloaded after the command.

        Returns:
            ``True``, because a delete can clear the headings of neighbors

        """
        return True

    def execute(self) -> bool:
        """
        Execute delete operation.

        The deleted sentence's division title is reverted first when it was a
        ``chapter`` or ``section`` heading. After the delete and renumbering,
        every heading in the same section that no longer sits in a legal slot
        is cleared and recorded in :attr:`cleared_headings`.

        Side Effects:
            Deletes the sentence, renumbers later sentences, and may rewrite
            titles and clear heading roles in the sentence's section. Commits.

        Returns:
            True if successful, False otherwise

        """
        session = get_runtime_session()
        sentence = Sentence.get(self.sentence_id, session=session)
        if sentence is None:
            return False
        self.previous_titles = _snapshot_titles(sentence)
        section = sentence.paragraph.section if sentence.paragraph else None
        _revert_heading(sentence)
        self.cleared_headings = []

        # Store sentence's display_order before deletion
        deleted_display_order = sentence.display_order
        project_id = sentence.project_id

        # Store sentence data for undo
        self.sentence_data = {
            "id": sentence.id,
            "project_id": sentence.project_id,
            "display_order": sentence.display_order,
            "text_oe": sentence.text_oe,
            "text_modern": sentence.text_modern,
            "paragraph_id": sentence.paragraph_id,
            "heading_role": sentence.heading_role,
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
            self.sentence_idioms.append(
                {
                    "start_token_order_index": idiom.start_token.order_index,
                    "end_token_order_index": idiom.end_token.order_index,
                    "annotation": idiom.annotation.to_json()
                    if idiom.annotation
                    else None,
                }
            )

        # Store sentence's display_order before deletion
        deleted_display_order = sentence.display_order
        project_id = sentence.project_id
        self.last_adjustment = StackAdjustment(
            obsolete_sentence_ids={self.sentence_id},
            obsolete_token_ids={token.id for token in sentence_tokens},
            obsolete_idiom_ids=_idiom_ids(sentence),
        )

        # Delete sentence (cascade will delete tokens and notes)
        sentence.delete()

        # Update display_order for all subsequent sentences (decrement by 1)
        # Use two-phase approach to avoid unique constraint violations
        subsequent_sentences = Sentence.subsequent_sentences(
            project_id, deleted_display_order, session=session
        )
        if subsequent_sentences:
            self.display_order_changes = Sentence.renumber_sentences(
                list(subsequent_sentences),
                order_function=lambda s: s.display_order - 1,
                session=session,
            )

        # Recalculate project structure after deletion
        Sentence.recalculate_project_structure(project_id, session=session)
        if section is not None:
            session.expire_all()
            self.cleared_headings = _clear_illegal_headings(section)
            session.commit()

        return True

    def undo(self) -> bool:
        """
        Undo delete operation.

        CRITICAL: Uses two-phase approach to handle unique constraint on
        (project_id, display_order).

        Side Effects:
            The sentence comes back under a new id, which is written onto
            :attr:`sentence_id` so a redo deletes the restored row.

        Returns:
            True if successful, False otherwise

        """
        session = self._get_session()
        # CRITICAL: Restore display_order for subsequent sentences FIRST
        # This must happen before recreating the sentence to avoid
        # unique constraint violations
        Sentence.restore_display_orders(
            self.display_order_changes, session=session
        )  # Ensure display_order changes are applied

        # Recreate sentence (will get a new ID, which is fine)
        restored_sentence = Sentence(
            project_id=self.sentence_data["project_id"],
            display_order=self.sentence_data["display_order"],
            paragraph_id=self.sentence_data["paragraph_id"],
            text_oe=self.sentence_data["text_oe"],
            text_modern=self.sentence_data["text_modern"],
            heading_role=self.sentence_data.get("heading_role"),
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
            if start_order is None or end_order is None:
                continue
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
                    Annotation.from_json(
                        None, idiom_data["annotation"], idiom_id=restored_idiom.id
                    )

        self.sentence_id = restored_sentence.id
        self._restore_headings(restored_sentence, session)
        self.last_adjustment = StackAdjustment()
        return True

    def _restore_headings(self, restored: Sentence, session: Session) -> None:
        """
        Put back the division titles and the heading roles the delete cleared.

        Args:
            restored: The sentence recreated by the undo
            session: The session the undo runs in

        Side Effects:
            Sets chapter and section titles and ``heading_role`` on the
            cleared sentences. Commits.

        """
        _restore_titles(restored, self.previous_titles)
        for sentence_id, role, _text_oe in self.cleared_headings:
            cleared = Sentence.get(sentence_id, session=session)
            if cleared is not None:
                cleared.heading_role = role
        session.commit()

    def locators(self) -> CommandLocators:
        """
        Get the sentence this command removes or restores.

        Returns:
            Locators naming :attr:`sentence_id`.

        """
        return CommandLocators(sentence_ids={self.sentence_id})

    def is_removal_of(self, sentence_id: int) -> bool:
        """
        Whether this command removes ``sentence_id``.

        Args:
            sentence_id: Sentence to check.

        Returns:
            ``True`` for the deleted sentence.

        """
        return sentence_id == self.sentence_id

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Delete sentence"

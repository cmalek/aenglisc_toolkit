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

        next_tokens, next_notes = self._record_next_sentence(next_sentence)
        token_ids_before = _token_ids(current_sentence.id) | _token_ids(
            next_sentence.id
        )
        self._move_children(current_sentence, next_sentence, next_tokens, next_notes)
        self._merge_texts(current_sentence, next_sentence)

        # Store next sentence's display_order before deletion
        next_display_order = next_sentence.display_order
        next_project_id = next_sentence.project_id

        # Delete next sentence FIRST to avoid unique constraint violation
        # when updating display_order of subsequent sentences
        next_sentence.delete(commit=False)
        self._close_gap(next_project_id, next_display_order, session)

        session.commit()
        self.last_adjustment = StackAdjustment(
            obsolete_sentence_ids={self.next_sentence_id},
            token_sentence=self._moved_tokens(current_sentence.id),
            obsolete_token_ids=token_ids_before - _token_ids(current_sentence.id),
        )

        return True

    def _record_next_sentence(
        self, next_sentence: Sentence
    ) -> tuple[list[Token], list[Note]]:
        """
        Store the next sentence's data, tokens, notes, and idioms for undo.

        Args:
            next_sentence: The sentence about to be folded into the current one.

        Side Effects:
            Sets :attr:`next_sentence_data`, :attr:`next_sentence_tokens`,
            :attr:`next_sentence_notes`, and :attr:`next_sentence_idioms`.

        Returns:
            The next sentence's tokens and notes, before they are moved.

        """
        self.next_sentence_data = {
            "id": next_sentence.id,
            "project_id": next_sentence.project_id,
            "display_order": next_sentence.display_order,
            "text_oe": next_sentence.text_oe,
            "text_modern": next_sentence.text_modern,
            "paragraph_id": next_sentence.paragraph_id,
        }
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
        self.next_sentence_idioms = [
            {
                "id": idiom.id,
                "sentence_id": idiom.sentence_id,
                "start_token_id": idiom.start_token_id,
                "end_token_id": idiom.end_token_id,
            }
            for idiom in next_sentence.idioms
        ]
        return next_tokens, next_notes

    @staticmethod
    def _move_children(
        current: Sentence,
        following: Sentence,
        tokens: list[Token],
        notes: list[Note],
    ) -> None:
        """
        Move the next sentence's tokens, notes, and idioms to the current one.

        Token ids stay the same, so annotations, which hang off token ids,
        survive.

        Args:
            current: The sentence that receives the children.
            following: The sentence that gives them up.
            tokens: The next sentence's tokens.
            notes: The next sentence's notes.

        Side Effects:
            Sets ``sentence_id`` (and, for tokens, ``order_index``) on each
            child. Does not commit.

        """
        current_token_count = len(current.tokens)
        for idx, token in enumerate(tokens):
            token.sentence_id = current.id
            token.order_index = current_token_count + idx
            token.save(commit=False)
        for note in notes:
            note.sentence_id = current.id
            note.save(commit=False)
        for idiom in following.idioms:
            idiom.sentence_id = current.id
            idiom.save(commit=False)

    @staticmethod
    def _merge_texts(current: Sentence, following: Sentence) -> None:
        """
        Join the two sentences' texts onto the current sentence.

        Args:
            current: The sentence that keeps its place.
            following: The sentence folded into it.

        Side Effects:
            Re-tokenizes ``current`` with the joined Old English and sets its
            translation. Does not commit.

        """
        merged_text_oe = current.text_oe + " " + following.text_oe
        current_modern = current.text_modern or ""
        next_modern = following.text_modern or ""
        merged_text_modern = (current_modern + " " + next_modern).strip() or None
        # This re-tokenizes and matches the existing tokens.
        current.update(merged_text_oe)
        current.text_modern = merged_text_modern
        current.save(commit=False)

    def _close_gap(self, project_id: int, deleted_order: int, session: Session) -> None:
        """
        Move the sentences after a folded-away sentence up by one.

        Args:
            project_id: The project the sentence belonged to.
            deleted_order: The ``display_order`` the deleted sentence had.
            session: The session the command runs in.

        Side Effects:
            Decrements ``display_order`` of later sentences and appends each
            change to :attr:`display_order_changes`. Does not commit.

        """
        for sentence in Sentence.subsequent_sentences(
            project_id, deleted_order, session=session
        ):
            old_order = sentence.display_order
            sentence.display_order -= 1
            self.display_order_changes.append(
                (sentence.id, old_order, sentence.display_order)
            )
            sentence.save(commit=False)

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

        affected_sentences = self._sentences_to_shift(
            reference_sentence, target_order, session
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

    def _sentences_to_shift(
        self, reference: Sentence, target_order: int, session: Session
    ) -> list[Sentence]:
        """
        Find the sentences whose ``display_order`` the insert pushes down.

        Args:
            reference: The sentence the new one goes next to.
            target_order: The ``display_order`` the new sentence will take.
            session: The session the command runs in.

        Returns:
            The sentences from the insert point on, last first.

        """
        if self.position == "before":
            return list(
                session.scalars(
                    select(Sentence)
                    .where(
                        Sentence.project_id == self.project_id,
                        Sentence.display_order >= target_order,
                    )
                    .order_by(Sentence.display_order.desc())
                ).all()
            )
        later = Sentence.subsequent_sentences(
            self.project_id, reference.display_order, session=session
        )
        return sorted(later, key=lambda s: s.display_order, reverse=True)

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
        section = self._prepare_heading_revert(sentence)
        deleted_display_order = sentence.display_order
        project_id = sentence.project_id
        sentence_tokens = self._record_sentence(sentence)
        self.last_adjustment = StackAdjustment(
            obsolete_sentence_ids={self.sentence_id},
            obsolete_token_ids={token.id for token in sentence_tokens},
            obsolete_idiom_ids=_idiom_ids(sentence),
        )

        # Delete sentence (cascade will delete tokens and notes)
        sentence.delete()
        self._close_gap(project_id, deleted_display_order, session)
        Sentence.recalculate_project_structure(project_id, session=session)
        self._recheck_section(section, session)
        return True

    def _prepare_heading_revert(self, sentence: Sentence) -> Section | None:
        """
        Snapshot the titles and revert the deleted sentence's division title.

        Args:
            sentence: The sentence about to be deleted.

        Side Effects:
            Sets :attr:`previous_titles` and resets :attr:`cleared_headings`.
            Rewrites the chapter or section title when the sentence is a
            ``chapter`` or ``section`` heading.

        Returns:
            The sentence's section, or ``None`` when it has no paragraph.

        """
        self.previous_titles = _snapshot_titles(sentence)
        section = sentence.paragraph.section if sentence.paragraph else None
        _revert_heading(sentence)
        self.cleared_headings = []
        return section

    def _recheck_section(self, section: Section | None, session: Session) -> None:
        """
        Clear the headings the delete left outside their legal slots.

        Only the section the sentence belonged to is checked.

        Args:
            section: The deleted sentence's section, or ``None``.
            session: The session the command runs in.

        Side Effects:
            Sets :attr:`cleared_headings`, reverts generated titles, clears
            roles, and commits.

        """
        if section is None:
            return
        session.expire_all()
        self.cleared_headings = _clear_illegal_headings(section)
        session.commit()

    def _close_gap(self, project_id: int, deleted_order: int, session: Session) -> None:
        """
        Move the sentences after the deleted one up by one.

        Uses a two-phase renumber to avoid unique constraint violations.

        Args:
            project_id: The project the sentence belonged to.
            deleted_order: The ``display_order`` the deleted sentence had.
            session: The session the command runs in.

        Side Effects:
            Sets :attr:`display_order_changes` and renumbers later sentences.

        """
        subsequent_sentences = Sentence.subsequent_sentences(
            project_id, deleted_order, session=session
        )
        if subsequent_sentences:
            self.display_order_changes = Sentence.renumber_sentences(
                list(subsequent_sentences),
                order_function=lambda s: s.display_order - 1,
                session=session,
            )

    def _record_sentence(self, sentence: Sentence) -> list[Token]:
        """
        Store the sentence, its tokens, notes, and idioms for undo.

        Args:
            sentence: The sentence about to be deleted.

        Side Effects:
            Sets :attr:`sentence_data`, :attr:`sentence_tokens`,
            :attr:`sentence_notes`, and :attr:`sentence_idioms`.

        Returns:
            The sentence's tokens, before deletion.

        """
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

        self._record_notes_and_idioms(sentence, sentence_tokens)
        return sentence_tokens

    def _record_notes_and_idioms(
        self, sentence: Sentence, sentence_tokens: list[Token]
    ) -> None:
        """
        Store the sentence's notes and idioms for undo, by token position.

        Args:
            sentence: The sentence about to be deleted.
            sentence_tokens: The sentence's tokens.

        Side Effects:
            Sets :attr:`sentence_notes` and :attr:`sentence_idioms`.

        """
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
        restored_sentence = self._recreate_sentence(session)
        self._restore_children(restored_sentence)
        self.sentence_id = restored_sentence.id
        self._restore_headings(restored_sentence, session)
        self.last_adjustment = StackAdjustment()
        return True

    def _recreate_sentence(self, session: Session) -> Sentence:
        """
        Put the deleted sentence's row back and re-tokenize it.

        CRITICAL: Restores ``display_order`` of later sentences first, to
        avoid unique constraint violations.

        Args:
            session: The session the undo runs in.

        Side Effects:
            Adds the sentence, which gets a new id, and its new tokens.

        Returns:
            The recreated sentence.

        """
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
        return restored_sentence

    def _restore_children(self, restored_sentence: Sentence) -> None:
        """
        Restore annotations, notes, and idioms onto the recreated sentence.

        Args:
            restored_sentence: The sentence recreated by the undo.

        Side Effects:
            Creates annotations, notes, and idioms, matching tokens by
            ``order_index``.

        """
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

        self._restore_notes(restored_sentence, order_index_to_token_id)
        self._restore_idioms(restored_sentence, order_index_to_token_id)

    def _restore_notes(
        self, restored_sentence: Sentence, order_index_to_token_id: dict[int, int]
    ) -> None:
        """
        Recreate the deleted sentence's notes.

        Args:
            restored_sentence: The sentence recreated by the undo.
            order_index_to_token_id: Maps a token's ``order_index`` to its new id.

        Side Effects:
            Creates and saves the notes.

        """
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

    def _restore_idioms(
        self, restored_sentence: Sentence, order_index_to_token_id: dict[int, int]
    ) -> None:
        """
        Recreate the deleted sentence's idioms and their annotations.

        Args:
            restored_sentence: The sentence recreated by the undo.
            order_index_to_token_id: Maps a token's ``order_index`` to its new id.

        Side Effects:
            Creates and saves the idioms and their annotations.

        """
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

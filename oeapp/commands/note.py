"""Notes related commands."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from oeapp.models.note import Note
from oeapp.models.sentence import Sentence

from .abstract import Command

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class AddNoteCommand(Command):
    """Command for adding a note."""

    #: The SQLAlchemy session.
    session: Session
    #: The sentence ID.
    sentence_id: int
    #: The start token ID.
    start_token_id: int
    #: The end token ID.
    end_token_id: int
    #: The note text.
    note_text: str
    #: The note number (computed).
    note_number: int | None = None
    #: The created note ID (set after execution).
    note_id: int | None = None

    def execute(self) -> bool:
        """
        Execute note creation.

        Returns:
            True if successful, False otherwise

        """
        # Get next note number
        if self.note_number is None:
            self.note_number = self._get_next_note_number()

        # Create note
        # Ensure None instead of False or 0 for nullable foreign keys
        start_token_id = (
            self.start_token_id if self.start_token_id is not None else None
        )
        end_token_id = self.end_token_id if self.end_token_id is not None else None
        note = Note(
            sentence_id=self.sentence_id,
            start_token=start_token_id,
            end_token=end_token_id,
            note_text_md=self.note_text,
            note_type="span",
        )
        self.session.add(note)
        self.session.flush()
        self.note_id = note.id

        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo note creation.

        Returns:
            True if successful, False otherwise

        """
        if self.note_id is None:
            return False

        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        self.session.delete(note)
        self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Add note {self.note_number} to sentence {self.sentence_id}"

    def _get_next_note_number(self) -> int:
        """
        Get next note number for the sentence.

        Returns:
            Next note number

        """
        sentence = Sentence.get(self.session, self.sentence_id)
        if sentence is None:
            return 1

        notes = sentence.notes
        if not notes:
            return 1

        # Note numbers are computed dynamically based on token position,
        # not stored. This returns the count + 1, but actual numbering
        # is done by sorting notes by token position.
        return len(notes) + 1

    @staticmethod
    def get_note_number(session: Session, sentence_id: int, note_id: int) -> int:
        """
        Get note number for a note (1-based index in sentence's notes).

        Notes are numbered by their position in the sentence (by start token
        order_index), not by creation time.

        Args:
            session: SQLAlchemy session
            sentence_id: Sentence ID
            note_id: Note ID

        Returns:
            Note number (1-based)

        """
        sentence = Sentence.get(session, sentence_id)
        if sentence is None:
            return 1

        # Refresh sentence to ensure relationships are up-to-date
        session.refresh(sentence)

        # Safely access tokens relationship - convert to list to trigger lazy load
        tokens_list = list(sentence.tokens)
        if not tokens_list:
            return 1

        # Build token ID to order_index mapping
        token_id_to_order: dict[int, int] = {}
        for token in tokens_list:
            if token.id:
                token_id_to_order[token.id] = token.order_index

        def get_note_position(note: Note) -> int:
            """Get position of note in sentence based on start token."""
            if note.start_token and note.start_token in token_id_to_order:
                return token_id_to_order[note.start_token]
            # Fallback to end_token if start_token not found
            if note.end_token and note.end_token in token_id_to_order:
                return token_id_to_order[note.end_token]
            # Fallback to very high number if neither found
            return 999999

        # Safely access notes relationship - convert to list to trigger lazy load
        notes_list = list(sentence.notes)
        notes = sorted(notes_list, key=get_note_position)
        for idx, note in enumerate(notes, start=1):
            if note.id == note_id:
                return idx
        return 1


@dataclass
class UpdateNoteCommand(Command):
    """Command for updating a note."""

    #: The SQLAlchemy session.
    session: Session
    #: The note ID.
    note_id: int
    #: The before note text.
    before_text: str
    #: The after note text.
    after_text: str
    #: The before start token ID.
    before_start_token: int | None
    #: The before end token ID.
    before_end_token: int | None
    #: The after start token ID.
    after_start_token: int | None
    #: The after end token ID.
    after_end_token: int | None

    def execute(self) -> bool:
        """
        Execute note update.

        Returns:
            True if successful, False otherwise

        """
        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        note.note_text_md = self.after_text
        # Ensure None instead of False or 0 for nullable foreign keys
        note.start_token = (
            self.after_start_token if self.after_start_token is not None else None
        )
        note.end_token = (
            self.after_end_token if self.after_end_token is not None else None
        )
        self.session.add(note)
        self.session.commit()
        return True

    def undo(self) -> bool:
        """
        Undo note update.

        Returns:
            True if successful, False otherwise

        """
        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        note.note_text_md = self.before_text
        # Ensure None instead of False or 0 for nullable foreign keys
        note.start_token = (
            self.before_start_token if self.before_start_token is not None else None
        )
        note.end_token = (
            self.before_end_token if self.before_end_token is not None else None
        )
        self.session.add(note)
        self.session.commit()
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Update note {self.note_id}"


@dataclass
class DeleteNoteCommand(Command):
    """Command for deleting a note."""

    #: The SQLAlchemy session.
    session: Session
    #: The note ID.
    note_id: int
    #: The note text (for undo).
    note_text: str = ""
    #: The start token ID (for undo).
    start_token_id: int | None = None
    #: The end token ID (for undo).
    end_token_id: int | None = None
    #: The sentence ID (for undo).
    sentence_id: int | None = None
    #: The note number (for undo).
    note_number: int | None = None

    def execute(self) -> bool:
        """
        Execute note deletion.

        Note: After deletion, remaining notes will be automatically renumbered
        when the UI refreshes, since note numbers are computed dynamically
        based on token position order (earlier tokens = lower numbers).

        Returns:
            True if successful, False otherwise

        """
        note = Note.get(self.session, self.note_id)
        if note is None:
            return False

        # Store values for undo
        self.note_text = note.note_text_md
        self.start_token_id = note.start_token
        self.end_token_id = note.end_token
        self.sentence_id = note.sentence_id
        if self.sentence_id:
            # Store note number for reference (though it's computed dynamically)
            self.note_number = AddNoteCommand.get_note_number(
                self.session, self.sentence_id, self.note_id
            )

        self.session.delete(note)
        self.session.commit()
        # Note: The UI should refresh after this command executes to renumber
        # remaining notes. This happens via the note_saved signal handler.
        return True

    def undo(self) -> bool:
        """
        Undo note deletion.

        Returns:
            True if successful, False otherwise

        """
        if (
            self.sentence_id is None
            or self.start_token_id is None
            or self.end_token_id is None
        ):
            return False

        # Recreate note
        note = Note(
            sentence_id=self.sentence_id,
            start_token=self.start_token_id,
            end_token=self.end_token_id,
            note_text_md=self.note_text,
            note_type="span",
        )
        self.session.add(note)
        self.session.commit()
        self.note_id = note.id
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Description string

        """
        return f"Delete note {self.note_id}"

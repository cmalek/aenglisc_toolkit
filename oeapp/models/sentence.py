"""Sentence model."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from typing import TYPE_CHECKING, cast

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.mixins import SaveDeleteMixin
from oeapp.models.note import Note
from oeapp.models.token import Token
from oeapp.utils import from_utc_iso, to_utc_iso

if TYPE_CHECKING:
    from oeapp.models.chapter import Chapter
    from oeapp.models.idiom import Idiom
    from oeapp.models.paragraph import Paragraph
    from oeapp.models.project import Project


class Sentence(SaveDeleteMixin, Base):
    """
    Represents a sentence.

    A sentences has these characteristics:

    - A paragraph ID
    - A project ID
    - A display order
    - An Old English text
    - A Modern English translation (optional)
    - A list of tokens
    - A list of notes
    - The date and time the sentence was created
    - The date and time the sentence was last updated

    A sentence is related to a project by the project ID.
    A sentence is related to a paragraph by the paragraph ID.
    A sentence is related to a list of tokens by the token ID.
    A sentence is related to a list of notes by the note ID.
    """

    __tablename__ = "sentences"
    __table_args__ = (
        UniqueConstraint(
            "project_id", "display_order", name="uq_sentences_project_order"
        ),
    )

    #: The sentence ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The project ID.
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    #: The paragraph ID.
    paragraph_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("paragraphs.id", ondelete="CASCADE"), nullable=True
    )
    #: The display order of the sentence in the project.
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The Old English text.
    text_oe: Mapped[str] = mapped_column(String, nullable=False)
    #: The Modern English translation.
    text_modern: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the sentence was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    #: The date and time the sentence was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="sentences")
    paragraph: Mapped["Paragraph"] = relationship("Paragraph", back_populates="sentences")
    tokens: Mapped[builtins.list[Token]] = relationship(
        "Token",
        back_populates="sentence",
        cascade="all, delete-orphan",
        order_by="Token.order_index",
        lazy="select",  # Load tokens when accessed
    )
    notes: Mapped[builtins.list[Note]] = relationship(
        "Note", back_populates="sentence", cascade="all, delete-orphan"
    )
    idioms: Mapped[builtins.list[Idiom]] = relationship(
        "Idiom", back_populates="sentence", cascade="all, delete-orphan"
    )

    @classmethod
    def _calculate_paragraph_and_sentence_numbers(
        cls,
        project_id: int,
        display_order: int,
        is_paragraph_start: bool,  # noqa: FBT001
    ) -> dict[str, int]:
        """
        Calculate paragraph_number and sentence_number_in_paragraph for a new sentence.

        Args:
            project_id: Project ID
            display_order: Display order of the new sentence
            is_paragraph_start: Whether this sentence starts a paragraph

        Returns:
            Dictionary with 'paragraph_number' and 'sentence_number_in_paragraph'

        """
        session = cls._get_session()
        # Get all sentences before this one, ordered by display_order
        previous_sentences = list(
            session.scalars(
                select(cls)
                .where(
                    cls.project_id == project_id,
                    cls.display_order < display_order,
                )
                .order_by(cls.display_order)
            ).all()
        )

        if not previous_sentences:
            # First sentence in project
            return {"paragraph_number": 1, "sentence_number_in_paragraph": 1}

        # Get the last sentence before this one
        last_sentence = previous_sentences[-1]

        if is_paragraph_start:
            # Starting a new paragraph
            paragraph_number = last_sentence.paragraph_number + 1
            sentence_number_in_paragraph = 1
        else:
            # Continuing the same paragraph
            paragraph_number = last_sentence.paragraph_number
            # Count sentences in this paragraph
            sentences_in_paragraph = [
                s for s in previous_sentences if s.paragraph_number == paragraph_number
            ]
            sentence_number_in_paragraph = len(sentences_in_paragraph) + 1

        return {
            "paragraph_number": paragraph_number,
            "sentence_number_in_paragraph": sentence_number_in_paragraph,
        }

    @classmethod
    def get(cls, sentence_id: int) -> Sentence | None:
        """
        Get a sentence by ID.
        """
        session = cls._get_session()
        return session.get(cls, sentence_id)

    @classmethod
    def list(cls, project_id: int) -> builtins.list[Sentence]:
        """
        Check if a sentence exists by project ID and display order.
        """
        session = cls._get_session()
        return builtins.list(
            session.scalars(
                select(cls)
                .where(
                    cls.project_id == project_id,
                )
                .order_by(cls.display_order)
            ).all()
        )

    @classmethod
    def get_next_sentence(cls, project_id: int, display_order: int) -> Sentence | None:
        """
        Get the next sentence by project ID and display order.

        Args:
            project_id: Project ID
            display_order: Display order

        Returns:
            The next sentence or None if there is no next sentence

        """
        session = cls._get_session()
        stmt = (
            select(Sentence)
            .where(
                cls.project_id == project_id,
                cls.display_order == display_order,
            )
            .limit(1)
        )
        return session.scalar(stmt)

    @classmethod
    def create(  # noqa: PLR0913
        cls,
        project_id: int,
        display_order: int,
        text_oe: str,
        paragraph_id: int | None = None,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> Sentence:
        """
        Import an entire OE text into a project.

        The text is split into sentences and each sentence is imported into
        the project.  The display order is the index of the sentence in the
        text.

        Args:
            project_id: Project ID
            display_order: Display order
            text_oe: Old English text
            paragraph_id: Paragraph ID

        Keyword Args:
            commit: Whether to commit the changes to the database

        Returns:
            The new :class:`~oeapp.models.sentence.Sentence` object

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(cls.__name__)

        session = cls._get_session()

        # If paragraph_id is not provided, ensure we have a default hierarchy
        if paragraph_id is None:
            from oeapp.models.project import Project
            from oeapp.models.chapter import Chapter
            from oeapp.models.section import Section
            from oeapp.models.paragraph import Paragraph
            
            project = session.get(Project, project_id)
            if project:
                if not project.chapters:
                    chapter = Chapter(project_id=project_id, number=1)
                    session.add(chapter)
                    session.flush()
                    section = Section(chapter_id=chapter.id, number=1)
                    session.add(section)
                    session.flush()
                    paragraph = Paragraph(section_id=section.id, order=1)
                    session.add(paragraph)
                    session.flush()
                    paragraph_id = paragraph.id
                else:
                    # Use existing first paragraph
                    paragraph_id = project.chapters[0].sections[0].paragraphs[0].id

        sentence = cls(
            project_id=project_id,
            display_order=display_order,
            paragraph_id=paragraph_id,
            text_oe=text_oe,
        )
        sentence.save(commit=False)

        # Create tokens from sentence text
        tokens = Token.create_from_sentence(
            sentence_id=sentence.id, sentence_text=text_oe
        )
        sentence.tokens = tokens

        if commit:
            session.commit()
            logger.info(
                "sentence.created",
                project_id=sentence.project_id,
                project_name=sentence.project.name,
                sentence_id=sentence.id,
                display_order=sentence.display_order,
                text_oe=text_oe,
            )
        return sentence

    @classmethod
    def subsequent_sentences(
        cls, project_id: int, display_order: int
    ) -> builtins.list[Sentence]:
        """
        Get the subsequent sentences by project ID and display order.

        Args:
            session: SQLAlchemy session
            project_id: Project ID
            display_order: Display order

        Returns:
            List of subsequent sentences

        """
        session = cls._get_session()
        return builtins.list(
            session.scalars(
                select(cls)
                .where(cls.project_id == project_id, cls.display_order > display_order)
                .order_by(cls.display_order)
            ).all()
        )

    @classmethod
    def renumber_sentences(
        cls,
        sentences: builtins.list[Sentence],
        order_mapping: dict[int, int] | None = None,
        order_function: Callable[[Sentence], int] | None = None,
    ) -> builtins.list[tuple[int, int, int]]:
        """
        Update display_order for multiple sentences using two-phase approach.

        This method safely updates display_order values for multiple sentences
        to avoid unique constraint violations on (project_id, display_order).

        Args:
            sentences: List of sentences to update
            order_mapping: Optional dict mapping sentence.id -> new display_order
            order_function: Optional function taking Sentence -> new display_order

        Returns:
            List of (sentence_id, old_order, new_order) tuples tracking changes

        Raises:
            ValueError: If neither order_mapping nor order_function is provided

        """
        session = cls._get_session()
        if not sentences:
            return []

        if order_mapping is None and order_function is None:
            msg = "Either order_mapping or order_function must be provided"
            raise ValueError(msg)

        # Track old orders before Phase 1
        old_orders = {s.id: s.display_order for s in sentences}

        # Phase 1: Move to temporary positions
        temp_offset = -10000
        for sentence in sentences:
            sentence.display_order = temp_offset
            temp_offset -= 1
            session.add(sentence)
        session.flush()

        # Phase 2: Move to final positions
        # CRITICAL: Use old_orders for computation, not current sentence.display_order
        # because sentences have been moved to temporary positions in Phase 1
        changes: builtins.list[tuple[int, int, int]] = []
        for sentence in sentences:
            old_order = old_orders[sentence.id]
            if order_mapping:
                new_order = order_mapping[sentence.id]
            else:
                assert order_function is not None  # noqa: S101
                # Temporarily restore display_order for order_function computation
                # The order_function needs to see the original display_order value
                sentence.display_order = old_order
                new_order = order_function(sentence)
            sentence.display_order = new_order
            changes.append((sentence.id, old_order, new_order))
            session.add(sentence)
        session.commit()
        session.flush()

        return changes

    @classmethod
    def restore_display_orders(
        cls,
        changes: builtins.list[tuple[int, int, int]],
    ) -> None:
        """
        Restore display_order values using two-phase approach.

        This method safely restores display_order values from a list of changes,
        where each change is (sentence_id, old_order, new_order). It restores
        sentences to their old_order values.

        Args:
            changes: List of (sentence_id, old_order, new_order) tuples

        """
        session = cls._get_session()
        if not changes:
            return

        # Phase 1: Move to temporary positions
        temp_offset = -10000
        for sentence_id, _old_order, _new_order in changes:
            sentence = cls.get(sentence_id)
            if sentence:
                sentence.display_order = temp_offset
                temp_offset -= 1
                session.add(sentence)
        session.flush()

        # Phase 2: Restore original display_order values
        # Sort by old_order descending (process in reverse order)
        sorted_changes: builtins.list[tuple[int, int, int]] = sorted(
            changes, key=lambda x: x[1], reverse=True
        )
        for sentence_id, old_order, _new_order in sorted_changes:
            sentence = cls.get(sentence_id)
            if sentence:
                sentence.display_order = old_order
                session.add(sentence)
        session.commit()
        session.flush()

    @classmethod
    def recalculate_project_structure(cls, project_id: int) -> None:
        """
        Recalculate paragraph order for all paragraphs in a project.
        """
        session = cls._get_session()
        from oeapp.models.project import Project
        project = Project.get(project_id)
        if not project:
            return

        for chapter in project.chapters:
            for section in chapter.sections:
                for i, paragraph in enumerate(section.paragraphs, 1):
                    paragraph.order = i
                    session.add(paragraph)
        
        session.commit()
        session.flush()

    def to_json(self) -> dict:
        """
        Serialize sentence to JSON-compatible dictionary (without PKs).

        Args:
            session: SQLAlchemy session (needed for token lookups in notes)

        Returns:
            Dictionary containing sentence data with tokens and notes

        """
        sentence_data: dict = {
            "display_order": self.display_order,
            "paragraph_id": self.paragraph_id,
            "text_oe": self.text_oe,
            "text_modern": self.text_modern,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
            "tokens": [],
            "notes": [],
        }
        # Sort tokens by order_index
        tokens = sorted(self.tokens, key=lambda t: t.order_index)
        for token in tokens:
            sentence_data["tokens"].append(token.to_json())

        # Add notes
        for note in self.notes:
            note_data = note.to_json()
            sentence_data["notes"].append(note_data)

        return sentence_data

    @classmethod
    def from_json(cls, project_id: int, sentence_data: dict) -> Sentence:
        """
        Create a sentence and all related entities from JSON import data.

        Args:
            project_id: Project ID to attach sentence to
            sentence_data: Sentence data dictionary from JSON

        Returns:
            Created Sentence entity

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(cls.__name__)

        sentence = cls(
            project_id=project_id,
            display_order=sentence_data["display_order"],
            paragraph_id=sentence_data.get("paragraph_id"),
            text_oe=sentence_data["text_oe"],
            text_modern=sentence_data.get("text_modern"),
        )
        created_at = from_utc_iso(sentence_data.get("created_at"))
        if created_at:
            sentence.created_at = created_at
        updated_at = from_utc_iso(sentence_data.get("updated_at"))
        if updated_at:
            sentence.updated_at = updated_at

        sentence.save()

        # Create tokens and build token map
        token_map: dict[int, Token] = {}
        for token_data in sentence_data.get("tokens", []):
            token = Token.from_json(sentence.id, token_data)
            token_map[token.order_index] = token

        # Create notes
        for note_data in sentence_data.get("notes", []):
            Note.from_json(sentence.id, note_data, token_map)

        logger.info(
            "sentence.from_json",
            project_id=sentence.project_id,
            project_name=sentence.project.name,
            sentence_id=sentence.id,
            sentence_number=sentence.display_order,
            text_oe=sentence.text_oe,
            text_modern=sentence.text_modern,
        )
        return sentence

    def update(self, text_oe: str, commit: bool = True) -> builtins.list[str]:  # noqa: FBT001, FBT002
        """
        Update the sentence.

        Args:
            text_oe: New Old English text

        Keyword Args:
            commit: Whether to commit the changes to the database

        Returns:
            List of messages about changes (e.g. deleted idioms)

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)

        session = self._get_session()
        self.text_oe = text_oe
        messages = Token.update_from_sentence(text_oe, self.id)
        if commit:
            session.commit()
        # Refresh to get updated tokens
        session.refresh(self)
        logger.info(
            "sentence.update",
            sentence_id=self.id,
            project_id=self.project_id,
            project_name=self.project.name,
            sentence_number=self.display_order,
            text_oe=self.text_oe,
            text_modern=self.text_modern,
        )
        return messages

    def save(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Save the sentence.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)

        super().save(commit=commit)
        logger.info(
            "sentence.saved",
            project_id=self.project_id,
            project_name=self.project.name,
            sentence_id=self.id,
            sentence_number=self.display_order,
            text_oe=self.text_oe,
            text_modern=self.text_modern,
        )

    def delete(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Delete the sentence.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)
        super().delete(commit=commit)
        logger.info(
            "sentence.deleted",
            project_id=self.project_id,
            project_name=self.project.name,
            sentence_id=self.id,
            sentence_number=self.display_order,
            text_oe=self.text_oe,
            text_modern=self.text_modern,
        )

    def _sort_notes_by_position(
        self, notes: builtins.list[Note]
    ) -> builtins.list[Note]:
        """
        Sort notes by their position in the sentence (by start token order_index).

        Args:
            notes: List of notes to sort

        Returns:
            Sorted list of notes

        """
        if not self.tokens:
            return notes

        # Build token ID to order_index mapping
        token_id_to_order: dict[int, int] = {}
        for token in self.tokens:
            if token.id:
                token_id_to_order[token.id] = token.order_index

        def get_note_position(note: Note) -> int:
            """
            Get position of note in sentence based on start token.

            Args:
                note: Note to get position of

            Returns:
                Position of note

            """
            if note.start_token and note.start_token in token_id_to_order:
                return token_id_to_order[note.start_token]
            # Fallback to end_token if start_token not found
            if note.end_token and note.end_token in token_id_to_order:
                return token_id_to_order[note.end_token]
            # Fallback to very high number if neither found
            return 999999

        return sorted(notes, key=get_note_position)

    @property
    def sorted_notes(self) -> builtins.list[Note]:
        """
        Get the notes for the sentence, sorted by start token order_index.

        Returns:
            List of notes

        """
        return self._sort_notes_by_position(list(self.notes) if self.notes else [])

    @property
    def sorted_tokens(self) -> tuple[builtins.list[Token], dict[int, int]]:
        """
        Return the tokens for the sentence, sorted by their actual position in
        the text.

        Returns:
            Sorted list of tokens

        """
        sorted_tokens = sorted(self.tokens, key=lambda t: t.order_index)
        current_pos = 0
        token_id_to_start: dict[int, int] = {}
        for token in sorted_tokens:
            # Find next occurrence of token's surface sequentially
            pos = self.text_oe.find(token.surface, current_pos)
            if pos != -1:
                token_id_to_start[cast("int", token.id)] = pos
                current_pos = pos + len(token.surface)
            # No fallback - if it's not found sequentially, it's not where we
            # expect it.  This prevents misidentifying tokens like "of" inside
            # other words.

        # Re-sort tokens by their actual position in text to build document
        return sorted(
            [t for t in self.tokens if t.id in token_id_to_start],
            key=lambda t: token_id_to_start[cast("int", t.id)],
        ), token_id_to_start

    @property
    def token_to_note_map(self) -> dict[int, builtins.list[int]]:
        """
        Return a dict of token IDs to note IDs.

        Returns:
            dict of token IDs to note IDs

        """
        # Build mapping of token ID to note numbers
        token_to_notes: dict[int, list[int]] = {}
        for note_idx, note in enumerate(self.sorted_notes, start=1):
            if note.end_token:
                if note.end_token not in token_to_notes:
                    token_to_notes[note.end_token] = []
                token_to_notes[note.end_token].append(note_idx)
        return token_to_notes

    def get_token_surfaces(
        self, start_token: int | None = None, end_token: int | None = None
    ) -> str:
        """
        Get the text of a token range.

        If end_token is not provided, the text of the start token is returned.

        Warning:
            One issue with this method is that it does not handle punctuation in
            the sentence correctly; it just returns the surface form of the
            tokens minus punctuation, nor does it deal with whitespace properly,
            so poetry will be messed up.

        Keyword Args:
            start_token: Start token ID
            end_token: End token ID

        Returns:
            Text of the token range

        """
        if not start_token or not end_token:
            return ""
        # Ensure start and end tokens are in the sentence
        sentence_token_ids: builtins.dict[int, Token] = {
            token.id: token for token in self.tokens
        }
        if start_token not in sentence_token_ids:
            msg = f"Start token ID {start_token} not found in sentence"
            raise ValueError(msg)
        if end_token and end_token not in sentence_token_ids:
            msg = f"End token ID {end_token} not found in sentence"
            raise ValueError(msg)
        if not end_token or start_token == end_token:
            return sentence_token_ids[start_token].surface

        # Get tokens in range between start and end tokens
        tokens: builtins.list[Token] = []
        in_range = False
        for token in sorted(self.tokens, key=lambda t: t.order_index):
            if token.id == start_token:
                in_range = True
            if in_range:
                tokens.append(token)
            if token.id == end_token:
                break

        return " ".join(token.surface for token in tokens)

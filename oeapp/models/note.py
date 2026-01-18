"""Note model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, reconstructor, relationship

from oeapp.db import Base
from oeapp.models.mixins import SaveDeleteMixin
from oeapp.models.token import Token
from oeapp.utils import from_utc_iso, to_utc_iso

if TYPE_CHECKING:
    from oeapp.models.sentence import Sentence


class Note(SaveDeleteMixin, Base):
    """
    Represents a note attached to tokens, spans, or sentences.
    """

    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint(
            "note_type IN ('token','span','sentence')", name="ck_notes_note_type"
        ),
    )

    #: The note ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The sentence ID.
    sentence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False
    )
    #: The start token ID.
    start_token: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True
    )
    #: The end token ID.
    end_token: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True
    )
    #: The note text in Markdown format.
    note_text_md: Mapped[str] = mapped_column(String, nullable=False, default="")
    #: The note type.
    note_type: Mapped[str] = mapped_column(
        String, nullable=False, default="token"
    )  # token, span, sentence
    #: The date and time the note was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    #: The date and time the note was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    sentence: Mapped["Sentence"] = relationship("Sentence", back_populates="notes")
    start_token_rel: Mapped[Token | None] = relationship(
        "Token", foreign_keys=[start_token]
    )
    end_token_rel: Mapped[Token | None] = relationship(
        "Token", foreign_keys=[end_token]
    )

    @reconstructor
    def _sanitize_foreign_keys(self) -> None:
        """
        Sanitize foreign key values when object is reconstructed from database.

        Ensures that nullable foreign keys are None instead of 0 or False,
        which can cause SQLAlchemy mapping errors.
        """
        # Convert 0 or False to None for nullable foreign keys
        if self.start_token == 0 or self.start_token is False:
            self.start_token = None
        if self.end_token == 0 or self.end_token is False:
            self.end_token = None

    @classmethod
    def get(cls, pk: int) -> "Note | None":
        """
        Get a note by ID.

        Args:
            session: SQLAlchemy session
            pk: Primary key

        Returns:
            Note or None if not found

        """
        session = cls._get_session()
        return session.get(cls, pk)

    def to_json(self) -> dict:
        """
        Serialize note to JSON-compatible dictionary (without PKs).

        Args:
            session: SQLAlchemy session (needed for token lookups)

        Returns:
            Dictionary containing note data

        """
        note_data: dict = {
            "note_text_md": self.note_text_md,
            "note_type": self.note_type,
            "created_at": to_utc_iso(self.created_at),
            "updated_at": to_utc_iso(self.updated_at),
        }

        # For notes, we need to reference tokens by order_index
        # since we don't have PKs
        if self.start_token:
            start_token = Token.get(self.start_token)
            if start_token:
                note_data["start_token_order_index"] = start_token.order_index
        if self.end_token:
            end_token = Token.get(self.end_token)
            if end_token:
                note_data["end_token_order_index"] = end_token.order_index

        return note_data

    @classmethod
    def from_json(
        cls,
        sentence_id: int,
        note_data: dict,
        token_map: dict[int, Token],
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> "Note":
        """
        Create a note from JSON import data.

        Args:
            sentence_id: Sentence ID to attach note to
            note_data: Note data dictionary from JSON
            token_map: Map of order_index to Token entities

        Keyword Args:
            commit: Whether to commit the changes

        Returns:
            Created Note entity

        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(cls.__name__)

        note = cls(
            sentence_id=sentence_id,
            note_text_md=note_data["note_text_md"],
            note_type=note_data.get("note_type", "token"),
        )
        created_at = from_utc_iso(note_data.get("created_at"))
        if created_at:
            note.created_at = created_at
        updated_at = from_utc_iso(note_data.get("updated_at"))
        if updated_at:
            note.updated_at = updated_at

        # Resolve token references by order_index
        # Ensure None instead of False or 0 for nullable foreign keys
        if "start_token_order_index" in note_data:
            order_idx = note_data["start_token_order_index"]
            if order_idx in token_map and token_map[order_idx].id:
                note.start_token = token_map[order_idx].id
            else:
                note.start_token = None
        else:
            note.start_token = None

        if "end_token_order_index" in note_data:
            order_idx = note_data["end_token_order_index"]
            if order_idx in token_map and token_map[order_idx].id:
                note.end_token = token_map[order_idx].id
            else:
                note.end_token = None
        else:
            note.end_token = None
        if note.sentence is not None:
            logger.info(
                "note.from_json",
                project_id=note.sentence.project_id,
                project_name=note.sentence.project.name,
                sentence_id=note.sentence_id,
                sentence_number=note.sentence.display_order,
                start_token_id=note.start_token,
                note_id=note.id,
                oe_text=note.sentence.get_token_surfaces(
                    note.start_token,
                    note.end_token,
                ),
                md_text=note.note_text_md,
            )
        note.save(commit=commit)
        return note

    def save(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Save the note.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)

        super().save(commit=commit)
        logger.info(
            "note.saved",
            project_id=self.sentence.project_id,
            project_name=self.sentence.project.name,
            note_id=self.id,
            sentence_id=self.sentence_id,
            oe_text=self.sentence.get_token_surfaces(
                self.start_token,
                self.end_token,
            ),
            md_text=self.note_text_md,
        )

    def delete(self, commit: bool = True) -> None:  # noqa: FBT001, FBT002
        """
        Delete the note.
        """
        # Import here to avoid circular import
        from oeapp.services.logs import get_logger  # noqa: PLC0415

        logger = get_logger(self.__class__.__name__)
        super().delete(commit=commit)
        logger.info(
            "note.deleted",
            project_id=self.sentence.project_id,
            project_name=self.sentence.project.name,
            note_id=self.id,
            sentence_id=self.sentence_id,
            oe_text=self.sentence.get_token_surfaces(
                self.start_token,
                self.end_token,
            ),
            md_text=self.note_text_md,
        )

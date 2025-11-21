"""Note model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base

if TYPE_CHECKING:
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class Note(Base):
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
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the note was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="notes")
    start_token_rel: Mapped[Token | None] = relationship(
        "Token", foreign_keys=[start_token]
    )
    end_token_rel: Mapped[Token | None] = relationship(
        "Token", foreign_keys=[end_token]
    )

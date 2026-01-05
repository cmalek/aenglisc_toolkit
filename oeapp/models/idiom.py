"""Idiom model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base

from .mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.models.sentence import Sentence
    from oeapp.models.token import Token


class Idiom(SaveDeleteMixin, Base):
    """Represents a multi-token group (idiom) in a sentence."""

    __tablename__ = "idioms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The sentence ID.
    sentence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False
    )
    #: The start token ID for the idiom in the sentence.
    start_token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    #: The end token ID for the idiom in the sentence.
    end_token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False
    )
    #: The date and time the idiom was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False
    )
    #: The date and time the idiom was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="idioms")
    start_token: Mapped[Token] = relationship("Token", foreign_keys=[start_token_id])
    end_token: Mapped[Token] = relationship("Token", foreign_keys=[end_token_id])
    annotation: Mapped[Annotation | None] = relationship(
        "Annotation",
        back_populates="idiom",
        uselist=False,
        cascade="all, delete-orphan",
    )

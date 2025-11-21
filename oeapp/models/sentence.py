"""Sentence model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.token import Token

if TYPE_CHECKING:
    from oeapp.models.note import Note
    from oeapp.models.project import Project


class Sentence(Base):
    """
    Represents a sentence.

    A sentences has these characteristics:
    - A project ID
    - A display order
    - An Old English text
    - A Modern English translation
    - A list of tokens
    - A list of notes

    A sentence is related to a project by the project ID.
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
    #: The display order of the sentence in the project.
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The Old English text.
    text_oe: Mapped[str] = mapped_column(String, nullable=False)
    #: The Modern English translation.
    text_modern: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the sentence was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the sentence was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="sentences")
    tokens: Mapped[list[Token]] = relationship(
        "Token",
        back_populates="sentence",
        cascade="all, delete-orphan",
        order_by="Token.order_index",
        lazy="select",  # Load tokens when accessed
    )
    notes: Mapped[list[Note]] = relationship(
        "Note", back_populates="sentence", cascade="all, delete-orphan"
    )

    @classmethod
    def create(
        cls, session: Session, project_id: int, display_order: int, text_oe: str
    ) -> Sentence:
        """
        Import an entire OE text into a project.

        The text is split into sentences and each sentence is imported into
        the project.  The display order is the index of the sentence in the
        text.

        Args:
            session: SQLAlchemy session
            project_id: Project ID
            display_order: Display order
            text_oe: Old English text

        Returns:
            The new :class:`~oeapp.models.sentence.Sentence` object

        """
        sentence = cls(
            project_id=project_id,
            display_order=display_order,
            text_oe=text_oe,
        )
        session.add(sentence)
        session.flush()  # Get the ID

        # Create tokens from sentence text
        tokens = Token.create_from_sentence(
            session=session, sentence_id=sentence.id, sentence_text=text_oe
        )
        sentence.tokens = tokens

        session.commit()
        return sentence

    def update(self, session, text_oe: str) -> Sentence:
        """
        Update the sentence.

        Args:
            session: SQLAlchemy session
            text_oe: New Old English text

        Returns:
            Updated sentence

        """
        self.text_oe = text_oe
        Token.update_from_sentence(session, text_oe, self.id)
        session.commit()
        # Refresh to get updated tokens
        session.refresh(self)
        return self

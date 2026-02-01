"""Paragraph model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.models.section import Section
    from oeapp.models.sentence import Sentence


class Paragraph(SaveDeleteMixin, Base):
    """
    Represents a paragraph within a section.
    """

    __tablename__ = "paragraphs"

    #: The paragraph ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The section ID.
    section_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False
    )
    #: The paragraph order within the section (1-based).
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    @classmethod
    def get(cls, paragraph_id: int) -> Paragraph | None:
        """
        Get a paragraph by ID.
        """
        session = cls._get_session()
        return session.get(cls, paragraph_id)

    # Relationships
    section: Mapped[Section] = relationship("Section", back_populates="paragraphs")
    sentences: Mapped[list[Sentence]] = relationship(
        "Sentence",
        back_populates="paragraph",
        order_by="Sentence.display_order",
    )

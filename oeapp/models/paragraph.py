"""Paragraph model."""

from __future__ import annotations

import builtins
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from collections.abc import Sequence

    from oeapp.models.section import Section
    from oeapp.models.sentence import Sentence


class Paragraph(SaveDeleteMixin, Base):
    """
    Represents a paragraph within a section.
    """

    __tablename__ = "paragraphs"
    __table_args__ = (
        Index("idx_paragraphs_section_order", "section_id", "order"),
    )

    #: The paragraph ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The section ID.
    section_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sections.id", ondelete="CASCADE"), nullable=False
    )
    #: The paragraph order within the section (1-based).
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    section: Mapped[Section] = relationship("Section", back_populates="paragraphs")
    sentences: Mapped[builtins.list[Sentence]] = relationship(
        "Sentence",
        back_populates="paragraph",
        order_by="Sentence.display_order",
    )

    @classmethod
    def create(
        cls,
        section_id: int,
        order: int,
        sentences: list[Sentence] | None = None,
        commit: bool = True,
    ) -> Paragraph:
        """
        Create a new paragraph.

        Args:
            section_id: Section ID
            order: Paragraph order

        Keyword Args:
            sentences: The sentences to add to the paragraph
            commit: Whether to commit the changes to the database

        Returns:
            The new :class:`~oeapp.models.paragraph.Paragraph` object

        """
        session = cls._get_session()
        paragraph = cls(section_id=section_id, order=order)
        if sentences:
            paragraph.sentences = sentences
        session.add(paragraph)
        if commit:
            session.commit()
        return paragraph

    @classmethod
    def get(cls, paragraph_id: int) -> Paragraph | None:
        """
        Get a paragraph by ID.

        Args:
            paragraph_id: Paragraph ID

        Returns:
            The :class:`~oeapp.models.paragraph.Paragraph` object or None if not found

        """
        session = cls._get_session()
        return session.get(cls, paragraph_id)

    @classmethod
    def list(cls, section_id: int | None = None) -> builtins.list[Paragraph]:
        """
        Get all paragraphs by section ID.

        Keyword Args:
            section_id: Section ID

        Returns:
            List of paragraphs ordered by (Section.number, Paragraph.order)

        """
        session = cls._get_session()
        if section_id:
            stmt = select(cls).where(cls.section_id == section_id).order_by(cls.order)
        else:
            stmt = select(cls).order_by(cls.section_id, cls.order)
        return builtins.list(session.scalars(stmt).all())

    @classmethod
    def get_paragraphs_after(
        cls, section_id: int, order: int, exclude_paragraph_id: int | None = None
    ) -> Sequence[Paragraph]:
        """
        Get all paragraphs in the same section, with ``order``
        greater than the given order, excluding the given paragraph ID

        Args:
            section_id: Section ID
            order: Paragraph order

        Keyword Args:
            exclude_paragraph_id: Paragraph ID to exclude

        Returns:
            List of subsequent paragraphs

        """
        session = cls._get_session()
        if exclude_paragraph_id:
            stmt = select(cls).where(
                cls.section_id == section_id,
                cls.order > order,
                cls.id != exclude_paragraph_id,
            )
        else:
            stmt = select(cls).where(cls.section_id == section_id, cls.order > order)
        return session.scalars(stmt.order_by(cls.order)).all()

    @classmethod
    def previous_paragraph(cls, section_id: int, order: int) -> Paragraph | None:
        """
        Get the paragraph with the given order - 1 in the same section.

        Args:
            section_id: Section ID
            order: Paragraph order

        Returns:
            The previous paragraph or None if not found

        """
        session = cls._get_session()
        return session.scalar(
            select(cls)
            .where(
                cls.section_id == section_id,
                cls.order == order - 1,
            )
            .order_by(cls.order.desc())
            .limit(1)
        )

    def last_sentence_number(self) -> int:
        """
        Get the last sentence number in the paragraph (1-based).
        """
        # Import here to avoid circular import
        from oeapp.models.sentence import Sentence  # noqa: PLC0415

        session = self._get_session()
        return (
            session.scalar(
                select(func.max(Sentence.display_order)).where(
                    Sentence.paragraph_id == self.id
                )
            )
            or 0
        )

    def to_json(self) -> dict:
        """
        Serialize paragraph to JSON-compatible dictionary (without PKs).

        Returns:
            Dictionary containing paragraph data

        """
        return {
            "order": self.order,
        }

    @classmethod
    def from_json(
        cls,
        section_id: int,
        paragraph_data: dict,
        commit: bool = True,
    ) -> Paragraph:
        """
        Create paragraph from JSON import data.

        Args:
            section_id: Section ID
            paragraph_data: Paragraph data dictionary from JSON

        Keyword Args:
            commit: Whether to commit changes

        Returns:
            Created paragraph

        """
        session = cls._get_session()
        paragraph = cls(
            section_id=section_id,
            order=paragraph_data["order"],
        )
        session.add(paragraph)
        if commit:
            session.commit()
        else:
            session.flush()
        return paragraph

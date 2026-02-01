"""Section model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.models.chapter import Chapter
    from oeapp.models.paragraph import Paragraph


class Section(SaveDeleteMixin, Base):
    """
    Represents a section within a chapter.
    """

    __tablename__ = "sections"

    #: The section ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The chapter ID.
    chapter_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False
    )
    #: The section number (1-based).
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The section title.
    title: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    chapter: Mapped[Chapter] = relationship("Chapter", back_populates="sections")
    paragraphs: Mapped[list[Paragraph]] = relationship(
        "Paragraph",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Paragraph.order",
    )

    @classmethod
    def get(cls, section_id: int) -> Section | None:
        """
        Get a section by ID.
        """
        session = cls._get_session()
        return session.get(cls, section_id)

    @property
    def display_title(self) -> str:
        """
        Get the display title for the section.
        """
        if self.title:
            return self.title
        return f"Section {self.number}"

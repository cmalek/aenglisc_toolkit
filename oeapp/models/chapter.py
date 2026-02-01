"""Chapter model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.models.mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.models.project import Project
    from oeapp.models.section import Section


class Chapter(SaveDeleteMixin, Base):
    """
    Represents a chapter within a project.
    """

    __tablename__ = "chapters"

    #: The chapter ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The project ID.
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    #: The chapter number (1-based).
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The chapter title.
    title: Mapped[str | None] = mapped_column(String, nullable=True)

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="chapters")
    sections: Mapped[list[Section]] = relationship(
        "Section",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="Section.number",
    )

    @classmethod
    def get(cls, chapter_id: int) -> Chapter | None:
        """
        Get a chapter by ID.
        """
        session = cls._get_session()
        return session.get(cls, chapter_id)

    @property
    def display_title(self) -> str:
        """
        Get the display title for the chapter.
        """
        if self.title:
            return self.title
        return f"Chapter {self.number}"

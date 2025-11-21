"""Project model."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from oeapp.db import Base
from oeapp.exc import AlreadyExists
from oeapp.models.sentence import Sentence
from oeapp.services.splitter import split_sentences


class Project(Base):
    """
    Represents a project.
    """

    __tablename__ = "projects"

    #: The project ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The project name.
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    #: The date and time the project was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the project was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    sentences: Mapped[list[Sentence]] = relationship(
        "Sentence",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="Sentence.display_order",
    )

    @classmethod
    def create(
        cls, session: Session, text: str, name: str = "Untitled Project"
    ) -> Project:
        """
        Create a new project.

        Args:
            session: SQLAlchemy session
            text: Old English text to process and add to the project

        Keyword Args:
            name: Project name

        Returns:
            The new :class:`~oeapp.models.project.Project` object

        """
        # Check if project with this name already exists

        existing = session.scalar(select(cls).where(cls.name == name))
        if existing:
            raise AlreadyExists("Project", name)  # noqa: EM101

        # Create project
        project = cls(name=name)
        session.add(project)
        session.flush()  # Get the ID

        sentences_text = split_sentences(text)
        for order, sentence_text in enumerate(sentences_text, 1):
            Sentence.create(
                session=session,
                project_id=project.id,
                display_order=order,
                text_oe=sentence_text,
            )

        session.commit()
        return project

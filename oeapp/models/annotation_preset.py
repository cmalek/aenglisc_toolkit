"""Annotation preset model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    String,
    UniqueConstraint,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column

from oeapp.db import Base

from .mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.types import PresetPos


class AnnotationPreset(SaveDeleteMixin, Base):
    """Represents a user-defined preset for annotation fields."""

    __tablename__ = "annotation_presets"
    __table_args__ = (
        UniqueConstraint("name", "pos", name="uq_annotation_presets_name_pos"),
        CheckConstraint(
            "pos IN ('N','V','A','R','D')", name="ck_annotation_presets_pos"
        ),
    )

    #: The preset ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The preset name.
    name: Mapped[str] = mapped_column(String, nullable=False)
    #: The Part of Speech.
    pos: Mapped[str] = mapped_column(String, nullable=False)  # N, V, A, R, D
    #: The gender.
    gender: Mapped[str | None] = mapped_column(String, nullable=True)  # m, f, n
    #: The number.
    number: Mapped[str | None] = mapped_column(String, nullable=True)  # s, p
    #: The case (using db_column_name to handle reserved keyword).
    case: Mapped[str | None] = mapped_column(
        String, nullable=True, name="case"
    )  # n, a, g, d, i
    #: The declension.
    declension: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The article type.
    article_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # d, i, p, D
    #: The pronoun type.
    pronoun_type: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, r, d, i
    #: The pronoun number.
    pronoun_number: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # s, d, pl
    #: The verb class.
    verb_class: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The verb tense.
    verb_tense: Mapped[str | None] = mapped_column(String, nullable=True)  # p, n
    #: The verb person.
    verb_person: Mapped[str | None] = mapped_column(String, nullable=True)  # 1, 2, 3
    #: The verb mood.
    verb_mood: Mapped[str | None] = mapped_column(String, nullable=True)  # i, s, imp
    #: The verb aspect.
    verb_aspect: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, f, prg, gn
    #: The verb form.
    verb_form: Mapped[str | None] = mapped_column(String, nullable=True)  # f, i, p
    #: The adjective inflection.
    adjective_inflection: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # s, w
    #: The adjective degree.
    adjective_degree: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, c, s
    #: The date and time the preset was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, nullable=False
    )
    #: The date and time the preset was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    @classmethod
    def create(
        cls,
        name: str,
        pos: PresetPos,
        commit: bool = True,  # noqa: FBT001, FBT002
        **kwargs,
    ) -> AnnotationPreset:
        """
        Create a new preset.

        Args:
            name: Preset name
            pos: Part of speech (N, V, A, R, D)

        Keyword Args:
            commit: Whether to commit the changes
            **kwargs: Field values for the preset

        Returns:
            Created AnnotationPreset entity

        Raises:
            ValueError: If name is empty or pos is invalid
            sqlalchemy.exc.IntegrityError: If preset with same name and pos
                already exists

        """
        if not name or not name.strip():
            msg = "Preset name cannot be empty"
            raise ValueError(msg)
        if pos not in ("N", "V", "A", "R", "D"):
            msg = f"Invalid POS: {pos}. Must be one of: N, V, A, R, D"
            raise ValueError(msg)

        session = cls._get_session()
        preset = cls(name=name.strip(), pos=pos, **kwargs)
        session.add(preset)
        session.flush()
        if commit:
            session.commit()
        return preset

    @classmethod
    def get(cls, preset_id: int) -> AnnotationPreset | None:
        """
        Get a preset by ID.

        Args:
            session: SQLAlchemy session
            preset_id: Preset ID

        Returns:
            AnnotationPreset or None if not found

        """
        session = cls._get_session()
        return session.get(cls, preset_id)

    @classmethod
    def get_all_by_pos(cls, pos: str) -> list[AnnotationPreset]:
        """
        Get all presets for a POS, ordered by name.

        Args:
            session: SQLAlchemy session
            pos: Part of speech (N, V, A, R, D)

        Returns:
            List of AnnotationPreset entities ordered by name

        """
        session = cls._get_session()
        return list(
            session.scalars(select(cls).where(cls.pos == pos).order_by(cls.name)).all()
        )

    @classmethod
    def update(
        cls,
        preset_id: int,
        commit: bool = True,  # noqa: FBT001, FBT002
        **kwargs,
    ) -> AnnotationPreset | None:
        """
        Update a preset.

        Args:
            preset_id: Preset ID

        Keyword Args:
            commit: Whether to commit the changes
            **kwargs: Field values to update

        Returns:
            Updated AnnotationPreset entity or None if not found

        Raises:
            sqlalchemy.exc.IntegrityError: If name change would create duplicate

        """
        session = cls._get_session()
        preset = cls.get(preset_id)
        if not preset:
            return None

        for key, value in kwargs.items():
            if hasattr(preset, key):
                setattr(preset, key, value)

        session.add(preset)
        session.flush()
        if commit:
            session.commit()
        return preset

    def to_json(self) -> dict:
        """
        Serialize preset to dictionary with all field values.

        Returns:
            Dictionary containing preset data

        """
        return {
            "id": self.id,
            "name": self.name,
            "pos": self.pos,
            "gender": self.gender,
            "number": self.number,
            "case": self.case,
            "declension": self.declension,
            "article_type": self.article_type,
            "pronoun_type": self.pronoun_type,
            "pronoun_number": self.pronoun_number,
            "verb_class": self.verb_class,
            "verb_tense": self.verb_tense,
            "verb_person": self.verb_person,
            "verb_mood": self.verb_mood,
            "verb_aspect": self.verb_aspect,
            "verb_form": self.verb_form,
            "adjective_inflection": self.adjective_inflection,
            "adjective_degree": self.adjective_degree,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

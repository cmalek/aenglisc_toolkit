"""Annotation model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    select,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base
from oeapp.mixins import AnnotationTextualMixin
from oeapp.utils import from_utc_iso, to_utc_iso

from .mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.models.idiom import Idiom
    from oeapp.models.token import Token


class Annotation(AnnotationTextualMixin, SaveDeleteMixin, Base):
    """Represents grammatical/morphological annotations for a token or idiom."""

    __tablename__ = "annotations"
    __table_args__ = (
        CheckConstraint(
            "pos IN ('N','V','A','R','D','B','C','E','I', 'L')",
            name="ck_annotations_pos",
        ),
        CheckConstraint("gender IN ('m','f','n')", name="ck_annotations_gender"),
        CheckConstraint("number IN ('s','p')", name="ck_annotations_number"),
        CheckConstraint(
            "\"case\" IN ('n','a','g','d','i')", name="ck_annotations_case"
        ),
        CheckConstraint(
            "pronoun_type IN ('p','rx','r','d','i', 'm')",
            name="ck_annotations_pronoun_type",
        ),
        CheckConstraint(
            "pronoun_number IN ('s','d','pl')", name="ck_annotations_pronoun_number"
        ),
        CheckConstraint(
            "article_type IN ('d','i','p','D')", name="ck_annotations_article_type"
        ),
        CheckConstraint(
            "verb_class IN ('a','w1','w2','w3','pp','s1','s2','s3','s4','s5','s6','s7')",  # noqa: E501
            name="ck_annotations_verb_class",
        ),
        CheckConstraint("verb_tense IN ('p','n')", name="ck_annotations_verb_tense"),
        CheckConstraint(
            "verb_person IN ('1','2','3')", name="ck_annotations_verb_person"
        ),
        CheckConstraint(
            "verb_mood IN ('i','s','imp')", name="ck_annotations_verb_mood"
        ),
        CheckConstraint(
            "verb_aspect IN ('p','f','prg','gn')", name="ck_annotations_verb_aspect"
        ),
        CheckConstraint(
            "verb_form IN ('f','i','p','ii')", name="ck_annotations_verb_form"
        ),
        CheckConstraint(
            "prep_case IN ('a','d','g','i')", name="ck_annotations_prep_case"
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100", name="ck_annotations_confidence"
        ),
        CheckConstraint(
            "adjective_inflection IN ('s','w')",
            name="ck_annotations_adjective_inflection",
        ),
        CheckConstraint(
            "adjective_degree IN ('p','c','s')", name="ck_annotations_adjective_degree"
        ),
        CheckConstraint(
            "conjunction_type IN ('c','s')", name="ck_annotations_conjunction_type"
        ),
        CheckConstraint(
            "adverb_degree IN ('p','c','s')", name="ck_annotations_adverb_degree"
        ),
    )

    #: The annotation ID (primary key).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The token ID (foreign key).
    token_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True
    )
    #: The idiom ID (foreign key).
    idiom_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("idioms.id", ondelete="CASCADE"), nullable=True
    )
    #: The Part of Speech.
    pos: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # N, V, A, R, D, B, C, E, I
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
    )  # 1, 2, pl
    #: The verb class.
    verb_class: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The verb tense.
    verb_tense: Mapped[str | None] = mapped_column(String, nullable=True)  # p, n
    #: The verb person.
    verb_person: Mapped[str | None] = mapped_column(String, nullable=True)  # 1, 2,
    #: The verb mood.
    verb_mood: Mapped[str | None] = mapped_column(String, nullable=True)  # i, s, imp
    #: The verb aspect.
    verb_aspect: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, f, prg, gn
    #: The verb form.
    verb_form: Mapped[str | None] = mapped_column(String, nullable=True)  # f, i, p
    #: The preposition case.
    prep_case: Mapped[str | None] = mapped_column(String, nullable=True)  # a, d, g
    #: The adjective inflection.
    adjective_inflection: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # s, w
    #: The adjective degree.
    adjective_degree: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # p, c, s
    #: The conjuncion type.
    conjunction_type: Mapped[str | None] = mapped_column(String, nullable=True)  # c, s
    #: The adverb degree.
    adverb_degree: Mapped[str | None] = mapped_column(String, nullable=True)  # p, c, s
    #: The confidence in the annotation.
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100
    #: The last inferred JSON.
    last_inferred_json: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The modern English meaning.
    modern_english_meaning: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The root.
    root: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The date and time the annotation was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    # Relationships
    token: Mapped[Token] = relationship("Token", back_populates="annotation")
    idiom: Mapped[Idiom] = relationship("Idiom", back_populates="annotation")

    @classmethod
    def exists(cls, token_id: int | None = None, idiom_id: int | None = None) -> bool:
        """Check if an annotation exists for a token or idiom."""
        session = cls._get_session()
        stmt = select(cls)
        if token_id is not None:
            stmt = stmt.where(cls.token_id == token_id)
        elif idiom_id is not None:
            stmt = stmt.where(cls.idiom_id == idiom_id)
        else:
            return False
        return session.scalar(stmt) is not None

    @classmethod
    def get(cls, annotation_id: int) -> Annotation | None:
        """Get an annotation by ID."""
        session = cls._get_session()
        return session.get(cls, annotation_id)

    @classmethod
    def get_by_token(cls, token_id: int) -> Annotation | None:
        """Get an annotation by token ID."""
        session = cls._get_session()
        return session.scalar(select(cls).where(cls.token_id == token_id))

    @classmethod
    def get_by_idiom(cls, idiom_id: int) -> Annotation | None:
        """Get an annotation by idiom ID."""
        session = cls._get_session()
        return session.scalar(select(cls).where(cls.idiom_id == idiom_id))

    def to_json(self) -> dict:
        """Serialize annotation to JSON-compatible dictionary."""
        data = {
            column.name: getattr(self, column.name)
            for column in self.__class__.__table__.columns
        }
        data["updated_at"] = to_utc_iso(self.updated_at)
        return data

    @classmethod
    def from_json(
        cls,
        token_id: int | None,
        ann_data: dict,
        idiom_id: int | None = None,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> Annotation:
        """
        Create an annotation from JSON import data.

        Args:
            token_id: Token ID
            ann_data: Annotation data
            idiom_id: Idiom ID
            commit: Whether to commit the annotation to the database

        Returns:
            Annotation

        """
        annotation = None
        if token_id is not None and idiom_id is not None:
            msg = "Either token_id or idiom_id must be provided, not both"
            raise ValueError(msg)
        if token_id is None and idiom_id is None:
            msg = "Either token_id or idiom_id must be provided"
            raise ValueError(msg)
        if token_id is not None:
            annotation = Annotation.get_by_token(token_id)
        if annotation is None and idiom_id is not None:
            annotation = Annotation.get_by_idiom(idiom_id)
        if annotation is None:
            annotation = cls(
                token_id=token_id,
                idiom_id=idiom_id,
                **cls._extract_base_fields_from_json(ann_data),
            )
        else:
            valid_fields = {column.name for column in cls.__table__.columns}
            # Check for invalid fields in ann_data
            for key in ann_data:
                if key != "updated_at" and key not in valid_fields:
                    msg = f"Invalid annotation field: {key}"
                    raise ValueError(msg)

            for key, value in cls._extract_base_fields_from_json(ann_data).items():
                setattr(annotation, key, value)
        updated_at = from_utc_iso(ann_data.get("updated_at"))
        if updated_at:
            annotation.updated_at = updated_at
        annotation.save(commit=commit)
        return annotation

    def from_annotation(
        self,
        annotation: Annotation,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> Annotation:
        """
        Update or create an annotation from an existing annotation.

        Args:
            annotation: Existing annotation
            commit: Whether to commit the annotation to the database

        Returns:
            Annotation

        """
        if annotation.token_id is not None and annotation.idiom_id is not None:
            msg = "Either token_id or idiom_id must be provided, not both"
            raise ValueError(msg)
        if annotation.token_id is None and annotation.idiom_id is None:
            msg = "Either token_id or idiom_id must be provided"
            raise ValueError(msg)
        if self.token_id is not None and self.token_id != annotation.token_id:
            msg = "Token ID mismatch"
            raise ValueError(msg)
        if self.idiom_id is not None and self.idiom_id != annotation.idiom_id:
            msg = "Idiom ID mismatch"
            raise ValueError(msg)
        self.pos = annotation.pos
        self.gender = annotation.gender
        self.number = annotation.number
        self.case = annotation.case
        self.declension = annotation.declension
        self.article_type = annotation.article_type
        self.pronoun_type = annotation.pronoun_type
        self.pronoun_number = annotation.pronoun_number
        self.verb_class = annotation.verb_class
        self.verb_tense = annotation.verb_tense
        self.verb_person = annotation.verb_person
        self.verb_mood = annotation.verb_mood
        self.verb_aspect = annotation.verb_aspect
        self.verb_form = annotation.verb_form
        self.prep_case = annotation.prep_case
        self.adjective_inflection = annotation.adjective_inflection
        self.adjective_degree = annotation.adjective_degree
        self.conjunction_type = annotation.conjunction_type
        self.adverb_degree = annotation.adverb_degree
        self.confidence = annotation.confidence
        self.last_inferred_json = annotation.last_inferred_json
        self.modern_english_meaning = annotation.modern_english_meaning
        self.root = annotation.root
        if commit:
            self.save()
        return self

    @classmethod
    def _extract_base_fields_from_json(cls, ann_data: dict) -> dict:
        """Extract base annotation fields from JSON data."""
        return {
            "pos": ann_data.get("pos"),
            "gender": ann_data.get("gender"),
            "number": ann_data.get("number"),
            "case": ann_data.get("case"),
            "declension": ann_data.get("declension"),
            "article_type": ann_data.get("article_type"),
            "pronoun_type": ann_data.get("pronoun_type"),
            "pronoun_number": ann_data.get("pronoun_number"),
            "verb_class": ann_data.get("verb_class"),
            "verb_tense": ann_data.get("verb_tense"),
            "verb_person": ann_data.get("verb_person"),
            "verb_mood": ann_data.get("verb_mood"),
            "verb_aspect": ann_data.get("verb_aspect"),
            "verb_form": ann_data.get("verb_form"),
            "prep_case": ann_data.get("prep_case"),
            "adjective_inflection": ann_data.get("adjective_inflection"),
            "adjective_degree": ann_data.get("adjective_degree"),
            "conjunction_type": ann_data.get("conjunction_type"),
            "adverb_degree": ann_data.get("adverb_degree"),
            "confidence": ann_data.get("confidence"),
            "last_inferred_json": ann_data.get("last_inferred_json"),
            "modern_english_meaning": ann_data.get("modern_english_meaning"),
            "root": ann_data.get("root"),
        }

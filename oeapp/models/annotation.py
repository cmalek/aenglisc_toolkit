"""Annotation model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from oeapp.db import Base

if TYPE_CHECKING:
    from oeapp.models.token import Token


class Annotation(Base):
    """Represents grammatical/morphological annotations for a token."""

    __tablename__ = "annotations"
    __table_args__ = (
        CheckConstraint(
            "pos IN ('N','V','A','R','D','B','C','E','I')", name="ck_annotations_pos"
        ),
        CheckConstraint("gender IN ('m','f','n')", name="ck_annotations_gender"),
        CheckConstraint("number IN ('s','p')", name="ck_annotations_number"),
        CheckConstraint(
            "\"case\" IN ('n','a','g','d','i')", name="ck_annotations_case"
        ),
        CheckConstraint(
            "pronoun_type IN ('p','r','d','i')", name="ck_annotations_pronoun_type"
        ),
        CheckConstraint(
            "article_type IN ('d','i','p','D')", name="ck_annotations_article_type"
        ),
        CheckConstraint(
            "verb_class IN ('a','w1','w2','w3','s1','s2','s3','s4','s5','s6','s7')",
            name="ck_annotations_verb_class",
        ),
        CheckConstraint("verb_tense IN ('p','n')", name="ck_annotations_verb_tense"),
        CheckConstraint("verb_person IN (1,2,3)", name="ck_annotations_verb_person"),
        CheckConstraint(
            "verb_mood IN ('i','s','imp')", name="ck_annotations_verb_mood"
        ),
        CheckConstraint(
            "verb_aspect IN ('p','f','prg','gn')", name="ck_annotations_verb_aspect"
        ),
        CheckConstraint("verb_form IN ('f','i','p')", name="ck_annotations_verb_form"),
        CheckConstraint("prep_case IN ('a','d','g')", name="ck_annotations_prep_case"),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100", name="ck_annotations_confidence"
        ),
    )

    #: The token ID (primary key and foreign key).
    token_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tokens.id", ondelete="CASCADE"), primary_key=True
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
    #: The verb class.
    verb_class: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The verb tense.
    verb_tense: Mapped[str | None] = mapped_column(String, nullable=True)  # p, n
    #: The verb person.
    verb_person: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 1, 2, 3
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
    #: Whether the annotation is uncertain.
    uncertain: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    #: The alternatives in JSON format.
    alternatives_json: Mapped[str | None] = mapped_column(String, nullable=True)
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
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    # Relationships
    token: Mapped[Token] = relationship("Token", back_populates="annotation")

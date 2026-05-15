"""Remembered annotation model."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    or_,
    select,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from oeapp.db import Base
from oeapp.mixins import AnnotationTextualMixin
from oeapp.utils import normalize_old_english, to_utc_iso

from .mixins import SaveDeleteMixin

if TYPE_CHECKING:
    from oeapp.models.project import Project
    from oeapp.models.token import Token


class RememberedAnnotation(AnnotationTextualMixin, SaveDeleteMixin, Base):
    """Stored token-only annotation template keyed by exact token surface."""

    __tablename__ = "remembered_annotations"
    __table_args__ = (
        CheckConstraint(
            "pos IN ('N','V','A','R','D','B','C','E','I', 'L')",
            name="ck_remembered_annotations_pos",
        ),
        CheckConstraint(
            "gender IN ('m','f','n')", name="ck_remembered_annotations_gender"
        ),
        CheckConstraint(
            "number IN ('s','p')", name="ck_remembered_annotations_number"
        ),
        CheckConstraint(
            "\"case\" IN ('n','a','g','d','i')",
            name="ck_remembered_annotations_case",
        ),
        CheckConstraint(
            "declension IN ('s','w','o','i','u','ja','jo','wa','wo','pu', 'r', 'i-mut', 'er', 'nd', 'th')",  # noqa: E501
            name="ck_remembered_annotations_declension",
        ),
        CheckConstraint(
            "pronoun_type IN ('p','rx','r','d','i','m','ind')",
            name="ck_remembered_annotations_pronoun_type",
        ),
        CheckConstraint(
            "pronoun_number IN ('s','d','pl')",
            name="ck_remembered_annotations_pronoun_number",
        ),
        CheckConstraint(
            "article_type IN ('d','i','p','D')",
            name="ck_remembered_annotations_article_type",
        ),
        CheckConstraint(
            "verb_class IN ('a','w1','w2','w3','pp','s1','s2','s3','s4','s5','s6','s7')",  # noqa: E501
            name="ck_remembered_annotations_verb_class",
        ),
        CheckConstraint(
            "verb_tense IN ('p','n')", name="ck_remembered_annotations_verb_tense"
        ),
        CheckConstraint(
            "verb_person IN ('1','2','3')",
            name="ck_remembered_annotations_verb_person",
        ),
        CheckConstraint(
            "verb_mood IN ('i','s','imp')",
            name="ck_remembered_annotations_verb_mood",
        ),
        CheckConstraint(
            "verb_aspect IN ('p','f','prg','gn')",
            name="ck_remembered_annotations_verb_aspect",
        ),
        CheckConstraint(
            "verb_form IN ('f','i','p','ii')",
            name="ck_remembered_annotations_verb_form",
        ),
        CheckConstraint(
            "verb_direct_object_case IN ('n', 'a','d','g','i')",
            name="ck_remembered_annotations_verb_direct_object_case",
        ),
        CheckConstraint(
            "verb_transitivity IN ('transitive','intransitive')",
            name="ck_remembered_annotations_verb_transitivity",
        ),
        CheckConstraint(
            "prep_case IN ('a','d','g','i')",
            name="ck_remembered_annotations_prep_case",
        ),
        CheckConstraint(
            "adjective_inflection IN ('s','w')",
            name="ck_remembered_annotations_adjective_inflection",
        ),
        CheckConstraint(
            "adjective_degree IN ('p','c','s')",
            name="ck_remembered_annotations_adjective_degree",
        ),
        CheckConstraint(
            "conjunction_type IN ('c','s')",
            name="ck_remembered_annotations_conjunction_type",
        ),
        CheckConstraint(
            "adverb_degree IN ('p','c','s')",
            name="ck_remembered_annotations_adverb_degree",
        ),
        Index("idx_remembered_annotations_project_id", "project_id"),
        Index(
            "uq_remembered_annotations_global_token_text",
            "token_text",
            unique=True,
            sqlite_where=text("project_id IS NULL"),
        ),
        Index(
            "uq_remembered_annotations_project_token_text",
            "project_id",
            "token_text",
            unique=True,
            sqlite_where=text("project_id IS NOT NULL"),
        ),
    )

    #: The remembered annotation ID.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    #: The owning project ID. ``None`` means global scope.
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True
    )
    #: The exact token surface this remembered entry matches.
    token_text: Mapped[str] = mapped_column(String, nullable=False)
    #: The remembered part of speech.
    pos: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered gender.
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered number.
    number: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered case.
    case: Mapped[str | None] = mapped_column(String, nullable=True, name="case")
    #: The remembered declension.
    declension: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered article type.
    article_type: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered pronoun type.
    pronoun_type: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered pronoun number.
    pronoun_number: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered verb class.
    verb_class: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered verb tense.
    verb_tense: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered verb person.
    verb_person: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered verb mood.
    verb_mood: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered verb aspect.
    verb_aspect: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered verb form.
    verb_form: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered verb direct object case.
    verb_direct_object_case: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Whether the remembered verb requires an infinitive complement.
    verb_requires_infinitive: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    #: Whether the remembered verb is impersonal.
    verb_impersonal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    #: Whether the remembered verb is transitive or intransitive.
    verb_transitivity: Mapped[str] = mapped_column(
        String, nullable=False, default="transitive", server_default="transitive"
    )
    #: The remembered preposition case.
    prep_case: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered adjective inflection.
    adjective_inflection: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered adjective degree.
    adjective_degree: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered conjunction type.
    conjunction_type: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered adverb degree.
    adverb_degree: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered Modern English meaning.
    modern_english_meaning: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The remembered root.
    root: Mapped[str | None] = mapped_column(String, nullable=True)
    #: The normalized root.
    root_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    #: Timestamp when the remembered entry was created.
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )
    #: Timestamp when the remembered entry was last updated.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
        nullable=False,
    )

    #: Back-reference to the owning project for project-scoped entries.
    project: Mapped[Project | None] = relationship(
        "Project", back_populates="remembered_annotations"
    )

    @classmethod
    def get(cls, remembered_annotation_id: int) -> RememberedAnnotation | None:
        """Get a remembered annotation by ID."""
        return cls._get_session().get(cls, remembered_annotation_id)

    @classmethod
    def get_for_scope(
        cls, token_text: str, project_id: int | None
    ) -> RememberedAnnotation | None:
        """Get a remembered annotation for one exact token/scope pair."""
        session = cls._get_session()
        stmt = select(cls).where(cls.token_text == token_text)
        stmt = (
            stmt.where(cls.project_id.is_(None))
            if project_id is None
            else stmt.where(cls.project_id == project_id)
        )
        return session.scalar(stmt)

    @classmethod
    def list_for_scope(
        cls, project_id: int | None
    ) -> builtins.list[RememberedAnnotation]:
        """List remembered annotations for one explicit scope."""
        session = cls._get_session()
        stmt = select(cls)
        stmt = (
            stmt.where(cls.project_id.is_(None))
            if project_id is None
            else stmt.where(cls.project_id == project_id)
        )
        return builtins.list(session.scalars(stmt.order_by(cls.token_text)).all())

    @classmethod
    def effective_for_project(
        cls, project_id: int
    ) -> dict[str, RememberedAnnotation]:
        """Resolve project-visible remembered entries with project scope winning."""
        session = cls._get_session()
        stmt = (
            select(cls)
            .where(or_(cls.project_id == project_id, cls.project_id.is_(None)))
            .order_by(cls.project_id.is_(None), cls.token_text, cls.id)
        )
        resolved: dict[str, RememberedAnnotation] = {}
        for entry in session.scalars(stmt):
            resolved.setdefault(entry.token_text, entry)
        return resolved

    @classmethod
    def upsert_from_token_annotation(
        cls, token: Token, project_id: int | None
    ) -> RememberedAnnotation:
        """Upsert a remembered entry from a live token annotation."""
        if token.annotation is None:
            msg = "Cannot remember a token without an annotation"
            raise ValueError(msg)
        return cls.upsert_fields(
            token_text=token.surface,
            project_id=project_id,
            field_data=cls._sanitize_annotation_data(token.annotation.to_json()),
        )

    @classmethod
    def upsert_fields(
        cls,
        token_text: str,
        project_id: int | None,
        field_data: dict[str, Any],
    ) -> RememberedAnnotation:
        """Upsert a remembered entry from sanitized field data."""
        remembered = cls.get_for_scope(token_text, project_id)
        if remembered is None:
            remembered = cls(token_text=token_text, project_id=project_id)
        for key, value in cls._sanitize_annotation_data(field_data).items():
            setattr(remembered, key, value)
        remembered.save()
        return remembered

    @classmethod
    def from_json(
        cls, project_id: int, remembered_data: dict[str, Any], commit: bool = True
    ) -> RememberedAnnotation:
        """Create or update a project-scoped remembered annotation from JSON."""
        remembered = cls.get_for_scope(remembered_data["token_text"], project_id)
        if remembered is None:
            remembered = cls(
                project_id=project_id, token_text=remembered_data["token_text"]
            )
        for key, value in cls._sanitize_annotation_data(remembered_data).items():
            setattr(remembered, key, value)
        remembered.token_text = remembered_data["token_text"]
        remembered.save(commit=commit)
        return remembered

    @classmethod
    def matching_tokens(
        cls, project_id: int, token_texts: builtins.list[str]
    ) -> builtins.list[Token]:
        """Return project tokens whose exact surface matches remembered keys."""
        if not token_texts:
            return []
        from oeapp.models.sentence import Sentence  # noqa: PLC0415
        from oeapp.models.token import Token  # noqa: PLC0415

        session = cls._get_session()
        stmt = (
            select(Token)
            .join(Sentence)
            .where(Sentence.project_id == project_id, Token.surface.in_(token_texts))
            .order_by(Sentence.display_order, Token.order_index)
        )
        return builtins.list(session.scalars(stmt).all())

    def annotation_payload(self) -> dict[str, Any]:
        """Convert this remembered entry into replayable annotation data."""
        return self._sanitize_annotation_data(self.to_json())

    def to_json(self) -> dict[str, Any]:
        """Serialize remembered annotation to JSON-compatible data."""
        data = self._sanitize_annotation_data(
            {
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
                "verb_direct_object_case": self.verb_direct_object_case,
                "verb_requires_infinitive": self.verb_requires_infinitive,
                "verb_impersonal": self.verb_impersonal,
                "verb_transitivity": self.verb_transitivity,
                "prep_case": self.prep_case,
                "adjective_inflection": self.adjective_inflection,
                "adjective_degree": self.adjective_degree,
                "conjunction_type": self.conjunction_type,
                "adverb_degree": self.adverb_degree,
                "modern_english_meaning": self.modern_english_meaning,
                "root": self.root,
                "root_normalized": self.root_normalized,
            }
        )
        data["token_text"] = self.token_text
        data["updated_at"] = to_utc_iso(self.updated_at)
        return data

    @classmethod
    def _sanitize_annotation_data(
        cls, annotation_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Keep only replay-safe remembered fields from annotation-like data."""
        return {
            "pos": annotation_data.get("pos"),
            "gender": annotation_data.get("gender"),
            "number": annotation_data.get("number"),
            "case": annotation_data.get("case"),
            "declension": annotation_data.get("declension"),
            "article_type": annotation_data.get("article_type"),
            "pronoun_type": annotation_data.get("pronoun_type"),
            "pronoun_number": annotation_data.get("pronoun_number"),
            "verb_class": annotation_data.get("verb_class"),
            "verb_tense": annotation_data.get("verb_tense"),
            "verb_person": annotation_data.get("verb_person"),
            "verb_mood": annotation_data.get("verb_mood"),
            "verb_aspect": annotation_data.get("verb_aspect"),
            "verb_form": annotation_data.get("verb_form"),
            "verb_direct_object_case": annotation_data.get("verb_direct_object_case"),
            "verb_requires_infinitive": annotation_data.get(
                "verb_requires_infinitive", False
            ),
            "verb_impersonal": annotation_data.get("verb_impersonal", False),
            "verb_transitivity": annotation_data.get(
                "verb_transitivity", "transitive"
            ),
            "prep_case": annotation_data.get("prep_case"),
            "adjective_inflection": annotation_data.get("adjective_inflection"),
            "adjective_degree": annotation_data.get("adjective_degree"),
            "conjunction_type": annotation_data.get("conjunction_type"),
            "adverb_degree": annotation_data.get("adverb_degree"),
            "modern_english_meaning": annotation_data.get("modern_english_meaning"),
            "root": annotation_data.get("root"),
            "root_normalized": annotation_data.get(
                "root_normalized", normalize_old_english(annotation_data.get("root"))
            ),
        }

    @validates("root")
    def _sync_root_normalized(self, _key: str, value: str | None) -> str | None:
        """Keep ``root_normalized`` in sync with ``root`` updates."""
        self.root_normalized = normalize_old_english(value)
        return value

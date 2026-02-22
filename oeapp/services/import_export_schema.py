"""Pydantic schemas for project import/export JSON payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnnotationJson(BaseModel):
    """Annotation payload."""

    model_config = ConfigDict(extra="forbid")

    pos: str | None = None
    gender: str | None = None
    number: str | None = None
    case: str | None = None
    declension: str | None = None
    article_type: str | None = None
    pronoun_type: str | None = None
    pronoun_number: str | None = None
    verb_class: str | None = None
    verb_tense: str | None = None
    verb_person: str | None = None
    verb_mood: str | None = None
    verb_aspect: str | None = None
    verb_form: str | None = None
    verb_direct_object_case: str | None = None
    prep_case: str | None = None
    adjective_inflection: str | None = None
    adjective_degree: str | None = None
    conjunction_type: str | None = None
    adverb_degree: str | None = None
    confidence: int | None = None
    last_inferred_json: str | None = None
    modern_english_meaning: str | None = None
    root: str | None = None
    updated_at: str | None = None


class TokenJson(BaseModel):
    """Token payload."""

    model_config = ConfigDict(extra="forbid")

    order_index: int
    surface: str
    lemma: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    annotation: AnnotationJson | None = None


class NoteJson(BaseModel):
    """Note payload."""

    model_config = ConfigDict(extra="forbid")

    note_text_md: str
    note_type: str | None = None
    start_token_order_index: int | None = None
    end_token_order_index: int | None = None
    created_at: str | None = None
    updated_at: str | None = None


class IdiomJson(BaseModel):
    """Idiom payload."""

    model_config = ConfigDict(extra="forbid")

    start_token_order_index: int
    end_token_order_index: int
    created_at: str | None = None
    updated_at: str | None = None
    annotation: AnnotationJson | None = None


class ParagraphRefJson(BaseModel):
    """Paragraph reference payload."""

    model_config = ConfigDict(extra="forbid")

    chapter_number: int
    section_number: int
    paragraph_order: int


class SentenceJson(BaseModel):
    """Sentence payload."""

    model_config = ConfigDict(extra="forbid")

    display_order: int
    text_oe: str
    text_modern: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    paragraph_ref: ParagraphRefJson
    tokens: list[TokenJson] = []
    notes: list[NoteJson] = []
    idioms: list[IdiomJson] = []


class ParagraphJson(BaseModel):
    """Paragraph payload."""

    model_config = ConfigDict(extra="forbid")

    order: int


class SectionJson(BaseModel):
    """Section payload."""

    model_config = ConfigDict(extra="forbid")

    number: int
    title: str | None = None
    paragraphs: list[ParagraphJson] = []


class ChapterJson(BaseModel):
    """Chapter payload."""

    model_config = ConfigDict(extra="forbid")

    number: int
    title: str | None = None
    sections: list[SectionJson] = []


class ProjectJson(BaseModel):
    """Project payload."""

    model_config = ConfigDict(extra="forbid")

    name: str
    source: str | None = None
    translator: str | None = None
    notes: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    chapters: list[ChapterJson] = []


class ProjectExportPayload(BaseModel):
    """Top-level export payload."""

    model_config = ConfigDict(extra="forbid")

    export_version: Literal["2.0"]
    migration_version: str
    project: ProjectJson
    sentences: list[SentenceJson]

"""Pydantic schemas for project import/export JSON payloads."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class AnnotationJson(BaseModel):
    """Annotation payload."""

    model_config = ConfigDict(extra="forbid")

    #: The part of speech
    pos: str | None = None
    #: The gender
    gender: str | None = None
    #: The number
    number: str | None = None
    #: The case.
    case: str | None = None
    #: The declension, for nouns.
    declension: str | None = None
    #: The article type for determiners/articles.
    article_type: str | None = None
    #: The pronoun type, for pronouns.
    pronoun_type: str | None = None
    #: The pronoun number, for pronouns.
    pronoun_number: str | None = None
    #: The verb class, for verbs.
    verb_class: str | None = None
    #: The verb tense, for verbs.
    verb_tense: str | None = None
    #: The verb person, for verbs.
    verb_person: str | None = None
    #: The verb mood, for verbs.
    verb_mood: str | None = None
    #: The verb aspect, for verbs.
    verb_aspect: str | None = None
    #: The verb form, for verbs.
    verb_form: str | None = None
    #: The direct object case for a verb.
    verb_direct_object_case: str | None = None
    #: The preposition case, for prepositions.
    prep_case: str | None = None
    #: The adjective inflection, for adjectives.
    adjective_inflection: str | None = None
    #: The adjective degree, for adjectives.
    adjective_degree: str | None = None
    #: The conjunction type, for conjunctions.
    conjunction_type: str | None = None
    #: The adverb degree, for adverbs.
    adverb_degree: str | None = None
    #: The confidence in the annotation.
    confidence: int | None = None
    #: The last inferred JSON.
    last_inferred_json: str | None = None
    #: The modern English meaning.
    modern_english_meaning: str | None = None
    #: The root.
    root: str | None = None
    #: The date and time the annotation was created.
    created_at: str | None = None
    #: The date and time the annotation was last updated.
    updated_at: str | None = None


class TokenJson(BaseModel):
    """Token payload."""

    model_config = ConfigDict(extra="forbid")

    #: The order index of the token.
    order_index: int
    #: The surface form of the token.
    surface: str
    #: The lemma of the token.
    lemma: str | None = None
    #: The date and time the token was created.
    created_at: str | None = None
    #: The date and time the token was last updated.
    updated_at: str | None = None
    #: The annotation for the token.
    annotation: AnnotationJson | None = None


class NoteJson(BaseModel):
    """Note payload."""

    model_config = ConfigDict(extra="forbid")

    #: The text of the note.
    note_text_md: str
    #: The type of the note.
    note_type: str | None = None
    #: The start token order index.
    start_token_order_index: int | None = None
    #: The end token order index.
    end_token_order_index: int | None = None
    #: The date and time the note was created.
    created_at: str | None = None
    #: The date and time the note was last updated.
    updated_at: str | None = None


class IdiomJson(BaseModel):
    """Idiom payload."""

    model_config = ConfigDict(extra="forbid")

    #: The start token order index.
    start_token_order_index: int
    #: The end token order index.
    end_token_order_index: int
    #: The date and time the idiom was created.
    created_at: str | None = None
    #: The date and time the idiom was last updated.
    updated_at: str | None = None
    #: The annotation for the idiom.
    annotation: AnnotationJson | None = None


class ParagraphRefJson(BaseModel):
    """Paragraph reference payload."""

    model_config = ConfigDict(extra="forbid")

    #: The chapter number.
    chapter_number: int
    #: The section number.
    section_number: int
    #: The paragraph order.
    paragraph_order: int


class SentenceJson(BaseModel):
    """Sentence payload."""

    model_config = ConfigDict(extra="forbid")

    #: The display order of the sentence.
    display_order: int
    #: The Old English text of the sentence.
    text_oe: str
    #: The Modern English text of the sentence.
    text_modern: str | None = None
    #: The date and time the sentence was created.
    created_at: str | None = None
    #: The date and time the sentence was last updated.
    updated_at: str | None = None
    #: The paragraph reference.  We're using a reference back to the paragraph
    #: here because sentences have global display order and an order within the
    #: paragraph, and we don't want to mess that up by making them children of
    #: the paragraph.
    paragraph_ref: ParagraphRefJson
    #: The tokens in the sentence.
    tokens: list[TokenJson] = []
    #: The notes in the sentence.
    notes: list[NoteJson] = []
    #: The idioms in the sentence.
    idioms: list[IdiomJson] = []


class ParagraphJson(BaseModel):
    """Paragraph payload."""

    model_config = ConfigDict(extra="forbid")

    #: The order of the paragraph.
    order: int


class SectionJson(BaseModel):
    """Section payload."""

    model_config = ConfigDict(extra="forbid")

    #: The number of the section.
    number: int
    #: The title of the section.
    title: str | None = None
    #: The paragraphs in the section.
    paragraphs: list[ParagraphJson] = []


class ChapterJson(BaseModel):
    """Chapter payload."""

    model_config = ConfigDict(extra="forbid")

    #: The number of the chapter.
    number: int
    #: The title of the chapter.
    title: str | None = None
    #: The sections in the chapter.
    sections: list[SectionJson] = []


class ProjectJson(BaseModel):
    """Project payload."""

    model_config = ConfigDict(extra="forbid")

    #: The name of the project.
    name: str
    #: The source of the project.
    source: str | None = None
    #: The translator of the project.
    translator: str | None = None
    #: The notes of the project.
    notes: str | None = None
    #: The date and time the project was created.
    created_at: str | None = None
    #: The date and time the project was last updated.
    updated_at: str | None = None
    #: The chapters in the project.
    chapters: list[ChapterJson] = []


class ProjectExportPayload(BaseModel):
    """Top-level export payload."""

    model_config = ConfigDict(extra="forbid")

    #: The export version.
    export_version: Literal["2.0"]
    #: The migration version.
    migration_version: str
    #: The project.
    project: ProjectJson
    #: The sentences in the project.
    sentences: list[SentenceJson]

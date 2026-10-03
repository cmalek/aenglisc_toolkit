"""Pydantic schema for one annotation's JSON payload."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AnnotationJson(BaseModel):
    """Annotation Json for this module."""

    #: Model config.
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
    #: Whether the verb requires an infinitive complement.
    verb_requires_infinitive: bool = False
    #: Whether the verb is impersonal.
    verb_impersonal: bool = False
    #: Verb transitivity type.
    verb_transitivity: str = "transitive"
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
    #: The contextual sense for this attested instance.
    sense: str | None = None
    #: The root.
    root: str | None = None
    #: The normalized root.
    root_normalized: str | None = None
    #: The date and time the annotation was created.
    created_at: str | None = None
    #: The date and time the annotation was last updated.
    updated_at: str | None = None

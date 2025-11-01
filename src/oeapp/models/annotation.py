"""Annotation model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Annotation:
    """Represents grammatical/morphological annotations for a token."""

    token_id: int
    pos: Optional[str] = None  # N, V, A, R, D, B, C, E, I
    gender: Optional[str] = None  # m, f, n
    number: Optional[str] = None  # s, p
    case: Optional[str] = None  # n, a, g, d, i (reserved keyword, use "case" in SQL)
    declension: Optional[str] = None
    pronoun_type: Optional[str] = None  # p, r, d, i
    verb_class: Optional[str] = None
    verb_tense: Optional[str] = None  # p, n
    verb_person: Optional[int] = None  # 1, 2, 3
    verb_mood: Optional[str] = None  # i, s, imp
    verb_aspect: Optional[str] = None  # p, f, prg, gn
    verb_form: Optional[str] = None  # f, i, p
    prep_case: Optional[str] = None  # a, d, g
    uncertain: bool = False
    alternatives_json: Optional[str] = None
    confidence: Optional[int] = None  # 0-100
    last_inferred_json: Optional[str] = None
    updated_at: Optional[datetime] = None


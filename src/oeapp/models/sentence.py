"""Sentence model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Sentence:
    """Represents a sentence."""

    id: Optional[int]
    project_id: int
    display_order: int
    text_oe: str
    text_modern: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


"""Token model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Token:
    """Represents a tokenized word."""

    id: Optional[int]
    sentence_id: int
    order_index: int
    surface: str
    lemma: Optional[str] = None
    created_at: Optional[datetime] = None


"""Note model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Note:
    """Represents a note attached to tokens, spans, or sentences."""

    id: Optional[int]
    sentence_id: int
    start_token: Optional[int] = None
    end_token: Optional[int] = None
    note_text_md: str = ""
    note_type: str = "token"  # token, span, sentence
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


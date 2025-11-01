"""Project model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    """Represents a project."""

    id: Optional[int]
    name: str
    created_at: datetime
    updated_at: datetime


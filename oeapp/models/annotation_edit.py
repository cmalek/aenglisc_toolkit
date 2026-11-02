"""Before-state of one annotation modal edit."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AnnotationEdit:
    """
    The annotation fields as they were when the annotation modal opened.

    An edit carries this snapshot to the apply step, because the modal
    writes the new values onto the same annotation object.

    Args:
        before: Undo snapshot of the annotation before the edit, or empty
            when there was no annotation.

    """

    #: Undo snapshot of the annotation before the edit.
    before: dict[str, Any] = field(default_factory=dict)

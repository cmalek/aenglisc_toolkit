"""Annotation related commands."""

from dataclasses import dataclass, field
from typing import Any

from oeapp.models.annotation import Annotation
from oeapp.models.mixins import SessionMixin

from .abstract import Command


@dataclass
class AnnotateTokenCommand(SessionMixin, Command):
    """Command for annotating a token or idiom."""

    #: The token ID.
    token_id: int | None = None
    #: The before state of the annotation.
    before: dict[str, Any] = field(default_factory=dict)
    #: The after state of the annotation.
    after: dict[str, Any] = field(default_factory=dict)
    #: The idiom ID.
    idiom_id: int | None = None

    @property
    def annotation(self) -> Annotation | None:
        """
        Get the current annotation.

        IF :attr:`token_id` is not None, get the annotation by token ID.
        IF :attr:`idiom_id` is not None, get the annotation by idiom ID.
        If both are None, return None.

        Returns:
            Annotation or None if not found

        """
        if self.token_id:
            return Annotation.get_by_token(self.token_id)
        if self.idiom_id:
            return Annotation.get_by_idiom(self.idiom_id)
        return None

    def execute(self) -> bool:
        """
        Execute annotation update.

        Update the annotation with the new data.

        If the annotation does not exist, create a new one with the given token
        or idiom ID, and update the annotation with the new data.

        Returns:
            True if the annotation was updated, False otherwise

        """
        session = self._get_session()
        annotation = self.annotation
        if annotation is None:
            annotation = Annotation(token_id=self.token_id, idiom_id=self.idiom_id)
            session.add(annotation)
            session.flush()
        annotation.from_json(annotation.token_id, self.after, annotation.idiom_id)
        return True

    def undo(self) -> bool:
        """
        Undo annotation update.
        """
        annotation = self.annotation
        if annotation is None:
            return False
        annotation.from_json(annotation.token_id, self.before, annotation.idiom_id)
        return True

    def get_description(self) -> str:
        """Get command description."""
        target = f"token {self.token_id}" if self.token_id else f"idiom {self.idiom_id}"
        return f"Annotate {target}"

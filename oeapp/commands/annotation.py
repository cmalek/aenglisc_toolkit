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

        Returns:
            True if there was an annotation to restore, False otherwise

        """
        annotation = self.annotation
        if annotation is None:
            return False
        annotation.from_json(annotation.token_id, self.before, annotation.idiom_id)
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            The computed value.

        """
        target = f"token {self.token_id}" if self.token_id else f"idiom {self.idiom_id}"
        return f"Annotate {target}"


@dataclass
class ApplyRememberedAnnotationsCommand(SessionMixin, Command):
    """Command for batch-applying remembered annotations to tokens."""

    #: Token IDs updated by this apply pass.
    token_ids: list[int] = field(default_factory=list)
    #: Per-token annotation state before apply.
    before: dict[int, dict[str, Any]] = field(default_factory=dict)
    #: Per-token annotation state after apply.
    after: dict[int, dict[str, Any]] = field(default_factory=dict)

    def execute(self) -> bool:
        """
        Apply the remembered annotation payloads to all target tokens.

        If there was an error applying the annotations, rollback the transaction
        and return False.

        Returns:
            True if the annotations were applied wihtout errors, False otherwise

        """
        session = self._get_session()
        try:
            for token_id in self.token_ids:
                Annotation.from_json(token_id, self.after[token_id], commit=False)
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
            return False
        return True

    def undo(self) -> bool:
        """
        Restore the pre-apply annotation payloads for all target tokens.

        If there was an error restoring the annotations, rollback the transaction
        and return False.

        Returns:
            True if the annotations were restored without errors, False otherwise

        """
        session = self._get_session()
        try:
            for token_id in self.token_ids:
                Annotation.from_json(token_id, self.before[token_id], commit=False)
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
            return False
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Human-readable undo-stack label.

        """
        token_count = len(self.token_ids)
        return f"Apply remembered annotations to {token_count} token(s)"


@dataclass
class ApplyAnnotationPropagationCommand(SessionMixin, Command):
    """Command for batch-propagating annotation payloads to tokens."""

    #: Token IDs updated by one propagation action.
    token_ids: list[int] = field(default_factory=list)
    #: Per-token annotation state before propagation.
    before: dict[int, dict[str, Any]] = field(default_factory=dict)
    #: Per-token annotation state after propagation.
    after: dict[int, dict[str, Any]] = field(default_factory=dict)

    def execute(self) -> bool:
        """
        Apply propagation payloads to all target tokens in one transaction.

        Returns:
            ``True`` when batch apply succeeds, else ``False``.

        """
        session = self._get_session()
        try:
            for token_id in self.token_ids:
                Annotation.from_json(token_id, self.after[token_id], commit=False)
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
            return False
        return True

    def undo(self) -> bool:
        """
        Restore pre-propagation annotation payloads in one transaction.

        Returns:
            ``True`` when batch undo succeeds, else ``False``.

        """
        session = self._get_session()
        try:
            for token_id in self.token_ids:
                Annotation.from_json(token_id, self.before[token_id], commit=False)
            session.commit()
        except Exception:  # noqa: BLE001
            session.rollback()
            return False
        return True

    def get_description(self) -> str:
        """
        Get command description.

        Returns:
            Human-readable undo-stack label.

        """
        token_count = len(self.token_ids)
        return f"Propagate annotation to {token_count} token(s)"

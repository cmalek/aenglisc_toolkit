"""Annotation related commands."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import make_transient

from oeapp.models.annotation import Annotation
from oeapp.models.idiom import Idiom
from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence

from .abstract import Command


@dataclass
class AnnotateTokenCommand(SessionMixin, Command):
    """Command for annotating a token or idiom, optionally creating the idiom first."""

    #: The token ID.
    token_id: int | None = None
    #: The before state of the annotation.
    before: dict[str, Any] = field(default_factory=dict)
    #: The after state of the annotation.
    after: dict[str, Any] = field(default_factory=dict)
    #: The idiom ID.
    idiom_id: int | None = None
    #: A not-yet-persisted Idiom to create before annotating it. When set,
    #: undo deletes this idiom (its annotation cascade-deletes with it)
    #: instead of just blanking the annotation's fields. See ADR 0002.
    new_idiom: Idiom | None = None
    #: Sentence the annotated token/idiom belongs to, used to refresh the
    #: sentence's ``tokens``/``idioms`` relationship collections after a new
    #: idiom is linked in. Required whenever ``new_idiom`` is set.
    sentence_id: int | None = None

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
        Execute annotation update, creating the idiom first if needed.

        If :attr:`new_idiom` is set, persist it first and use its id as
        :attr:`idiom_id`. The id is reset to ``None`` before every insert so
        a redo after a prior undo (which deleted the row) gets a fresh
        primary key rather than reusing the deleted one.

        If the annotation does not exist, create a new one with the given
        token or idiom ID, and update the annotation with the new data.

        Returns:
            True if the annotation was updated, False otherwise

        """
        session = self._get_session()

        if self.new_idiom is not None:
            # Redo after a prior undo() reuses this same Idiom instance,
            # which undo() already deleted (session.delete + flush). That
            # leaves it in SQLAlchemy's "deleted" identity-map state, and
            # its cascade-deleted Annotation (cascade="all, delete-orphan"
            # on Idiom.annotation) is still cached in this instance's
            # __dict__["annotation"]. Session.add() on a deleted-state
            # instance raises InvalidRequestError, so it must be reset to
            # transient first. The cached Annotation reference must be
            # popped directly from __dict__ (bypassing the ORM's
            # instrumented attribute events) rather than cleared via a
            # normal assignment (``self.new_idiom.annotation = None``):
            # a normal assignment still leaves the deleted Annotation
            # reachable through SQLAlchemy's attribute history, so the
            # "save-update" cascade below re-attaches it and raises
            # ``InvalidRequestError: Instance ... has been deleted``. A
            # brand-new Annotation is created further down in this method,
            # so the stale cached reference isn't needed. Only do any of
            # this when the state actually requires it.
            if inspect(self.new_idiom).deleted:
                self.new_idiom.__dict__.pop("annotation", None)
                make_transient(self.new_idiom)
            self.new_idiom.id = None
            session.add(self.new_idiom)
            session.flush()
            self.idiom_id = self.new_idiom.id

        annotation = self.annotation
        if annotation is None:
            annotation = Annotation(token_id=self.token_id, idiom_id=self.idiom_id)
            session.add(annotation)
            session.flush()
        annotation.from_json(annotation.token_id, self.after, annotation.idiom_id)

        if self.idiom_id is not None and self.sentence_id is not None:
            sentence = Sentence.get(self.sentence_id)
            if sentence is not None:
                session.refresh(sentence, ["tokens", "idioms"])

        return True

    def undo(self) -> bool:
        """
        Undo annotation update.

        When :attr:`new_idiom` is set, deletes the created idiom (its
        annotation cascade-deletes with it) rather than blanking fields,
        per ADR 0002.

        Returns:
            True if there was an annotation/idiom to restore, False otherwise

        """
        if self.new_idiom is not None:
            if self.idiom_id is not None:
                session = self._get_session()
                idiom = Idiom.get(self.idiom_id)
                if idiom is not None:
                    session.delete(idiom)
                    session.flush()
            return True

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

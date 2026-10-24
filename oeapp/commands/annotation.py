"""Annotation related commands."""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import inspect
from sqlalchemy.orm import make_transient

from oeapp.models.annotation import Annotation
from oeapp.models.idiom import Idiom
from oeapp.models.mixins import SessionMixin
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token

from .abstract import Command, CommandLocators, StackAdjustment


class TokenBatchLocators(Command):
    """
    Locators for a command that writes one annotation payload per token.

    The command keeps its target tokens in ``token_ids`` and, from the first
    ``execute`` on, the sentence of each in ``token_sentence``. ``before`` and
    ``after`` are keyed by token id and are undo snapshots; a dropped token's
    entries stay there untouched.
    """

    #: Token IDs this command writes to.
    token_ids: list[int]
    #: Sentence of each target token, filled on the first ``execute``.
    token_sentence: dict[int, int]

    def record_sentences(self) -> None:
        """
        Note which sentence each target token belongs to.

        Side Effects:
            Fills :attr:`token_sentence` for the tokens not yet recorded.

        """
        for token_id in self.token_ids:
            if token_id in self.token_sentence:
                continue
            token = Token.get(token_id)
            if token is not None:
                self.token_sentence[token_id] = token.sentence_id

    def locators(self) -> CommandLocators:
        """
        Get the tokens and sentences this batch acts on.

        Returns:
            Locators naming every target token and its sentence.

        """
        return CommandLocators(
            sentence_ids=set(self.token_sentence.values()),
            token_ids=set(self.token_ids),
        )

    def relocate(self, adjustment: StackAdjustment) -> None:
        """
        Drop target tokens that are gone and follow the ones that moved.

        Args:
            adjustment: What another command removed or moved.

        Side Effects:
            Removes dead ids from :attr:`token_ids` and :attr:`token_sentence`
            and updates the sentence of each moved token.

        """
        self.token_ids = [
            token_id
            for token_id in self.token_ids
            if token_id not in adjustment.obsolete_token_ids
        ]
        for token_id in adjustment.obsolete_token_ids:
            self.token_sentence.pop(token_id, None)
        for token_id, sentence_id in adjustment.token_sentence.items():
            if token_id in self.token_sentence:
                self.token_sentence[token_id] = sentence_id


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
            # which undo() already deleted (session.delete + commit). That
            # leaves it out of SQLAlchemy's identity map (deleted-and-
            # flushed instances are "deleted"; deleted-and-committed
            # instances are "detached" — inspect(...).deleted is only True
            # in the former case), and its cascade-deleted Annotation
            # (cascade="all, delete-orphan" on Idiom.annotation) is still
            # cached in this instance's __dict__["annotation"]. Session.add()
            # on a non-transient instance whose row no longer exists raises
            # InvalidRequestError, so it must be reset to transient first.
            # Checking "not transient" (rather than "deleted") catches both
            # the flushed-only and the committed-delete cases; a brand-new
            # Idiom that has never been added to a session is transient, so
            # this only fires on reuse. The cached Annotation reference must
            # be popped directly from __dict__ (bypassing the ORM's
            # instrumented attribute events) rather than cleared via a
            # normal assignment (``self.new_idiom.annotation = None``):
            # a normal assignment still leaves the deleted Annotation
            # reachable through SQLAlchemy's attribute history, so the
            # "save-update" cascade below re-attaches it and raises
            # ``InvalidRequestError: Instance ... has been deleted``. A
            # brand-new Annotation is created further down in this method,
            # so the stale cached reference isn't needed. Only do any of
            # this when the state actually requires it.
            if not inspect(self.new_idiom).transient:
                self.new_idiom.__dict__.pop("annotation", None)
                make_transient(self.new_idiom)
            # Idiom.id is Mapped[int] (non-optional), but SQLAlchemy allows
            # resetting a transient instance's PK to None before re-insert
            # so a redo gets a fresh id instead of reusing the deleted one.
            self.new_idiom.id = None  # type: ignore[assignment]
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
        if self.sentence_id is None:
            self.sentence_id = self._target_sentence_id()

        return True

    def _target_sentence_id(self) -> int | None:
        """
        Look up the sentence that holds the annotated token or idiom.

        Returns:
            The sentence id, or ``None`` when neither target exists.

        """
        if self.token_id is not None:
            token = Token.get(self.token_id)
            return token.sentence_id if token is not None else None
        if self.idiom_id is not None:
            idiom = Idiom.get(self.idiom_id)
            return idiom.sentence_id if idiom is not None else None
        return None

    def locators(self) -> CommandLocators:
        """
        Get the sentence, token, and idiom this annotation targets.

        Returns:
            Locators with whichever of :attr:`sentence_id`, :attr:`token_id`,
            and :attr:`idiom_id` are set.

        """
        return CommandLocators(
            sentence_ids=set() if self.sentence_id is None else {self.sentence_id},
            token_ids=set() if self.token_id is None else {self.token_id},
            idiom_ids=set() if self.idiom_id is None else {self.idiom_id},
        )

    def relocate(self, adjustment: StackAdjustment) -> None:
        """
        Follow the annotated token to the sentence it was moved to.

        Args:
            adjustment: What another command removed or moved.

        Side Effects:
            Updates :attr:`sentence_id` when :attr:`token_id` moved. The token
            id itself is never changed.

        """
        if self.token_id in adjustment.token_sentence:
            self.sentence_id = adjustment.token_sentence[self.token_id]

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
                    session.commit()
            return True

        annotation = self.annotation
        if annotation is None:
            return False
        annotation.from_json(annotation.token_id, self.before, annotation.idiom_id)
        return True

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Annotate"


@dataclass
class ApplyRememberedAnnotationsCommand(SessionMixin, TokenBatchLocators):
    """Command for batch-applying remembered annotations to tokens."""

    #: Token IDs updated by this apply pass.
    token_ids: list[int] = field(default_factory=list)
    #: Per-token annotation state before apply.
    before: dict[int, dict[str, Any]] = field(default_factory=dict)
    #: Per-token annotation state after apply.
    after: dict[int, dict[str, Any]] = field(default_factory=dict)
    #: Sentence of each target token, filled on the first ``execute``.
    token_sentence: dict[int, int] = field(default_factory=dict)

    def execute(self) -> bool:
        """
        Apply the remembered annotation payloads to all target tokens.

        If there was an error applying the annotations, rollback the transaction
        and return False.

        Returns:
            True if the annotations were applied wihtout errors, False otherwise

        """
        session = self._get_session()
        self.record_sentences()
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

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Apply remembered annotations"


@dataclass
class ApplyAnnotationPropagationCommand(SessionMixin, TokenBatchLocators):
    """Command for batch-propagating annotation payloads to tokens."""

    #: Token IDs updated by one propagation action.
    token_ids: list[int] = field(default_factory=list)
    #: Per-token annotation state before propagation.
    before: dict[int, dict[str, Any]] = field(default_factory=dict)
    #: Per-token annotation state after propagation.
    after: dict[int, dict[str, Any]] = field(default_factory=dict)
    #: Sentence of each target token, filled on the first ``execute``.
    token_sentence: dict[int, int] = field(default_factory=dict)

    def execute(self) -> bool:
        """
        Apply propagation payloads to all target tokens in one transaction.

        Returns:
            ``True`` when batch apply succeeds, else ``False``.

        """
        session = self._get_session()
        self.record_sentences()
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

    def menu_text(self) -> str:
        """
        Get the plain-language name shown in the Edit menu.

        Returns:
            Short action name with no database ids.

        """
        return "Propagate annotation"

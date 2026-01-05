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

    def _update_annotation(self, annotation: Annotation, state: dict[str, Any]) -> None:
        """Update an annotation with a new state."""
        annotation.pos = state.get("pos")
        annotation.gender = state.get("gender")
        annotation.number = state.get("number")
        annotation.case = state.get("case")
        annotation.declension = state.get("declension")
        annotation.article_type = state.get("article_type")
        annotation.pronoun_type = state.get("pronoun_type")
        annotation.pronoun_number = state.get("pronoun_number")
        annotation.verb_class = state.get("verb_class")
        annotation.verb_tense = state.get("verb_tense")
        annotation.verb_person = state.get("verb_person")
        annotation.verb_mood = state.get("verb_mood")
        annotation.verb_aspect = state.get("verb_aspect")
        annotation.verb_form = state.get("verb_form")
        annotation.prep_case = state.get("prep_case")
        annotation.adjective_inflection = state.get("adjective_inflection")
        annotation.adjective_degree = state.get("adjective_degree")
        annotation.conjunction_type = state.get("conjunction_type")
        annotation.adverb_degree = state.get("adverb_degree")
        annotation.confidence = state.get("confidence")
        annotation.modern_english_meaning = state.get("modern_english_meaning")
        annotation.root = state.get("root")
        annotation.save()

    def _get_annotation(self) -> Annotation | None:
        """Get the current annotation."""
        if self.token_id:
            return Annotation.get_by_token(self.token_id)
        if self.idiom_id:
            return Annotation.get_by_idiom(self.idiom_id)
        return None

    def execute(self) -> bool:
        """Execute annotation update."""
        session = self._get_session()
        annotation = self._get_annotation()
        if annotation is None:
            annotation = Annotation(token_id=self.token_id, idiom_id=self.idiom_id)
            session.add(annotation)
            session.flush()
        self._update_annotation(annotation, self.after)
        return True

    def undo(self) -> bool:
        """Undo annotation update."""
        annotation = self._get_annotation()
        if annotation is None:
            return False
        self._update_annotation(annotation, self.before)
        return True

    def get_description(self) -> str:
        """Get command description."""
        target = f"token {self.token_id}" if self.token_id else f"idiom {self.idiom_id}"
        return f"Annotate {target}"

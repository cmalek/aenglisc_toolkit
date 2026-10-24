"""Remembered annotation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from oeapp.commands import ApplyRememberedAnnotationsCommand
from oeapp.models import Annotation, RememberedAnnotation
from oeapp.utils import partially_normalize_old_english


@dataclass
class RememberedAnnotationApplyPlan:
    """Prepared remembered-annotation apply result."""

    #: Undoable command for the apply pass.
    command: ApplyRememberedAnnotationsCommand
    #: Number of tokens that will be updated.
    applied_count: int
    #: Number of matching tokens skipped because they already had annotations.
    skipped_count: int
    #: Total matching tokens found by exact surface lookup.
    matched_count: int
    #: Human-readable status message for the UI.
    message: str
    #: Token IDs that will change if the command executes.
    affected_token_ids: list[int] = field(default_factory=list)


class RememberedAnnotationService:
    """Thin UI-facing workflows for remembered annotation management."""

    def remember_token_annotation(
        self, token, project_id: int | None
    ) -> RememberedAnnotation:
        """
        Remember the selected token annotation into one scope.

        Args:
            token: Token.
            project_id: Project id.

        Returns:
            The computed value.

        """
        return RememberedAnnotation.upsert_from_token_annotation(token, project_id)

    def save_entry(
        self,
        token_text: str,
        project_id: int | None,
        field_data: dict,
    ) -> RememberedAnnotation:
        """
        Save remembered-annotation form data into one scope.

        Args:
            token_text: Token text.
            project_id: Project id.
            field_data: Field data.

        Returns:
            The computed value.

        """
        return RememberedAnnotation.upsert_fields(
            token_text=token_text,
            project_id=project_id,
            field_data=field_data,
        )

    def plan_apply(self, project_id: int) -> RememberedAnnotationApplyPlan:
        """
        Build an undoable remembered-annotation apply plan for one project.

        Args:
            project_id: Project id.

        Returns:
            The computed value.

        """
        applicable, ambiguous = RememberedAnnotation.resolve_for_project(project_id)
        tokens = RememberedAnnotation.matching_tokens(project_id, list(applicable))
        before: dict[int, dict] = {}
        after: dict[int, dict] = {}
        skipped_count = 0
        affected_token_ids: list[int] = []

        for token in tokens:
            if token.id is None:
                continue
            annotation = token.annotation or Annotation.get_by_token(token.id)
            if annotation is None:
                annotation = Annotation(token_id=token.id)
            if not annotation.is_safe_to_auto_fill():
                skipped_count += 1
                continue
            partial_key = partially_normalize_old_english(token.surface) or ""
            before[token.id] = annotation.to_json()
            after[token.id] = applicable[partial_key].annotation_payload()
            affected_token_ids.append(token.id)

        applied_count = len(affected_token_ids)
        return RememberedAnnotationApplyPlan(
            command=ApplyRememberedAnnotationsCommand(
                token_ids=affected_token_ids,
                before=before,
                after=after,
            ),
            applied_count=applied_count,
            skipped_count=skipped_count,
            matched_count=len(tokens),
            message=_apply_message(
                applied_count, skipped_count, len(tokens), ambiguous
            ),
            affected_token_ids=affected_token_ids,
        )


def _count_line(count: int, verb: str) -> str:
    """
    Format a token count sentence.

    Args:
        count: Token count.
        verb: Past-tense verb for the sentence.

    Returns:
        A one-line summary.

    """
    noun = "token" if count == 1 else "tokens"
    return f"{count} {noun} {verb}."


def _skipped_line(count: int) -> str:
    """
    Format the skipped-token sentence.

    Args:
        count: Number of tokens that already had annotations.

    Returns:
        A one-line summary.

    """
    if count == 1:
        return "1 token skipped because it already had an annotation."
    return f"{count} tokens skipped because they already had an annotation."


def _apply_message(
    applied: int,
    skipped: int,
    matched: int,
    ambiguous: list,
) -> str:
    """
    Build the apply summary dialog text.

    Args:
        applied: Tokens that will be updated.
        skipped: Tokens skipped because they already had annotations.
        matched: Tokens that matched an applicable remembered entry.
        ambiguous: Same-scope partial-spelling conflicts.

    Returns:
        Dialog text.

    """
    lines = [_count_line(applied, "updated")]
    if skipped:
        lines.append(_skipped_line(skipped))
    if ambiguous:
        lines.append("")
        lines.append("Ambiguous remembered annotations were not applied:")
        for group in ambiguous:
            scope = "global" if group[0].project_id is None else "project"
            spellings = " / ".join(entry.token_text for entry in group)
            lines.append(f"- {spellings} ({scope})")
    elif applied == 0 and matched == 0:
        lines.append("No remembered annotations matched this text.")
    return "\n".join(lines)

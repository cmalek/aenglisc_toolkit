"""Remembered annotation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field

from oeapp.commands import ApplyRememberedAnnotationsCommand
from oeapp.models import Annotation, RememberedAnnotation


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
        remembered_by_token = RememberedAnnotation.effective_for_project(project_id)
        if not remembered_by_token:
            return RememberedAnnotationApplyPlan(
                command=ApplyRememberedAnnotationsCommand(),
                applied_count=0,
                skipped_count=0,
                matched_count=0,
                message="0 applied: no remembered annotations matched this text",
            )

        tokens = RememberedAnnotation.matching_tokens(
            project_id, list(remembered_by_token.keys())
        )
        if not tokens:
            return RememberedAnnotationApplyPlan(
                command=ApplyRememberedAnnotationsCommand(),
                applied_count=0,
                skipped_count=0,
                matched_count=0,
                message="0 applied: no remembered annotations matched this text",
            )

        before: dict[int, dict] = {}
        after: dict[int, dict] = {}
        matched_count = len(tokens)
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
            before[token.id] = annotation.to_json()
            after[token.id] = remembered_by_token[token.surface].annotation_payload()
            affected_token_ids.append(token.id)

        applied_count = len(affected_token_ids)
        if applied_count == 0:
            message = "0 applied: all matched tokens already had annotations"
        elif skipped_count == 0:
            message = f"{applied_count} applied, 0 skipped"
        else:
            message = f"{applied_count} applied, {skipped_count} skipped"

        return RememberedAnnotationApplyPlan(
            command=ApplyRememberedAnnotationsCommand(
                token_ids=affected_token_ids,
                before=before,
                after=after,
            ),
            applied_count=applied_count,
            skipped_count=skipped_count,
            matched_count=matched_count,
            message=message,
            affected_token_ids=affected_token_ids,
        )

"""Project-wide token annotation propagation workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

from sqlalchemy import select

from oeapp.commands import ApplyAnnotationPropagationCommand
from oeapp.models import Annotation
from oeapp.ui.token_details_sidebar import BaseTokenDetailsSidebar


@dataclass
class AnnotationPropagationPlan:
    """Prepared propagation result for one user action."""

    #: Undoable command for propagation.
    command: ApplyAnnotationPropagationCommand
    #: Number of tokens that will be updated.
    updated_count: int
    #: Token IDs affected by propagation.
    affected_token_ids: list[int] = field(default_factory=list)
    #: User-facing rich-text dialog message.
    dialog_message: str = "No matching words found"
    #: Rich-text source token summary used in the dialog.
    rich_text_summary: str = ""


class AnnotationPropagationService:
    """Build undoable annotation propagation plans."""

    def plan_surface_propagation(
        self, project_id: int, source_token
    ) -> AnnotationPropagationPlan:
        """
        Build plan for normalized-surface propagation.

        Args:
            project_id: Project to search.
            source_token: Token whose annotation should be propagated.

        Returns:
            Prepared propagation plan.

        """
        source_annotation = source_token.annotation or Annotation.get_by_token(
            source_token.id
        )
        summary = self._build_summary_html(source_token)
        if (
            source_token.id is None
            or not source_token.surface_normalized
            or source_annotation is None
        ):
            return self._empty_plan(summary)

        source_payload = {
            key: value
            for key, value in source_annotation.to_json().items()
            if key != "sense"
        }
        targets = self._surface_targets(project_id, source_token.surface_normalized)
        return self._build_plan(
            source_token=source_token,
            targets=targets,
            summary=summary,
            build_after=lambda target_annotation: (
                source_payload
                if target_annotation.is_safe_to_auto_fill()
                else None
            ),
        )

    def plan_meaning_propagation(
        self, project_id: int, source_token
    ) -> AnnotationPropagationPlan:
        """
        Build plan for root-normalized meaning propagation.

        Args:
            project_id: Project to search.
            source_token: Token whose meaning should be propagated.

        Returns:
            Prepared propagation plan.

        """
        source_annotation = source_token.annotation or Annotation.get_by_token(
            source_token.id
        )
        summary = self._build_summary_html(source_token)
        if (
            source_token.id is None
            or source_annotation is None
            or not source_annotation.root_normalized
            or not source_annotation.modern_english_meaning
        ):
            return self._empty_plan(summary)

        targets = self._meaning_targets(project_id, source_annotation.root_normalized)
        return self._build_plan(
            source_token=source_token,
            targets=targets,
            summary=summary,
            build_after=lambda target_annotation: (
                {
                    **target_annotation.to_json(),
                    "modern_english_meaning": source_annotation.modern_english_meaning,
                }
            ),
        )

    def _build_plan(
        self,
        source_token,
        targets: list,
        summary: str,
        build_after,
    ) -> AnnotationPropagationPlan:
        """
        Build one propagation plan from resolved targets and payload mapper.

        Args:
            source_token: Token that initiated propagation.
            targets: Candidate target tokens.
            summary: Rich-text source summary for dialogs.
            build_after: Callable returning post-update payload or ``None``.

        Returns:
            Prepared propagation plan.

        """
        before: dict[int, dict] = {}
        after: dict[int, dict] = {}
        affected_token_ids: list[int] = []

        for target in targets:
            if target.id is None or target.id == source_token.id:
                continue
            target_annotation = target.annotation or Annotation.get_by_token(target.id)
            if target_annotation is None:
                target_annotation = Annotation(token_id=target.id)
            payload = build_after(target_annotation)
            if payload is None:
                continue
            before[target.id] = target_annotation.to_json()
            after[target.id] = payload
            affected_token_ids.append(target.id)

        if not affected_token_ids:
            return self._empty_plan(summary)

        updated_count = len(affected_token_ids)
        return AnnotationPropagationPlan(
            command=ApplyAnnotationPropagationCommand(
                token_ids=affected_token_ids,
                before=before,
                after=after,
            ),
            updated_count=updated_count,
            affected_token_ids=affected_token_ids,
            dialog_message=f"{updated_count} words updated to match {summary}",
            rich_text_summary=summary,
        )

    def _surface_targets(self, project_id: int, normalized_surface: str) -> list:
        """
        Return project tokens matching one normalized surface.

        Args:
            project_id: Project to search.
            normalized_surface: Normalized surface to match.

        Returns:
            Matching tokens in display order.

        """
        from oeapp.models.sentence import Sentence  # noqa: PLC0415
        from oeapp.models.token import Token  # noqa: PLC0415

        session = Annotation._get_session()
        stmt = (
            select(Token)
            .join(Sentence)
            .where(
                Sentence.project_id == project_id,
                Token.surface_normalized == normalized_surface,
            )
            .order_by(Sentence.display_order, Token.order_index)
        )
        return list(session.scalars(stmt).all())

    def _meaning_targets(self, project_id: int, root_normalized: str) -> list:
        """
        Return project tokens matching one normalized root.

        Args:
            project_id: Project to search.
            root_normalized: Normalized root to match.

        Returns:
            Matching tokens in display order.

        """
        from oeapp.models.sentence import Sentence  # noqa: PLC0415
        from oeapp.models.token import Token  # noqa: PLC0415

        session = Annotation._get_session()
        stmt = (
            select(Token)
            .join(Sentence)
            .join(Annotation, Annotation.token_id == Token.id)
            .where(
                Sentence.project_id == project_id,
                Annotation.root_normalized == root_normalized,
            )
            .order_by(Sentence.display_order, Token.order_index)
        )
        return list(session.scalars(stmt).all())

    def _empty_plan(self, summary: str) -> AnnotationPropagationPlan:
        """
        Return zero-update plan with standard dialog text.

        Args:
            summary: Rich-text source summary for dialogs.

        Returns:
            Empty propagation plan.

        """
        return AnnotationPropagationPlan(
            command=ApplyAnnotationPropagationCommand(),
            updated_count=0,
            affected_token_ids=[],
            dialog_message="No matching words found",
            rich_text_summary=summary,
        )

    def _build_summary_html(self, source_token) -> str:
        """
        Build rich-text token summary matching sidebar title formatting.

        Args:
            source_token: Token to summarize.

        Returns:
            HTML summary string for dialogs.

        """
        annotation = source_token.annotation or (
            Annotation.get_by_token(source_token.id) if source_token.id else None
        )
        pos_str = ""
        gender_str = ""
        context_str = ""
        if annotation is not None:
            pos_str = annotation.format_pos(annotation)
            gender_str = annotation.format_gender(annotation)
            context_str = annotation.format_context(annotation)

        summary = ""
        if pos_str:
            summary += (
                f"<sup style='{BaseTokenDetailsSidebar.SUP_STYLE}'>"
                f"{escape(pos_str)}</sup>"
            )
        if gender_str:
            summary += (
                f"<sub style='{BaseTokenDetailsSidebar.SUB_STYLE}'>"
                f"{escape(gender_str)}</sub>"
            )
        summary += escape(source_token.surface_normalized or source_token.surface)
        if context_str:
            summary += (
                f"<sub style='{BaseTokenDetailsSidebar.SUB_STYLE}'>"
                f"{escape(context_str)}</sub>"
            )
        return summary

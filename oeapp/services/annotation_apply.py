"""Turn one annotation modal result into an undoable command."""

from oeapp.commands import AnnotateTokenCommand
from oeapp.models import Annotation, AnnotationEdit


class AnnotationApplyService:
    """
    Build the undoable command that saves one annotation modal result.

    The caller starts an edit before the modal opens, pushes the command
    this service builds, and calls :meth:`finish` once the push succeeds.
    """

    def begin(self, existing: Annotation | None) -> AnnotationEdit:
        """
        Snapshot an annotation before the modal edits it.

        Args:
            existing: Annotation the modal will edit, or ``None`` when the
                token or idiom has none yet.

        Returns:
            The edit, holding the before-snapshot.

        """
        if existing is None:
            return AnnotationEdit(before={})
        return AnnotationEdit(before=existing.undo_snapshot())

    def command_for(
        self, edit: AnnotationEdit, applied: Annotation, sentence_id: int | None
    ) -> AnnotateTokenCommand:
        """
        Build the command that saves the modal's result.

        Args:
            edit: Edit started when the modal opened.
            applied: Annotation the modal emitted.
            sentence_id: Sentence that holds the token or idiom.

        Returns:
            Command that writes ``applied`` and restores ``edit.before`` on
            Undo. It creates the idiom first when ``applied`` is for a new
            idiom (ADR 0002).

        """
        new_idiom = None
        if applied.idiom_id is None and applied.idiom is not None:
            new_idiom = applied.idiom
        return AnnotateTokenCommand(
            token_id=applied.token_id,
            idiom_id=applied.idiom_id,
            before=dict(edit.before),
            after=applied.undo_snapshot(),
            new_idiom=new_idiom,
            sentence_id=sentence_id,
        )

    def finish(self, applied: Annotation, command: AnnotateTokenCommand) -> None:
        """
        Record what a successful push created.

        Args:
            applied: Annotation the modal emitted.
            command: Command that was pushed successfully.

        Side Effects:
            Sets ``applied.idiom_id`` to the created idiom's id when the
            command created an idiom.

        """
        if command.new_idiom is not None:
            applied.idiom_id = command.idiom_id

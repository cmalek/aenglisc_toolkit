"""Explicit read/write state for the annotation modal form."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from oeapp.models import Annotation
    from oeapp.models.remembered_annotation import RememberedAnnotation
    from oeapp.ui.dialogs.annotation_modal import AnnotationModal


@dataclass
class AnnotationFormState:
    """
    Snapshot of annotation modal field values.

    POS-specific morphological values are still applied through
    :class:`~oeapp.ui.dialogs.pos_form_system.AnnotationPosFormManager`; this
    object owns POS selection and shared metadata fields.
    """

    #: Part-of-speech code, or ``None`` when the combo is empty.
    pos: str | None = None
    #: Confidence percentage for token/idiom annotations.
    confidence: int = 100
    #: Whether the TODO checkbox is checked.
    todo: bool = False
    #: Definition of the root word (modern English gloss).
    modern_english_meaning: str | None = None
    #: Contextual sense for this token instance.
    sense: str | None = None
    #: Old English root form.
    root: str | None = None
    #: Whether confidence should be read from or written to the target.
    include_confidence: bool = True
    #: Whether sense should be read from or written to the target.
    include_sense: bool = True

    @classmethod
    def from_annotation(
        cls,
        annotation: Annotation | RememberedAnnotation,
        *,
        remembered: bool = False,
    ) -> AnnotationFormState:
        """
        Build form state from an annotation or remembered annotation.

        Args:
            annotation: Existing annotation values to load into the form.

        Keyword Args:
            remembered: When ``True``, omit confidence and sense fields.

        Returns:
            Form state representing the annotation metadata.

        """
        confidence = 100
        sense: str | None = None
        if not remembered:
            token_annotation = cast("Annotation", annotation)
            if token_annotation.confidence is not None:
                confidence = token_annotation.confidence
            sense = token_annotation.sense

        return cls(
            pos=annotation.pos,
            confidence=confidence,
            modern_english_meaning=annotation.modern_english_meaning,
            sense=sense,
            root=annotation.root,
            include_confidence=not remembered,
            include_sense=not remembered,
        )

    @classmethod
    def from_modal(cls, modal: AnnotationModal) -> AnnotationFormState:
        """
        Read the current modal widget values into form state.

        Args:
            modal: Annotation modal whose widgets should be read.

        Returns:
            Form state representing the current widget values.

        """
        remembered = modal.remembered_annotation is not None
        combo_index = modal.pos_combo.currentIndex()
        if combo_index == 0:
            pos: str | None = None
        else:
            pos = modal.PART_OF_SPEECH_REVERSE_MAP.get(modal.pos_combo.currentText())

        modern_english_text = modal.modern_english_edit.text().strip()
        sense_text = modal.sense_edit.text().strip()
        root_text = modal.root_edit.text().strip()

        return cls(
            pos=pos,
            confidence=modal.confidence_slider.value(),
            todo=modal.todo_check.isChecked(),
            modern_english_meaning=modern_english_text or None,
            sense=None if remembered else (sense_text or None),
            root=root_text or None,
            include_confidence=not remembered,
            include_sense=not remembered,
        )

    @classmethod
    def cleared(cls, *, remembered: bool = False) -> AnnotationFormState:
        """
        Build the default cleared form state.

        Keyword Args:
            remembered: When ``True``, omit confidence and sense fields.

        Returns:
            Empty form state used by Clear All.

        """
        return cls(
            include_confidence=not remembered,
            include_sense=not remembered,
        )

    def apply_metadata_to_modal(self, modal: AnnotationModal) -> None:
        """
        Write metadata fields from this state into modal widgets.

        Side Effects:
            Updates confidence, TODO, meaning, sense, and root widgets on ``modal``.

        Args:
            modal: Annotation modal whose widgets should be updated.

        """
        if self.include_confidence:
            modal.confidence_slider.setValue(self.confidence)
        modal.todo_check.setChecked(self.todo)
        modal.modern_english_edit.setText(self.modern_english_meaning or "")
        if self.include_sense:
            modal.sense_edit.setText(self.sense or "")
        modal.root_edit.setText(self.root or "")

    def apply_to(self, target: Annotation | RememberedAnnotation) -> None:
        """
        Write POS and metadata from this state onto an annotation target.

        Side Effects:
            Mutates ``target`` POS and metadata attributes.

        Args:
            target: Annotation or remembered annotation to update.

        """
        target.pos = self.pos
        target.modern_english_meaning = self.modern_english_meaning
        target.root = self.root
        if self.include_confidence:
            cast("Annotation", target).confidence = self.confidence
        if self.include_sense:
            cast("Annotation", target).sense = self.sense

"""Service for handling annotation presets."""

from typing import TYPE_CHECKING

from oeapp.models.annotation_preset import AnnotationPreset

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from oeapp.models.annotation import Annotation


class AnnotationPresetService:
    """Service for managing annotation presets."""

    @staticmethod
    def get_presets_for_pos(session: Session, pos: str) -> list[AnnotationPreset]:
        """
        Get presets filtered by POS.

        Args:
            session: SQLAlchemy session
            pos: Part of speech (N, V, A, R, D)

        Returns:
            List of AnnotationPreset entities ordered by name

        """
        return AnnotationPreset.get_all_by_pos(session, pos)

    @staticmethod
    def create_preset(
        session: Session, name: str, pos: str, field_values: dict
    ) -> AnnotationPreset:
        """
        Create preset with field values dict.

        Args:
            session: SQLAlchemy session
            name: Preset name
            pos: Part of speech (N, V, A, R, D)
            field_values: Dictionary of field values

        Returns:
            Created AnnotationPreset entity

        Raises:
            ValueError: If name is empty or pos is invalid
            IntegrityError: If preset with same name and pos already exists

        """
        return AnnotationPreset.create(session, name, pos, **field_values)

    @staticmethod
    def update_preset(
        session: Session, preset_id: int, name: str, field_values: dict
    ) -> AnnotationPreset | None:
        """
        Update preset.

        Args:
            session: SQLAlchemy session
            preset_id: Preset ID
            name: New preset name
            field_values: Dictionary of field values to update

        Returns:
            Updated AnnotationPreset entity or None if not found

        Raises:
            IntegrityError: If name change would create duplicate

        """
        update_data = {"name": name.strip() if name else None, **field_values}
        return AnnotationPreset.update(session, preset_id, **update_data)

    @staticmethod
    def delete_preset(session: Session, preset_id: int) -> bool:
        """
        Delete preset.

        Args:
            session: SQLAlchemy session
            preset_id: Preset ID

        Returns:
            True if preset was deleted, False if not found

        """
        return AnnotationPreset.delete(session, preset_id)

    @staticmethod
    def apply_preset_to_annotation(  # noqa: PLR0912
        preset: AnnotationPreset, annotation: Annotation
    ) -> None:
        """
        Apply preset values to annotation object (only sets non-None values).

        Args:
            preset: AnnotationPreset to apply
            annotation: Annotation object to update

        """
        # Only set fields that have values in the preset
        if preset.gender is not None:
            annotation.gender = preset.gender
        if preset.number is not None:
            annotation.number = preset.number
        if preset.case is not None:
            annotation.case = preset.case
        if preset.declension is not None:
            annotation.declension = preset.declension
        if preset.article_type is not None:
            annotation.article_type = preset.article_type
        if preset.pronoun_type is not None:
            annotation.pronoun_type = preset.pronoun_type
        if preset.pronoun_number is not None:
            annotation.pronoun_number = preset.pronoun_number
        if preset.verb_class is not None:
            annotation.verb_class = preset.verb_class
        if preset.verb_tense is not None:
            annotation.verb_tense = preset.verb_tense
        if preset.verb_person is not None:
            annotation.verb_person = preset.verb_person
        if preset.verb_mood is not None:
            annotation.verb_mood = preset.verb_mood
        if preset.verb_aspect is not None:
            annotation.verb_aspect = preset.verb_aspect
        if preset.verb_form is not None:
            annotation.verb_form = preset.verb_form
        if preset.adjective_inflection is not None:
            annotation.adjective_inflection = preset.adjective_inflection
        if preset.adjective_degree is not None:
            annotation.adjective_degree = preset.adjective_degree

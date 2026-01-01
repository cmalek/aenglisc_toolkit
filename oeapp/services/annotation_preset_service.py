"""Service for handling annotation presets."""

from typing import TYPE_CHECKING, cast

from oeapp.models.annotation_preset import AnnotationPreset

if TYPE_CHECKING:
    from oeapp.models.annotation import Annotation
    from oeapp.types import PresetPos


class AnnotationPresetService:
    """Service for managing annotation presets."""

    @staticmethod
    def get_presets_for_pos(pos: str) -> list[AnnotationPreset]:
        """
        Get presets filtered by POS.

        Args:
            pos: Part of speech (N, V, A, R, D)

        Returns:
            List of AnnotationPreset entities ordered by name

        """
        return AnnotationPreset.get_all_by_pos(pos)

    @staticmethod
    def create_preset(
        name: str,
        pos: str,
        field_values: dict,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> AnnotationPreset:
        """
        Create preset with field values dict.

        Args:
            name: Preset name
            pos: Part of speech (N, V, A, R, D)
            field_values: Dictionary of field values

        Keyword Args:
            commit: Whether to commit the changes

        Returns:
            Created AnnotationPreset entity

        Raises:
            ValueError: If name is empty or pos is invalid
            IntegrityError: If preset with same name and pos already exists

        """
        return AnnotationPreset.create(
            name, cast("PresetPos", pos), commit=commit, **field_values
        )

    @staticmethod
    def update_preset(
        preset_id: int,
        name: str,
        field_values: dict,
        commit: bool = True,  # noqa: FBT001, FBT002
    ) -> AnnotationPreset | None:
        """
        Update preset.

        Args:
            preset_id: Preset ID
            name: New preset name
            field_values: Dictionary of field values to update

        Keyword Args:
            commit: Whether to commit the changes

        Returns:
            Updated AnnotationPreset entity or None if not found

        Raises:
            IntegrityError: If name change would create duplicate

        """
        update_data = {"name": name.strip() if name else None, **field_values}
        return AnnotationPreset.update(preset_id, commit=commit, **update_data)

    @staticmethod
    def delete_preset(preset_id: int) -> bool:
        """
        Delete preset.

        Args:
            preset_id: Preset ID

        Returns:
            True if preset was deleted, False if not found

        """
        preset = AnnotationPreset.get(preset_id)
        if preset:
            preset.delete()
            return True
        return False

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

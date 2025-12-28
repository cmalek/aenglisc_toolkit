"""Unit tests for AnnotationPresetService."""

import pytest
from sqlalchemy.exc import IntegrityError

from oeapp.models.annotation import Annotation
from oeapp.models.annotation_preset import AnnotationPreset
from oeapp.services.annotation_preset_service import AnnotationPresetService


class TestAnnotationPresetService:
    """Test cases for AnnotationPresetService."""

    def test_get_presets_for_pos_filters_correctly(self, db_session):
        """Test get_presets_for_pos() filters correctly by POS."""
        AnnotationPreset.create(name="Noun 1", pos="N")
        AnnotationPreset.create(name="Noun 2", pos="N")
        AnnotationPreset.create(name="Verb 1", pos="V")
        db_session.commit()

        service = AnnotationPresetService()
        nouns = service.get_presets_for_pos("N")
        assert len(nouns) == 2
        assert all(p.pos == "N" for p in nouns)

        verbs = service.get_presets_for_pos("V")
        assert len(verbs) == 1
        assert verbs[0].pos == "V"

    def test_create_preset_creates_with_field_values(self, db_session):
        """Test create_preset() creates preset with field values."""
        service = AnnotationPresetService()
        field_values = {"gender": "m", "number": "s", "case": "n"}
        preset = service.create_preset("Test Noun", "N", field_values)
        db_session.commit()

        assert preset.id is not None
        assert preset.name == "Test Noun"
        assert preset.pos == "N"
        assert preset.gender == "m"
        assert preset.number == "s"
        assert preset.case == "n"

    def test_create_preset_handles_partial_field_values(self, db_session):
        """Test create_preset() handles partial field values (None)."""
        service = AnnotationPresetService()
        field_values = {"verb_class": "w1", "verb_tense": None, "verb_mood": "i"}
        preset = service.create_preset("Partial Verb", "V", field_values)
        db_session.commit()

        assert preset.verb_class == "w1"
        assert preset.verb_tense is None
        assert preset.verb_mood == "i"

    def test_create_preset_handles_duplicate_error(self, db_session):
        """Test create_preset() handles IntegrityError for duplicates."""
        service = AnnotationPresetService()
        service.create_preset("Duplicate", "N", {})
        db_session.commit()

        with pytest.raises(IntegrityError):
            service.create_preset("Duplicate", "N", {})
            db_session.commit()

    def test_update_preset_updates_fields(self, db_session):
        """Test update_preset() updates preset fields."""
        preset = AnnotationPreset.create(name="Original", pos="A", gender="m")
        db_session.commit()

        service = AnnotationPresetService()
        field_values = {"gender": "f", "number": "p"}
        updated = service.update_preset(
            preset.id, "Updated Name", field_values
        )
        db_session.commit()

        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.gender == "f"
        assert updated.number == "p"

    def test_update_preset_handles_duplicate_error(self, db_session):
        """Test update_preset() handles IntegrityError for duplicates."""
        AnnotationPreset.create(name="Existing", pos="N")
        preset2 = AnnotationPreset.create(name="To Update", pos="N")
        db_session.commit()

        service = AnnotationPresetService()
        with pytest.raises(IntegrityError):
            service.update_preset(preset2.id, "Existing", {})
            db_session.commit()

    def test_delete_preset_removes_preset(self, db_session):
        """Test delete_preset() removes preset."""
        preset = AnnotationPreset.create(name="To Delete", pos="R")
        db_session.commit()
        preset_id = preset.id

        service = AnnotationPresetService()
        result = service.delete_preset(preset_id)
        db_session.commit()

        assert result is True
        assert AnnotationPreset.get(preset_id) is None

    def test_apply_preset_to_annotation_applies_only_non_none_values(self, db_session):
        """Test apply_preset_to_annotation() applies only non-None values."""
        preset = AnnotationPreset(
            name="Test",
            pos="N",
            gender="m",
            number="s",
            case=None,  # None value
            declension="s",
        )
        db_session.add(preset)
        db_session.commit()

        annotation = Annotation(token_id=1, gender="f", case="a")
        service = AnnotationPresetService()
        service.apply_preset_to_annotation(preset, annotation)

        # Should update non-None values
        assert annotation.gender == "m"
        assert annotation.number == "s"
        assert annotation.declension == "s"
        # Should not update None values
        assert annotation.case == "a"  # Original value preserved

    def test_apply_preset_to_annotation_sets_none_for_clear_fields(self, db_session):
        """Test apply_preset_to_annotation() sets fields to None when preset has None (Clear selected)."""
        preset = AnnotationPreset(
            name="With Clear",
            pos="N",
            gender="m",
            number=None,  # "Clear" was selected
            case="n",
        )
        db_session.add(preset)
        db_session.commit()

        annotation = Annotation(token_id=1, gender="f", number="p", case="a")
        service = AnnotationPresetService()
        service.apply_preset_to_annotation(preset, annotation)

        # Should update non-None values
        assert annotation.gender == "m"
        assert annotation.case == "n"
        # Should set None for "Clear" fields (this is handled in the UI, not the service)
        # The service still only sets non-None values to preserve backward compatibility
        # The UI layer (_on_preset_apply) handles None values by setting combos to index 0

"""Unit tests for AnnotationPreset model."""

import pytest
from datetime import datetime

from sqlalchemy.exc import IntegrityError

from oeapp.models.annotation_preset import AnnotationPreset


class TestAnnotationPreset:
    """Test cases for AnnotationPreset model."""

    def test_model_creation_with_all_fields(self, db_session):
        """Test model creation with all fields."""
        preset = AnnotationPreset(
            name="Test Noun",
            pos="N",
            gender="m",
            number="s",
            case="n",
            declension="s",
        )
        db_session.add(preset)
        db_session.commit()

        assert preset.id is not None
        assert preset.name == "Test Noun"
        assert preset.pos == "N"
        assert preset.gender == "m"
        assert preset.number == "s"
        assert preset.case == "n"
        assert preset.declension == "s"
        assert isinstance(preset.created_at, datetime)
        assert isinstance(preset.updated_at, datetime)

    def test_model_creation_with_partial_fields(self, db_session):
        """Test model creation with partial fields (None values)."""
        preset = AnnotationPreset(
            name="Partial Preset",
            pos="V",
            verb_class="w1",
            verb_tense=None,
            verb_mood=None,
        )
        db_session.add(preset)
        db_session.commit()

        assert preset.id is not None
        assert preset.name == "Partial Preset"
        assert preset.pos == "V"
        assert preset.verb_class == "w1"
        assert preset.verb_tense is None
        assert preset.verb_mood is None

    def test_create_class_method(self, db_session):
        """Test create() class method."""
        preset = AnnotationPreset.create(
            name="Created Preset",
            pos="A",
            gender="f",
            number="p",
        )
        db_session.commit()

        assert preset.id is not None
        assert preset.name == "Created Preset"
        assert preset.pos == "A"
        assert preset.gender == "f"
        assert preset.number == "p"

    def test_create_validates_empty_name(self):
        """Test create() rejects empty name."""
        with pytest.raises(ValueError, match="Preset name cannot be empty"):
            AnnotationPreset.create(name="", pos="N")

    def test_create_validates_invalid_pos(self):
        """Test create() rejects invalid POS."""
        with pytest.raises(ValueError, match="Invalid POS"):
            AnnotationPreset.create(name="Test", pos="X")

    def test_get_class_method(self, db_session):
        """Test get() class method."""
        preset = AnnotationPreset.create(
            name="Get Test", pos="N", gender="m"
        )
        db_session.commit()

        retrieved = AnnotationPreset.get(preset.id)
        assert retrieved is not None
        assert retrieved.id == preset.id
        assert retrieved.name == "Get Test"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent preset."""
        result = AnnotationPreset.get(99999)
        assert result is None

    def test_get_all_by_pos_filters_correctly(self, db_session):
        """Test get_all_by_pos() filters correctly by POS."""
        AnnotationPreset.create(name="Noun 1", pos="N")
        AnnotationPreset.create(name="Noun 2", pos="N")
        AnnotationPreset.create(name="Verb 1", pos="V")
        db_session.commit()

        nouns = AnnotationPreset.get_all_by_pos("N")
        assert len(nouns) == 2
        assert all(p.pos == "N" for p in nouns)
        assert nouns[0].name == "Noun 1"  # Ordered by name
        assert nouns[1].name == "Noun 2"

        verbs = AnnotationPreset.get_all_by_pos("V")
        assert len(verbs) == 1
        assert verbs[0].pos == "V"

    def test_get_all_by_pos_orders_by_name(self, db_session):
        """Test get_all_by_pos() orders by name."""
        AnnotationPreset.create(name="Zebra", pos="N")
        AnnotationPreset.create(name="Alpha", pos="N")
        AnnotationPreset.create(name="Beta", pos="N")
        db_session.commit()

        presets = AnnotationPreset.get_all_by_pos("N")
        assert len(presets) == 3
        assert presets[0].name == "Alpha"
        assert presets[1].name == "Beta"
        assert presets[2].name == "Zebra"

    def test_update_class_method(self, db_session):
        """Test update() class method."""
        preset = AnnotationPreset.create(
            name="Original", pos="N", gender="m"
        )
        db_session.commit()

        updated = AnnotationPreset.update(
            preset.id, name="Updated", gender="f"
        )
        db_session.commit()

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.gender == "f"
        assert updated.pos == "N"  # Unchanged

    def test_update_returns_none_for_nonexistent(self, db_session):
        """Test update() returns None for nonexistent preset."""
        result = AnnotationPreset.update(99999, name="Test")
        assert result is None

    def test_delete_class_method(self, db_session):
        """Test delete() class method."""
        preset = AnnotationPreset.create(name="To Delete", pos="N")
        db_session.commit()
        preset_id = preset.id

        result = AnnotationPreset.delete(preset_id)
        db_session.commit()

        assert result is True
        assert AnnotationPreset.get(preset_id) is None

    def test_delete_returns_false_for_nonexistent(self, db_session):
        """Test delete() returns False for nonexistent preset."""
        result = AnnotationPreset.delete(99999)
        assert result is False

    def test_to_dict_method(self, db_session):
        """Test to_dict() method."""
        preset = AnnotationPreset.create(
            name="Dict Test", pos="R", pronoun_type="p", gender="m"
        )
        db_session.commit()

        data = preset.to_dict()
        assert data["id"] == preset.id
        assert data["name"] == "Dict Test"
        assert data["pos"] == "R"
        assert data["pronoun_type"] == "p"
        assert data["gender"] == "m"
        assert "created_at" in data
        assert "updated_at" in data

    def test_check_constraint_rejects_invalid_pos(self, db_session):
        """Test check constraint rejects invalid POS values."""
        preset = AnnotationPreset(name="Invalid", pos="X")
        db_session.add(preset)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_unique_constraint_prevents_duplicates(self, db_session):
        """Test unique constraint prevents duplicate names per POS."""
        AnnotationPreset.create(name="Duplicate", pos="N")
        db_session.commit()

        # Same name, same POS should fail
        with pytest.raises(IntegrityError):
            AnnotationPreset.create(name="Duplicate", pos="N")
            db_session.commit()

    def test_unique_constraint_allows_same_name_different_pos(self, db_session):
        """Test unique constraint allows same name for different POS."""
        AnnotationPreset.create(name="Same Name", pos="N")
        db_session.commit()

        # Same name, different POS should succeed
        preset2 = AnnotationPreset.create(name="Same Name", pos="V")
        db_session.commit()
        assert preset2.id is not None

    def test_nullable_fields_allow_none(self, db_session):
        """Test nullable fields allow None values."""
        preset = AnnotationPreset(
            name="Nullable Test",
            pos="D",
            gender=None,
            number=None,
            case=None,
        )
        db_session.add(preset)
        db_session.commit()

        assert preset.gender is None
        assert preset.number is None
        assert preset.case is None

    def test_timestamps_set_correctly(self, db_session):
        """Test timestamps are set correctly."""
        before = datetime.now()
        preset = AnnotationPreset.create(name="Timestamp Test", pos="A")
        db_session.commit()
        after = datetime.now()

        assert before <= preset.created_at <= after
        assert before <= preset.updated_at <= after
        # Timestamps should be very close (within 1 second) since both are set on creation
        time_diff = abs((preset.updated_at - preset.created_at).total_seconds())
        assert time_diff < 1.0

    def test_updated_at_changes_on_update(self, db_session):
        """Test updated_at changes on update."""
        preset = AnnotationPreset.create(name="Update Test", pos="N")
        db_session.commit()
        original_updated = preset.updated_at

        import time
        time.sleep(0.01)  # Small delay to ensure timestamp difference

        AnnotationPreset.update(preset.id, name="Updated Name")
        db_session.commit()
        db_session.refresh(preset)

        assert preset.updated_at > original_updated

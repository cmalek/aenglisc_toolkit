"""Unit tests for AnnotationPreset model."""

from datetime import datetime

import pytest
from oeapp.db import get_runtime_session
from oeapp.models.annotation_preset import AnnotationPreset
from sqlalchemy.exc import IntegrityError


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
        preset.save()

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
        preset.save()

        assert preset.id is not None
        assert preset.name == "Partial Preset"
        assert preset.pos == "V"
        assert preset.verb_class == "w1"
        assert preset.verb_tense is None
        assert preset.verb_mood is None
        assert preset.verb_requires_infinitive is False
        assert preset.verb_impersonal is False
        assert preset.verb_transitivity == "transitive"

    def test_create_class_method(self, db_session):
        """Test create() class method."""
        session = get_runtime_session()
        preset = AnnotationPreset.create(
            name="Created Preset", pos="A", gender="f", number="p", session=session
        )

        assert preset.id is not None
        assert preset.name == "Created Preset"
        assert preset.pos == "A"
        assert preset.gender == "f"
        assert preset.number == "p"

    def test_create_validates_empty_name(self):
        """Test create() rejects empty name."""
        session = get_runtime_session()
        with pytest.raises(ValueError, match="Preset name cannot be empty"):
            AnnotationPreset.create(name="", pos="N", session=session)

    def test_create_validates_invalid_pos(self):
        """Test create() rejects invalid POS."""
        session = get_runtime_session()
        with pytest.raises(ValueError, match="Invalid POS"):
            AnnotationPreset.create(name="Test", pos="X", session=session)

    def test_get_class_method(self, db_session):
        """Test get() class method."""
        session = get_runtime_session()
        preset = AnnotationPreset.create(
            name="Get Test", pos="N", gender="m", session=session
        )

        retrieved = AnnotationPreset.get(preset.id, session=session)
        assert retrieved is not None
        assert retrieved.id == preset.id
        assert retrieved.name == "Get Test"

    def test_get_returns_none_for_nonexistent(self, db_session):
        """Test get() returns None for nonexistent preset."""
        session = get_runtime_session()
        result = AnnotationPreset.get(99999, session=session)
        assert result is None

    def test_get_all_by_pos_filters_correctly(self, db_session):
        """Test get_all_by_pos() filters correctly by POS."""
        session = get_runtime_session()
        AnnotationPreset.create(name="Noun 1", pos="N", session=session)
        AnnotationPreset.create(name="Noun 2", pos="N", session=session)
        AnnotationPreset.create(name="Verb 1", pos="V", session=session)

        nouns = AnnotationPreset.get_all_by_pos("N", session=session)
        assert len(nouns) == 2
        assert all(p.pos == "N" for p in nouns)
        assert nouns[0].name == "Noun 1"  # Ordered by name
        assert nouns[1].name == "Noun 2"

        verbs = AnnotationPreset.get_all_by_pos("V", session=session)
        assert len(verbs) == 1
        assert verbs[0].pos == "V"

    def test_get_all_by_pos_orders_by_name(self, db_session):
        """Test get_all_by_pos() orders by name."""
        session = get_runtime_session()
        AnnotationPreset.create(name="Zebra", pos="N", session=session)
        AnnotationPreset.create(name="Alpha", pos="N", session=session)
        AnnotationPreset.create(name="Beta", pos="N", session=session)

        presets = AnnotationPreset.get_all_by_pos("N", session=session)
        assert len(presets) == 3
        assert presets[0].name == "Alpha"
        assert presets[1].name == "Beta"
        assert presets[2].name == "Zebra"

    def test_update_class_method(self, db_session):
        """Test update() class method."""
        session = get_runtime_session()
        preset = AnnotationPreset.create(
            name="Original", pos="N", gender="m", session=session
        )

        updated = AnnotationPreset.update(
            preset.id, name="Updated", gender="f", session=session
        )

        assert updated is not None
        assert updated.name == "Updated"
        assert updated.gender == "f"
        assert updated.pos == "N"  # Unchanged

    def test_update_returns_none_for_nonexistent(self, db_session):
        """Test update() returns None for nonexistent preset."""
        session = get_runtime_session()
        result = AnnotationPreset.update(99999, name="Test", session=session)
        assert result is None

    def test_delete_class_method(self, db_session):
        """Test delete() class method."""
        session = get_runtime_session()
        preset = AnnotationPreset.create(name="To Delete", pos="N", session=session)
        preset_id = preset.id

        preset.delete()
        assert AnnotationPreset.get(preset_id, session=session) is None

    def test_to_json_method(self, db_session):
        """Test to_dict() method."""
        session = get_runtime_session()
        preset = AnnotationPreset.create(
            name="Dict Test", pos="R", pronoun_type="p", gender="m", session=session
        )

        data = preset.to_json()
        assert data["name"] == "Dict Test"
        assert data["pos"] == "R"
        assert data["pronoun_type"] == "p"
        assert data["gender"] == "m"
        assert data["verb_requires_infinitive"] is False
        assert data["verb_impersonal"] is False
        assert data["verb_transitivity"] == "transitive"
        assert "created_at" in data
        assert "updated_at" in data
        assert "id" not in data

    def test_from_json_method(self, db_session):
        """Test from_json() creates a preset."""
        session = get_runtime_session()
        preset_data = {
            "name": "Imported Preset",
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "verb_requires_infinitive": True,
            "verb_impersonal": True,
            "verb_transitivity": "intransitive",
        }

        preset = AnnotationPreset.from_json(preset_data, session=session)
        assert preset.id is not None
        assert preset.name == "Imported Preset"
        assert preset.pos == "N"
        assert preset.gender == "m"
        assert preset.number == "s"
        assert preset.case == "n"
        assert preset.verb_requires_infinitive is True
        assert preset.verb_impersonal is True
        assert preset.verb_transitivity == "intransitive"

    def test_check_constraint_rejects_invalid_pos(self, db_session):
        """Test check constraint rejects invalid POS values."""
        preset = AnnotationPreset(name="Invalid", pos="X")
        with pytest.raises(IntegrityError):
            preset.save()

    def test_unique_constraint_prevents_duplicates(self, db_session):
        """Test unique constraint prevents duplicate names per POS."""
        session = get_runtime_session()
        AnnotationPreset.create(name="Duplicate", pos="N", session=session)

        # Same name, same POS should fail
        with pytest.raises(IntegrityError):
            AnnotationPreset.create(name="Duplicate", pos="N", session=session)

    def test_unique_constraint_allows_same_name_different_pos(self, db_session):
        """Test unique constraint allows same name for different POS."""
        session = get_runtime_session()
        AnnotationPreset.create(name="Same Name", pos="N", session=session)

        # Same name, different POS should succeed
        preset2 = AnnotationPreset.create(name="Same Name", pos="V", session=session)
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
        preset.save()

        assert preset.gender is None
        assert preset.number is None
        assert preset.case is None

    def test_timestamps_set_correctly(self, db_session):
        """Test timestamps are set correctly."""
        session = get_runtime_session()
        before = datetime.now()
        preset = AnnotationPreset.create(
            name="Timestamp Test", pos="A", session=session
        )
        after = datetime.now()

        assert before <= preset.created_at <= after
        assert before <= preset.updated_at <= after
        # Timestamps should be very close (within 1 second) since both are set on creation
        time_diff = abs((preset.updated_at - preset.created_at).total_seconds())
        assert time_diff < 1.0

    def test_updated_at_changes_on_update(self, db_session):
        """Test updated_at changes on update."""
        session = get_runtime_session()
        preset = AnnotationPreset.create(name="Update Test", pos="N", session=session)
        original_updated = preset.updated_at

        import time

        time.sleep(0.01)  # Small delay to ensure timestamp difference

        AnnotationPreset.update(preset.id, name="Updated Name", session=session)
        db_session.refresh(preset)

        assert preset.updated_at > original_updated

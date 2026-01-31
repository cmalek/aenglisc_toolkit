"""Unit tests for AnnotationModal and related POS field classes."""

import pytest
import weakref
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QWidget, QVBoxLayout, QApplication

from oeapp.models import Annotation, Idiom
from oeapp.models.annotation_preset import AnnotationPreset
from oeapp.ui.dialogs.annotation_modal import (
    PartOfSpeechFieldsBase,
    NounFields,
    VerbFields,
    PronounFields,
    PrepositionFields,
    AdjectiveFields,
    ArticleFields,
    AdverbFields,
    ConjunctionFields,
    InterjectionFields,
    PartOfSpeechFormManager,
    AnnotationModal,
    NoneFields,
    CLEAR_SENTINEL
)
from tests.conftest import create_test_project, create_test_sentence


class TestPartOfSpeechFieldsBase:
    """Test cases for PartOfSpeechFieldsBase."""

    @pytest.fixture
    def parent_widget(self):
        return QWidget()

    @pytest.fixture
    def layout(self, parent_widget):
        return QFormLayout(parent_widget)

    @pytest.fixture
    def fields_base(self, layout, parent_widget):
        class ConcreteFields(PartOfSpeechFieldsBase):
            PART_OF_SPEECH = "Test"
            def build(self):
                self.add_combo("gender", "Gender", self.GENDER_MAP)
                self.add_combo("number", "Number", self.NUMBER_MAP)

        return ConcreteFields(layout, parent_widget)

    def test_add_combo(self, fields_base):
        fields_base.build()
        assert "gender" in fields_base.fields
        assert "gender" in fields_base.lookup_map
        assert fields_base.fields["gender"].count() == len(fields_base.GENDER_MAP)

    def test_add_field(self, fields_base):
        from PySide6.QtWidgets import QComboBox
        combo = QComboBox()
        fields_base.add_field("test_attr", "Test Label", combo)
        assert "test_attr" in fields_base.fields
        assert fields_base.layout.rowCount() == 1

    def test_clear(self, fields_base):
        fields_base.build()
        fields_base.clear()
        assert not fields_base.fields
        assert not fields_base.lookup_map
        assert not fields_base.code_to_index_map
        assert not fields_base.index_to_code_map

    def test_reset(self, fields_base):
        fields_base.build()
        fields_base.fields["gender"].setCurrentIndex(1)
        fields_base.reset()
        assert fields_base.fields["gender"].currentIndex() == 0

    def test_load_from_indices(self, fields_base):
        fields_base.build()
        fields_base.load_from_indices({"gender": 1, "number": 2})
        assert fields_base.fields["gender"].currentIndex() == 1
        assert fields_base.fields["number"].currentIndex() == 2

    def test_load_from_preset(self, fields_base, db_session):
        fields_base.build()
        preset = AnnotationPreset(name="Test", pos="N", gender="m", number=CLEAR_SENTINEL)
        preset.save()
        fields_base.load_from_preset(preset)
        assert fields_base.fields["gender"].currentIndex() == 1 # m
        assert fields_base.fields["number"].currentIndex() == 0 # CLEAR_SENTINEL sets to 0

    def test_load_from_annotation(self, fields_base):
        fields_base.build()
        ann = Annotation(gender="f")
        fields_base.load_from_annotation(ann)
        # index 0 is empty, 1 is m, 2 is f
        assert fields_base.fields["gender"].currentIndex() == 2

    def test_extract_indices(self, fields_base):
        fields_base.build()
        fields_base.fields["gender"].setCurrentIndex(1)
        indices = fields_base.extract_indices()
        assert indices["gender"] == 1

    def test_extract_values(self, fields_base):
        fields_base.build()
        fields_base.fields["gender"].setCurrentIndex(1) # Masculine (m)
        values = fields_base.extract_values()
        assert values["gender"] == "m"

    def test_update_annotation(self, fields_base):
        fields_base.build()
        fields_base.fields["gender"].setCurrentIndex(1) # m
        ann = Annotation()
        fields_base.update_annotation(ann)
        assert ann.gender == "m"

    def test_update_annotation_invalid_attr(self, fields_base):
        fields_base.fields["invalid_attr"] = MagicMock()
        fields_base.index_to_code_map["invalid_attr"] = {0: "val"}
        ann = Annotation()
        with pytest.raises(AttributeError, match="Invalid Annotation attribute"):
            fields_base.update_annotation(ann)


class TestPartOfSpeechSubclasses:
    """Test cases for specific POS field subclasses."""

    @pytest.mark.parametrize("cls, expected_field_maps", [
        (NounFields, {
            "gender": PartOfSpeechFieldsBase.GENDER_MAP,
            "number": PartOfSpeechFieldsBase.NUMBER_MAP,
            "case": PartOfSpeechFieldsBase.CASE_MAP,
            "declension": PartOfSpeechFieldsBase.DECLENSION_MAP,
        }),
        (VerbFields, {
            "verb_class": PartOfSpeechFieldsBase.VERB_CLASS_MAP,
            "verb_tense": PartOfSpeechFieldsBase.VERB_TENSE_MAP,
            "verb_mood": PartOfSpeechFieldsBase.VERB_MOOD_MAP,
            "verb_person": PartOfSpeechFieldsBase.VERB_PERSON_MAP,
            "number": PartOfSpeechFieldsBase.NUMBER_MAP,
            "verb_aspect": PartOfSpeechFieldsBase.VERB_ASPECT_MAP,
            "verb_form": PartOfSpeechFieldsBase.VERB_FORM_MAP,
            "verb_direct_object_case": PartOfSpeechFieldsBase.VERB_DIRECT_OBJECT_CASE_MAP,
        }),
        (PronounFields, {
            "pronoun_type": PartOfSpeechFieldsBase.PRONOUN_TYPE_MAP,
            "gender": PartOfSpeechFieldsBase.GENDER_MAP,
            "pronoun_number": PartOfSpeechFieldsBase.PRONOUN_NUMBER_MAP,
            "case": PartOfSpeechFieldsBase.CASE_MAP,
        }),
        (PrepositionFields, {
            "prep_case": PartOfSpeechFieldsBase.PREPOSITION_CASE_MAP,
        }),
        (AdjectiveFields, {
            "adjective_degree": PartOfSpeechFieldsBase.ADJECTIVE_DEGREE_MAP,
            "adjective_inflection": PartOfSpeechFieldsBase.ADJECTIVE_INFLECTION_MAP,
            "gender": PartOfSpeechFieldsBase.GENDER_MAP,
            "number": PartOfSpeechFieldsBase.NUMBER_MAP,
            "case": PartOfSpeechFieldsBase.CASE_MAP,
        }),
        (ArticleFields, {
            "article_type": PartOfSpeechFieldsBase.ARTICLE_TYPE_MAP,
            "gender": PartOfSpeechFieldsBase.GENDER_MAP,
            "number": PartOfSpeechFieldsBase.NUMBER_MAP,
            "case": PartOfSpeechFieldsBase.CASE_MAP,
        }),
        (AdverbFields, {
            "adverb_degree": PartOfSpeechFieldsBase.ADVERB_DEGREE_MAP,
        }),
        (ConjunctionFields, {
            "conjunction_type": PartOfSpeechFieldsBase.CONJUNCTION_TYPE_MAP,
        }),
        (InterjectionFields, {}),
        (NoneFields, {}),
    ])
    def test_subclass_build_and_items(self, cls, expected_field_maps):
        parent = QWidget()
        layout = QFormLayout(parent)
        fields = cls(layout, parent)
        fields.build()

        # Verify all expected fields exist
        assert len(fields.fields) == len(expected_field_maps)

        for field_name, expected_map in expected_field_maps.items():
            assert field_name in fields.fields
            combo = fields.fields[field_name]

            # Verify combo items match the lookup map
            expected_items = list(expected_map.values())
            actual_items = [combo.itemText(i) for i in range(combo.count())]
            assert actual_items == expected_items


class TestPartOfSpeechFormManager:
    """Test cases for PartOfSpeechFormManager."""

    @pytest.fixture
    def manager(self):
        parent = QWidget()
        layout = QVBoxLayout(parent)
        return PartOfSpeechFormManager(layout, parent)

    def test_select_pos(self, manager):
        manager.select("N")
        assert isinstance(manager.current, NounFields)
        assert manager.container_layout.count() > 0

    def test_select_none(self, manager):
        manager.select(None)
        assert isinstance(manager.current, NoneFields)
        # N/A has no fields, but it should still have its layout in the container
        assert manager.container_layout.count() > 0

    def test_select_invalid(self, manager):
        with pytest.raises(ValueError, match="Invalid Part of Speech"):
            manager.select("INVALID")

    def test_select_rebuild(self, manager):
        manager.select("N")
        assert manager.container_layout.count() > 0

        # Test that switching POS clears the layout and creates a new one
        prev_fields = manager.current
        manager.select("V")
        assert manager.container_layout.count() > 0
        assert manager.current is not prev_fields

    def test_reset(self, manager):
        manager.select("N")
        manager.current.fields["gender"].setCurrentIndex(1)
        manager.reset()
        assert manager.current.fields["gender"].currentIndex() == 0

    def test_load_from_indices(self, manager):
        manager.select("N")
        manager.load_from_indices({"gender": 1})
        assert manager.current.fields["gender"].currentIndex() == 1

    def test_load_from_preset(self, manager, db_session):
        manager.select("N")
        preset = AnnotationPreset(name="Test", pos="N", gender="m")
        preset.save()
        manager.load_from_preset(preset)
        assert manager.current.fields["gender"].currentIndex() == 1

    def test_load_from_annotation(self, manager):
        manager.select("N")
        ann = Annotation(gender="f")
        manager.load_from_annotation(ann)
        assert manager.current.fields["gender"].currentIndex() == 2

    def test_extract_indices(self, manager):
        manager.select("N")
        manager.current.fields["gender"].setCurrentIndex(1)
        indices = manager.extract_indices()
        assert indices["gender"] == 1

    def test_extract_values_delegation(self, manager):
        manager.select("N")
        manager.current.fields["gender"].setCurrentIndex(1)
        values = manager.extract_values()
        assert values["gender"] == "m"

    def test_update_annotation(self, manager):
        manager.select("N")
        manager.current.fields["gender"].setCurrentIndex(1)
        ann = Annotation()
        manager.update_annotation(ann)
        assert ann.gender == "m"


class TestPOSFieldModelMapping:
    """Test that all POS fields map to valid Annotation model attributes."""

    @pytest.mark.parametrize("cls", [
        NounFields, VerbFields, PronounFields, PrepositionFields,
        AdjectiveFields, ArticleFields, AdverbFields, ConjunctionFields,
        InterjectionFields, NoneFields
    ])
    def test_fields_map_to_model_attributes(self, cls):
        parent = QWidget()
        layout = QFormLayout(parent)
        fields_obj = cls(layout, parent)
        fields_obj.build()

        valid_attributes = {column.name for column in Annotation.__table__.columns}

        for attr in fields_obj.fields:
            assert attr in valid_attributes, f"POS class {cls.__name__} has invalid attribute mapping: {attr}"

    @pytest.mark.parametrize("cls, attr, expected_map", [
        (PronounFields, "pronoun_number", PartOfSpeechFieldsBase.PRONOUN_NUMBER_MAP),
    ])
    def test_special_field_maps(self, cls, attr, expected_map):
        """Test that fields requiring special maps (like PRONOUN_NUMBER_MAP) use them."""
        parent = QWidget()
        layout = QFormLayout(parent)
        fields_obj = cls(layout, parent)
        fields_obj.build()

        assert attr in fields_obj.lookup_map
        assert fields_obj.lookup_map[attr] == expected_map


class TestAnnotationModal:
    """Test cases for AnnotationModal."""

    @pytest.fixture
    def token(self, db_session):
        """Create a test token."""
        project = create_test_project(db_session, name="Test Project")
        sentence = create_test_sentence(
            db_session, project_id=project.id, text="Se cyning"
        )
        return sentence.tokens[1]  # "cyning"

    def test_init_without_annotation(self, qtbot, token):
        """Test initialization without an existing annotation."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        assert modal.token == token
        assert modal.pos_combo.currentIndex() == 0

    def test_init_with_annotation(self, qtbot, token, db_session):
        """Test initialization with an existing annotation."""
        annotation = db_session.get(Annotation, token.id)
        annotation.pos = "N"
        annotation.gender = "m"
        annotation.save()

        modal = AnnotationModal(token=token, annotation=annotation)
        qtbot.addWidget(modal)

        assert modal.pos_combo.currentText() == "Noun (N)"
        manager = modal.part_of_speech_manager
        assert manager.current.fields["gender"].currentText() == "Masculine (m)"

    def test_pos_selection_changes_fields(self, qtbot, token):
        """Test that changing POS updates the dynamic fields."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        # Initially NoneFields
        assert isinstance(modal.part_of_speech_manager.current, NoneFields)

        # Select Noun
        modal.pos_combo.setCurrentText("Noun (N)")
        assert isinstance(modal.part_of_speech_manager.current, NounFields)
        assert "gender" in modal.part_of_speech_manager.current.fields

    def test_apply_saves_to_db(self, qtbot, token, db_session):
        """Test that clicking Apply saves values to the database."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        modal.pos_combo.setCurrentText("Noun (N)")
        modal.part_of_speech_manager.current.fields["gender"].setCurrentIndex(2) # Feminine (f)
        modal.confidence_slider.setValue(90)

        with qtbot.waitSignal(modal.annotation_applied, timeout=1000):
            qtbot.mouseClick(modal.apply_button, Qt.LeftButton)

        modal.annotation.save()
        db_session.expire_all()
        ann = db_session.get(Annotation, token.id)
        assert ann.pos == "N"
        assert ann.gender == "f"
        assert ann.confidence == 90

    def test_clear_all(self, qtbot, token):
        """Test that Clear All button resets the form."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        modal.pos_combo.setCurrentText("Noun (N)")
        modal.modern_english_edit.setText("test")

        qtbot.mouseClick(modal.clear_button, Qt.LeftButton)

        assert modal.pos_combo.currentIndex() == 0
        assert modal.modern_english_edit.text() == ""

    def test_idiom_init(self, qtbot, token, db_session):
        """Test initialization with an idiom."""
        sentence = token.sentence
        tokens = list(sentence.tokens)
        idiom = Idiom(
            sentence_id=sentence.id,
            start_token_id=tokens[0].id,
            end_token_id=tokens[-1].id,
        )
        idiom.save()
        db_session.commit()

        class DummyParent(QWidget):
            def __init__(self, tokens):
                super().__init__()
                self.oe_text_edit = MagicMock()
                self.oe_text_edit.tokens = tokens

        modal = AnnotationModal(idiom=idiom, parent=DummyParent(tokens))
        qtbot.addWidget(modal)
        assert modal.idiom == idiom

    def test_presets_apply(self, qtbot, token, db_session):
        """Test applying a preset."""
        preset = AnnotationPreset(
            name="Test Preset",
            pos="N",
            gender="m",
        )
        preset.save()
        db_session.commit()

        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        modal.pos_combo.setCurrentText("Noun (N)")

        # Wait for presets to load
        qtbot.waitUntil(lambda: modal.preset_combo.count() > 1, timeout=2000)
        modal.preset_combo.setCurrentText("Test Preset")

        qtbot.mouseClick(modal.apply_preset_button, Qt.LeftButton)
        assert modal.part_of_speech_manager.current.fields["gender"].currentText() == "Masculine (m)"

    def test_metadata_fields_load(self, qtbot, token, db_session):
        """Test that metadata fields are loaded correctly from annotation."""
        ann = db_session.get(Annotation, token.id)
        ann.confidence = 42
        ann.modern_english_meaning = "test meaning"
        ann.root = "test root"
        ann.pos = "N" # POS must be set for load() to proceed past the first check
        ann.save()

        modal = AnnotationModal(token=token, annotation=ann)
        qtbot.addWidget(modal)

        assert modal.confidence_slider.value() == 42
        assert modal.confidence_label.text() == "42%"
        assert modal.modern_english_edit.text() == "test meaning"
        assert modal.root_edit.text() == "test root"

    def test_metadata_fields_save(self, qtbot, token, db_session):
        """Test that metadata fields are saved correctly to annotation."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        modal.confidence_slider.setValue(85)
        modal.modern_english_edit.setText("  saved meaning  ")
        modal.root_edit.setText("  saved root  ")

        qtbot.mouseClick(modal.apply_button, Qt.LeftButton)

        ann = modal.annotation
        assert ann.confidence == 85
        assert ann.modern_english_meaning == "saved meaning" # trimmed
        assert ann.root == "saved root" # trimmed

    def test_metadata_fields_clear(self, qtbot, token):
        """Test that Clear All button resets metadata fields."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        modal.confidence_slider.setValue(10)
        modal.modern_english_edit.setText("something")
        modal.root_edit.setText("something else")
        modal.todo_check.setChecked(True)

        qtbot.mouseClick(modal.clear_button, Qt.LeftButton)

        assert modal.confidence_slider.value() == 100
        assert modal.modern_english_edit.text() == ""
        assert modal.root_edit.text() == ""
        assert modal.todo_check.isChecked() == False

    def test_confidence_label_updates_on_slider_move(self, qtbot, token):
        """Test that the confidence label updates when slider value changes."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)

        modal.confidence_slider.setValue(75)
        assert modal.confidence_label.text() == "75%"

        modal.confidence_slider.setValue(0)
        assert modal.confidence_label.text() == "0%"


class TestAnnotationModalLifecycle:
    """Test cases for the lifecycle and repeated opening of AnnotationModal."""

    @pytest.fixture
    def token(self, db_session):
        """Create a test token."""
        project = create_test_project(db_session, name="Lifecycle Project")
        sentence = create_test_sentence(
            db_session, project_id=project.id, text="Se cyning ricsode"
        )
        return sentence.tokens  # "Se", "cyning", "ricsode"

    def test_wa_delete_on_close_is_set(self, qtbot, token):
        """Verify that WA_DeleteOnClose is set to ensure cleanup."""
        modal = AnnotationModal(token=token[0])
        qtbot.addWidget(modal)
        assert modal.testAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

    def test_repeated_opening_on_same_token(self, qtbot, token):
        """Test that fields are correctly loaded when opening multiple times on same token."""
        # First opening
        modal1 = AnnotationModal(token=token[1])
        qtbot.addWidget(modal1)
        modal1.show()
        modal1.pos_combo.setCurrentText("Noun (N)")

        # Capture weak references to fields
        gender_combo1 = modal1.part_of_speech_manager.current.fields["gender"]
        weak_gender1 = weakref.ref(gender_combo1)

        assert isinstance(modal1.part_of_speech_manager.current, NounFields)
        assert not gender_combo1.isWindow()

        # Cancel the modal
        modal1.reject()

        # Second opening
        modal2 = AnnotationModal(token=token[1])
        qtbot.addWidget(modal2)
        modal2.show()
        modal2.pos_combo.setCurrentText("Noun (N)")

        gender_combo2 = modal2.part_of_speech_manager.current.fields["gender"]

        assert gender_combo2 is not gender_combo1

        # Verify old fields are not top-level windows
        old_gender = weak_gender1()
        if old_gender is not None:
            assert not old_gender.isWindow()

        assert not gender_combo2.isWindow()
        assert gender_combo2.window() == modal2.window()
        modal2.accept()

    def test_opening_on_different_tokens(self, qtbot, token):
        """Test that fields correctly appear when switching between different tokens."""
        # Open on token 1 (cyning - Noun)
        modal1 = AnnotationModal(token=token[1])
        qtbot.addWidget(modal1)
        modal1.pos_combo.setCurrentText("Noun (N)")
        assert isinstance(modal1.part_of_speech_manager.current, NounFields)
        modal1.accept()

        # Open on token 2 (ricsode - Verb)
        modal2 = AnnotationModal(token=token[2])
        qtbot.addWidget(modal2)
        modal2.pos_combo.setCurrentText("Verb (V)")
        assert isinstance(modal2.part_of_speech_manager.current, VerbFields)
        modal2.accept()

    def test_no_extra_top_level_windows(self, qtbot, token):
        """Verify that no extra top-level windows are created (floating fields)."""
        initial_windows = [w for w in QApplication.topLevelWidgets() if w.isVisible()]

        modal = AnnotationModal(token=token[1])
        qtbot.addWidget(modal)
        modal.show()

        # Select a POS to trigger dynamic field creation
        modal.pos_combo.setCurrentText("Noun (N)")

        # We should only see the modal as a new visible top-level window
        current_windows = [w for w in QApplication.topLevelWidgets() if w.isVisible()]
        # Filter out potential internal Qt windows or the main window if it exists
        new_windows = [w for w in current_windows if w not in initial_windows]

        assert len(new_windows) == 1, f"Expected 1 new window (the modal), found {len(new_windows)}: {new_windows}"
        assert new_windows[0] == modal

        modal.reject()

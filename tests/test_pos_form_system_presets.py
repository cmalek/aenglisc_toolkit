"""Preset POS form behaviour after the catalog refactor."""

import pytest
from PySide6.QtWidgets import QFormLayout, QWidget

from oeapp.ui.dialogs.pos_form_system import (
    CLEAR_SENTINEL,
    PresetPartOfSpeechFieldsBase,
    PresetPosFormManager,
)


def _build(pos):
    parent = QWidget()
    fields = PresetPartOfSpeechFieldsBase(QFormLayout(parent), parent, pos)
    fields.build()
    return parent, fields


def test_declension_extracts_the_code_not_the_label(qapp):
    _parent, fields = _build("N")
    combo = fields.fields["declension"]
    combo.setCurrentIndex(combo.findText("Strong (s)"))
    assert fields.extract_values()["declension"] == "s"


def test_verb_class_round_trips_the_code(qapp):
    _parent, fields = _build("V")
    fields.load_from_values({"verb_class": "pp"})
    assert fields.fields["verb_class"].currentText() == "Preterite-Present (pp)"
    assert fields.extract_values()["verb_class"] == "pp"


def test_declension_and_verb_class_have_no_clear_choice(qapp):
    _p, noun = _build("N")
    _p2, verb = _build("V")
    assert noun.fields["declension"].findText("Clear") == -1
    assert verb.fields["verb_class"].findText("Clear") == -1


def test_ordinary_field_still_round_trips_the_clear_sentinel(qapp):
    _parent, fields = _build("N")
    fields.load_from_values({"gender": CLEAR_SENTINEL})
    assert fields.fields["gender"].currentText() == "Clear"
    assert fields.extract_values()["gender"] == CLEAR_SENTINEL


def test_label_form_value_loads_as_blank_without_crashing(qapp):
    """A pre-migration row holding a label must not break the dialog."""
    _parent, fields = _build("N")
    fields.load_from_values({"declension": "Strong (s)"})
    assert fields.fields["declension"].currentIndex() == 0
    assert fields.extract_values()["declension"] is None


def test_manager_accepts_only_preset_supported_pos(qapp):
    parent = QWidget()
    for pos in ("N", "V", "A", "R", "D"):
        PresetPosFormManager(pos, QFormLayout(parent), parent)
    for pos in ("E", "B", "C", "I", "L", "Z"):
        with pytest.raises(ValueError, match="Unsupported preset Part of Speech"):
            PresetPosFormManager(pos, QFormLayout(parent), parent)


def test_object_names_are_derived(qapp):
    _p, noun = _build("N")
    _p2, verb = _build("V")
    assert noun.fields["gender"].objectName() == "n_gender_combo"
    assert verb.fields["verb_class"].objectName() == "v_verb_class_combo"


@pytest.mark.parametrize("pos", ["N", "V", "A", "R", "D"])
def test_boolean_and_blank_semantics_survive(qapp, pos):
    _parent, fields = _build(pos)
    assert all(combo.itemText(0) == "" for combo in fields.fields.values())
    assert set(fields.extract_values().values()) == {None}

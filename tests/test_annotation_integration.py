import pytest
from PySide6.QtCore import Qt
from oeapp.models import Annotation
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.dialogs.annotation_modal import AnnotationModal
from tests.conftest import create_test_project

@pytest.fixture
def sentence_card(db_session, qapp, mock_main_window):
    """Create a SentenceCard for testing."""
    project = create_test_project(db_session, name="Integration Test Project", text="Se cyning ricsode.")
    sentence = project.sentences[0]
    card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
    card.show()
    return card

@pytest.mark.parametrize("pos_name, pos_code, field_values", [
    ("Noun (N)", "N", {"gender": 1, "number": 1, "case": 1, "declension": 1}),  # m, s, n, s
    ("Verb (V)", "V", {"verb_class": 1, "verb_tense": 1, "verb_mood": 1, "verb_person": 1, "number": 1}),
    ("Adjective (A)", "A", {"adjective_degree": 1, "adjective_inflection": 1, "gender": 1, "number": 1, "case": 1}),
    ("Pronoun (R)", "R", {"pronoun_type": 1, "gender": 1, "pronoun_number": 1, "case": 1}),
    ("Determiner/Article (D)", "D", {"article_type": 1, "gender": 1, "number": 1, "case": 1}),
    ("Adverb (B)", "B", {"adverb_degree": 1}),
    ("Conjunction (C)", "C", {"conjunction_type": 1}),
    ("Preposition (E)", "E", {"prep_case": 1}),
    ("Interjection (I)", "I", {}),
    ("Number (L)", "L", {}),
])
def test_all_pos_fields_save_via_modal(qtbot, sentence_card, db_session, pos_name, pos_code, field_values):
    """
    Integration test to ensure that all fields for all parts of speech
    are correctly saved when using the AnnotationModal within a SentenceCard.
    """
    token = sentence_card.sentence.tokens[0]

    # 1. Open the modal
    modal = AnnotationModal(token=token, parent=sentence_card)
    modal.annotation_applied.connect(sentence_card._on_annotation_applied)
    qtbot.addWidget(modal)
    modal.show()

    # 2. Select POS
    modal.pos_combo.setCurrentText(pos_name)

    # 3. Set field values
    for field_name, index in field_values.items():
        assert field_name in modal.part_of_speech_manager.current.fields
        modal.part_of_speech_manager.current.fields[field_name].setCurrentIndex(index)

    # 4. Click Apply
    with qtbot.waitSignal(modal.annotation_applied, timeout=2000):
        qtbot.mouseClick(modal.apply_button, Qt.LeftButton)

    # 5. Verify database
    db_session.expire_all()
    ann = db_session.get(Annotation, token.id)
    assert ann is not None
    assert ann.pos == pos_code

    # Verify each field
    # We need to map indices back to codes for verification
    fields_obj = modal.part_of_speech_manager.current
    for field_name, index in field_values.items():
        expected_code = fields_obj.index_to_code_map[field_name].get(index)
        actual_code = getattr(ann, field_name)
        assert actual_code == expected_code, f"Field {field_name} mismatch for POS {pos_code}"

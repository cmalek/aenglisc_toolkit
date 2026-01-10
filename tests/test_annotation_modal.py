"""Unit tests for AnnotationModal using pytest-qt and real database."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QWidget

from oeapp.models.annotation import Annotation
from oeapp.models.annotation_preset import AnnotationPreset
from oeapp.models.idiom import Idiom
from oeapp.ui.dialogs.annotation_modal import AnnotationModal
from tests.conftest import create_test_project, create_test_sentence


class TestAnnotationModal:
    """Test cases for AnnotationModal."""

    @pytest.fixture
    def token(self, db_session):
        """Create a test token."""
        project = create_test_project(db_session, name="Test Project")
        sentence = create_test_sentence(
            db_session, project_id=project.id, text="Se cyning"
        )
        # Token.create_from_sentence already creates an empty annotation for each token
        return sentence.tokens[1]  # "cyning"

    def test_init_without_annotation(self, qtbot, token):
        """Test initialization without an existing annotation (uses token's existing empty one)."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        assert modal.token == token
        assert modal.annotation.token_id == token.id
        assert modal.pos_combo.currentIndex() == 0
        assert modal.pos_combo.currentText() == ""

    def test_init_with_annotation(self, qtbot, token, db_session):
        """Test initialization with an existing annotation."""
        # Retrieve the existing empty annotation and update it
        annotation = db_session.get(Annotation, token.id)
        annotation.pos = "N"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.declension = "s"
        annotation.confidence = 75
        annotation.modern_english_meaning = "king"
        annotation.root = "cyning"
        annotation.save()

        modal = AnnotationModal(token=token, annotation=annotation)
        qtbot.addWidget(modal)
        modal.show()
        # qtbot.waitForWindowShown(modal) # Deprecated, use waitExposed if needed but show() often enough

        # Verify POS selection
        assert modal.pos_combo.currentText() == "Noun (N)"

        # Verify dynamic fields were loaded with verbose names
        assert modal.gender_combo.currentText() == "Masculine (m)"
        assert modal.number_combo.currentText() == "Singular (s)"
        assert modal.case_combo.currentText() == "Nominative (n)"
        assert modal.declension_combo.currentText() == "Strong (s)"

        # Verify metadata
        assert modal.confidence_slider.value() == 75
        assert modal.modern_english_edit.text() == "king"
        assert modal.root_edit.text() == "cyning"

    def test_pos_selection_changes_fields(self, qtbot, token):
        """Test that changing POS updates the dynamic fields visibility."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Initially no POS fields (besides POS selection itself)
        assert modal.fields_layout.rowCount() == 0

        # Select Noun
        modal.pos_combo.setCurrentText("Noun (N)")
        assert hasattr(modal, "gender_combo")
        assert hasattr(modal, "declension_combo")
        assert modal.fields_layout.rowCount() > 0

        # Select Verb
        modal.pos_combo.setCurrentText("Verb (V)")
        assert not hasattr(modal, "gender_combo")
        assert hasattr(modal, "verb_class_combo")
        assert hasattr(modal, "verb_tense_combo")

        # Select Empty
        modal.pos_combo.setCurrentIndex(0)
        assert modal.fields_layout.rowCount() == 0

    def test_apply_saves_noun_to_db(self, qtbot, token, db_session):
        """Test that filling noun fields and clicking Apply saves to DB."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Fill fields
        modal.pos_combo.setCurrentText("Noun (N)")
        # Use indices to avoid text matching issues
        modal.gender_combo.setCurrentIndex(2)  # Feminine (f)
        modal.number_combo.setCurrentIndex(2)  # Plural (p)
        modal.case_combo.setCurrentIndex(4)    # Dative (d)
        modal.declension_combo.setCurrentIndex(2) # Weak (w)

        modal.confidence_slider.setValue(90)
        modal.modern_english_edit.setText("kings")
        modal.root_edit.setText("cyning")
        modal.todo_check.setChecked(True)

        # Click Apply
        with qtbot.waitSignal(modal.annotation_applied, timeout=1000):
            qtbot.mouseClick(modal.apply_button, Qt.LeftButton)

        # The modal emits the signal but doesn't save. We must save it in the test.
        modal.annotation.save()

        # Verify in database
        db_session.expire_all()
        ann = db_session.get(Annotation, token.id)
        assert ann is not None
        assert ann.pos == "N"
        assert ann.gender == "f"
        assert ann.number == "p"
        assert ann.case == "d"
        assert ann.declension == "w"
        assert ann.confidence == 90
        assert ann.modern_english_meaning == "kings"
        assert ann.root == "cyning"

    def test_apply_saves_verb_to_db(self, qtbot, token, db_session):
        """Test that filling verb fields and clicking Apply saves to DB."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Fill fields
        modal.pos_combo.setCurrentText("Verb (V)")
        modal.verb_class_combo.setCurrentIndex(6) # Strong Class 1 (s1)
        modal.verb_tense_combo.setCurrentIndex(1) # Past (p)
        modal.verb_mood_combo.setCurrentIndex(1)  # Indicative (i)
        modal.verb_person_combo.setCurrentIndex(3) # 3rd
        modal.verb_number_combo.setCurrentIndex(1) # Singular (s)

        # Click Apply
        qtbot.mouseClick(modal.apply_button, Qt.LeftButton)
        modal.annotation.save()

        # Verify in database
        db_session.expire_all()
        ann = db_session.get(Annotation, token.id)
        assert ann is not None
        assert ann.pos == "V"
        assert ann.verb_class == "s1"
        assert ann.verb_tense == "p"
        assert ann.verb_mood == "i"
        assert ann.verb_person == "3"
        assert ann.number == "s"

    def test_clear_all_resets_form(self, qtbot, token):
        """Test that Clear All button resets the form fields."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Fill some values
        modal.pos_combo.setCurrentText("Noun (N)")
        modal.gender_combo.setCurrentIndex(1)
        modal.confidence_slider.setValue(50)
        modal.modern_english_edit.setText("something")

        # Click Clear All
        qtbot.mouseClick(modal.clear_button, Qt.LeftButton)

        # Verify reset
        assert modal.pos_combo.currentIndex() == 0
        assert modal.confidence_slider.value() == 100
        assert modal.modern_english_edit.text() == ""
        assert modal.fields_layout.rowCount() == 0

    def test_init_with_idiom_annotation(self, qtbot, token, db_session):
        """Test initialization when idiom is annotated."""
        sentence = token.sentence
        tokens = list(sentence.tokens)
        idiom = Idiom(
            sentence_id=sentence.id,
            start_token_id=tokens[0].id,
            end_token_id=tokens[-1].id,
        )
        idiom.save()
        annotation = Annotation(idiom_id=idiom.id, pos="N")
        annotation.save()
        db_session.commit()

        class DummySentenceCard(QWidget):
            def __init__(self, tokens):
                super().__init__()
                self.oe_text_edit = MagicMock()
                self.oe_text_edit.tokens = tokens

        dummy_parent = DummySentenceCard(tokens)
        modal = AnnotationModal(idiom=idiom, annotation=annotation, parent=dummy_parent)
        modal.show()
        assert modal.idiom == idiom
        assert modal.annotation.idiom_id == idiom.id
        # Ensure idiom header exposes each token as a clickable button
        buttons = [
            btn
            for btn in modal.findChildren(QPushButton)
            if btn.text() in {tokens[0].surface, tokens[-1].surface}
        ]
        assert buttons
        qtbot.wait(200)
        modal.close()

    def test_shortcuts_select_pos(self, qtbot, token):
        """Test keyboard shortcuts for POS selection."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()
        modal.setFocus()
        QApplication.processEvents()

        # Shortcut 'N' for Noun
        qtbot.keyClick(modal, Qt.Key_N)
        QApplication.processEvents()
        assert modal.pos_combo.currentText() == "Noun (N)"

        # Shortcut 'V' for Verb
        qtbot.keyClick(modal, Qt.Key_V)
        QApplication.processEvents()
        assert modal.pos_combo.currentText() == "Verb (V)"

        # Shortcut 'A' for Adjective
        qtbot.keyClick(modal, Qt.Key_A)
        assert modal.pos_combo.currentText() == "Adjective (A)"

    def test_presets_apply(self, qtbot, token, db_session):
        """Test applying a preset to the form."""
        # Create a preset
        preset = AnnotationPreset(
            name="Strong Masc Nom Sing",
            pos="N",
            gender="m",
            number="s",
            case="n",
            declension="s",
        )
        preset.save()

        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Select Noun POS so presets are loaded
        modal.pos_combo.setCurrentText("Noun (N)")

        # Wait for presets to load (happens via QTimer)
        qtbot.waitUntil(lambda: modal.preset_combo.count() > 1, timeout=1000)

        # Select preset
        modal.preset_combo.setCurrentText("Strong Masc Nom Sing")

        # Click Apply Preset
        qtbot.mouseClick(modal.apply_preset_button, Qt.LeftButton)

        # Verify fields updated with verbose names
        assert modal.gender_combo.currentText() == "Masculine (m)"
        assert modal.number_combo.currentText() == "Singular (s)"
        assert modal.case_combo.currentText() == "Nominative (n)"
        assert modal.declension_combo.currentText() == "Strong (s)"

    def test_save_as_preset_opens_dialog(self, qtbot, token, db_session, monkeypatch):
        """Test that Save as Preset button opens the management dialog."""
        # Mock QMessageBox to prevent blocking
        monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)
        monkeypatch.setattr(QMessageBox, "critical", lambda *args, **kwargs: None)

        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        modal.pos_combo.setCurrentText("Noun (N)")
        modal.gender_combo.setCurrentText("Masculine (m)")

        # Mock the dialog execution
        mock_exec = []
        def mock_dialog_exec(self):
            mock_exec.append(self)
            return True

        from oeapp.ui.dialogs.annotation_preset_management import AnnotationPresetManagementDialog
        monkeypatch.setattr(AnnotationPresetManagementDialog, "exec", mock_dialog_exec)

        # Patch _on_save_as_preset directly to avoid MainWindow dependencies in this test
        def mock_on_save():
            # Minimal logic needed for the test
            pos = modal.PART_OF_SPEECH_REVERSE_MAP.get(modal.pos_combo.currentText())
            field_values = modal._extract_current_field_values()
            dialog = AnnotationPresetManagementDialog(
                save_mode=True,
                initial_pos=pos,
                initial_field_values=field_values,
            )
            dialog.exec()
            modal._refresh_preset_dropdown()

        monkeypatch.setattr(modal, "_on_save_as_preset", mock_on_save)

        # Click Save as Preset
        qtbot.mouseClick(modal.save_as_preset_button, Qt.LeftButton)

        assert len(mock_exec) == 1
        assert mock_exec[0].initial_pos == "N"
        assert mock_exec[0].initial_field_values["gender"] == "m"

    def test_cancel_button(self, qtbot, token):
        """Test that Cancel button closes the dialog without applying."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        modal.pos_combo.setCurrentText("Noun (N)")

        # Click Cancel
        qtbot.mouseClick(modal.cancel_button, Qt.LeftButton)

        assert modal.result() == AnnotationModal.Rejected

    @pytest.mark.parametrize("pos_code, pos_name", [
        ("A", "Adjective (A)"),
        ("R", "Pronoun (R)"),
        ("D", "Determiner/Article (D)"),
        ("E", "Preposition (E)"),
        ("B", "Adverb (B)"),
        ("C", "Conjunction (C)"),
        ("I", "Interjection (I)"),
    ])
    def test_all_pos_types_load_and_save(self, qtbot, token, db_session, pos_code, pos_name):
        """Test that all supported POS types can be selected, filled, and saved."""
        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Select POS
        modal.pos_combo.setCurrentText(pos_name)
        assert modal.pos_combo.currentText() == pos_name

        # For some POS types, fill at least one field if available
        if pos_code == "A":
            modal.adj_degree_combo.setCurrentIndex(1)
            modal.adj_inflection_combo.setCurrentIndex(1)
        elif pos_code == "R":
            modal.pro_type_combo.setCurrentIndex(1)
        elif pos_code == "D":
            modal.article_type_combo.setCurrentIndex(1)
        elif pos_code == "E":
            modal.prep_case_combo.setCurrentIndex(1)
        elif pos_code == "B":
            modal.adv_degree_combo.setCurrentIndex(1)
        elif pos_code == "C":
            modal.conj_type_combo.setCurrentIndex(1)

        # Apply
        qtbot.mouseClick(modal.apply_button, Qt.LeftButton)
        modal.annotation.save()

        # Verify in DB
        db_session.expire_all()
        ann = db_session.get(Annotation, token.id)
        assert ann.pos == pos_code

        # Reload and verify verbose names
        modal2 = AnnotationModal(token=token, annotation=ann)
        qtbot.addWidget(modal2)
        modal2.show()
        assert modal2.pos_combo.currentText() == pos_name

        if pos_code == "A":
            assert modal2.adj_degree_combo.currentIndex() == 1
        elif pos_code == "R":
            assert modal2.pro_type_combo.currentIndex() == 1
        elif pos_code == "D":
            assert modal2.article_type_combo.currentIndex() == 1
        elif pos_code == "E":
            assert modal2.prep_case_combo.currentIndex() == 1
        elif pos_code == "B":
            assert modal2.adv_degree_combo.currentIndex() == 1
        elif pos_code == "C":
            assert modal2.conj_type_combo.currentIndex() == 1

    def test_presets_clear_sentinel(self, qtbot, token, db_session):
        """Test applying a preset with the CLEAR_SENTINEL value."""
        from oeapp.ui.dialogs.annotation_preset_management import CLEAR_SENTINEL

        # Create a preset that clears gender
        preset = AnnotationPreset(
            name="Clear Gender",
            pos="N",
            gender=CLEAR_SENTINEL,
        )
        preset.save()

        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Set gender first
        modal.pos_combo.setCurrentText("Noun (N)")
        modal.gender_combo.setCurrentIndex(1)
        assert modal.gender_combo.currentIndex() == 1

        # Wait for presets to load
        qtbot.waitUntil(lambda: modal.preset_combo.count() > 1, timeout=1000)
        modal.preset_combo.setCurrentText("Clear Gender")

        # Apply
        qtbot.mouseClick(modal.apply_preset_button, Qt.LeftButton)

        # Verify gender is cleared (index 0)
        assert modal.gender_combo.currentIndex() == 0

    def test_on_save_as_preset_error_handling(self, qtbot, token, monkeypatch):
        """Test error handling in _on_save_as_preset."""
        from PySide6.QtWidgets import QMessageBox
        mock_warning = []
        monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: mock_warning.append(args))

        modal = AnnotationModal(token=token)
        qtbot.addWidget(modal)
        modal.show()

        # Select POS
        modal.pos_combo.setCurrentText("Noun (N)")

        # Use the ORIGINAL _on_save_as_preset for this test.
        # It will fail to find MainWindow and show warning.
        modal._on_save_as_preset()

        assert len(mock_warning) > 0
        assert "Could not find main window" in mock_warning[0][2]

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox
from oeapp.ui.dialogs.sentence_filters import (
    PartOfSpeechFilterDialog,
    CaseFilterDialog,
    NumberFilterDialog,
)
from oeapp.ui.mixins import AnnotationLookupsMixin

class TestSentenceFilters:
    @pytest.fixture
    def pos_dialog(self, qapp, qtbot):
        dialog = PartOfSpeechFilterDialog()
        qtbot.addWidget(dialog)
        return dialog

    @pytest.fixture
    def case_dialog(self, qapp, qtbot):
        dialog = CaseFilterDialog()
        qtbot.addWidget(dialog)
        return dialog

    @pytest.fixture
    def number_dialog(self, qapp, qtbot):
        dialog = NumberFilterDialog()
        qtbot.addWidget(dialog)
        return dialog

    def test_pos_dialog_initialization(self, pos_dialog):
        """Test that POS dialog is initialized with correct items."""
        assert pos_dialog.windowTitle() == "" # It's a dialog title, TITLE class var is used in build() for a label
        # The TITLE ClassVar is used for a label in the dialog, not windowTitle() explicitly set in __init__
        # Let's check the checkboxes
        expected_codes = {k for k in AnnotationLookupsMixin.PART_OF_SPEECH_MAP if k not in [None, ""]}
        assert set(pos_dialog.checkboxes.keys()) == expected_codes
        
        # All checkboxes should be checked by default
        for checkbox in pos_dialog.checkboxes.values():
            assert checkbox.isChecked()

    def test_pos_dialog_selection_changed(self, pos_dialog, qtbot):
        """Test that toggling a checkbox emits selection_changed signal."""
        # Find a code to toggle
        code_to_toggle = "N"
        checkbox = pos_dialog.checkboxes[code_to_toggle]
        assert checkbox.isChecked()

        with qtbot.waitSignal(pos_dialog.selection_changed, timeout=1000) as blocker:
            checkbox.setChecked(False)
            
        # N should now be deselected
        assert code_to_toggle not in blocker.args[0]
        assert not checkbox.isChecked()

    def test_select_all_deselect_all(self, pos_dialog):
        """Test _select_all and _deselect_all methods."""
        pos_dialog._deselect_all()
        for checkbox in pos_dialog.checkboxes.values():
            assert not checkbox.isChecked()
        assert pos_dialog.filter_selection == set()

        pos_dialog._select_all()
        for checkbox in pos_dialog.checkboxes.values():
            assert checkbox.isChecked()
        expected_codes = {k for k in AnnotationLookupsMixin.PART_OF_SPEECH_MAP if k not in [None, ""]}
        assert pos_dialog.filter_selection == expected_codes

    def test_get_set_selected_items(self, pos_dialog):
        """Test get_selected_items and set_selected_items."""
        initial_selection = pos_dialog.get_selected_items()
        assert "N" in initial_selection
        
        new_selection = {"V", "A"}
        pos_dialog.set_selected_items(new_selection)
        assert pos_dialog.get_selected_items() == new_selection
        
        assert pos_dialog.checkboxes["V"].isChecked()
        assert not pos_dialog.checkboxes["N"].isChecked()

    def test_case_dialog_initialization(self, case_dialog):
        """Test that Case dialog is initialized with correct items."""
        expected_codes = {k for k in AnnotationLookupsMixin.CASE_MAP if k not in [None, ""]}
        assert set(case_dialog.checkboxes.keys()) == expected_codes

    def test_number_dialog_initialization(self, number_dialog):
        """Test that Number dialog is initialized with correct items."""
        expected_codes = {k for k in AnnotationLookupsMixin.PRONOUN_NUMBER_MAP if k not in [None, ""]}
        assert set(number_dialog.checkboxes.keys()) == expected_codes

    def test_dialog_closed_signal(self, pos_dialog, qtbot):
        """Test that dialog_closed signal is emitted."""
        with qtbot.waitSignal(pos_dialog.dialog_closed):
            pos_dialog.close()

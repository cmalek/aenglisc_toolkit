"""Unit tests for AnnotationPresetManagementDialog."""

import pytest

from oeapp.models.annotation_preset import AnnotationPreset


class TestAnnotationPresetManagementDialog:
    """Test cases for AnnotationPresetManagementDialog."""

    def test_dialog_initialization_default_state(self, qapp, db_session):
        """Test dialog initialization with default state."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog()
        assert dialog is not None
        assert hasattr(dialog, "tab_widget")
        assert not dialog.save_mode

    def test_dialog_initialization_save_mode(self, qapp, db_session):
        """Test dialog initialization with save_mode=True."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )
        assert dialog.save_mode
        assert dialog.initial_pos == "N"
        assert hasattr(dialog, "name_edit")

    def test_dialog_initialization_with_initial_pos(self, qapp, db_session):
        """Test dialog initialization with initial_pos parameter."""
        import oeapp.ui.dialogs.annotation_preset_management as apm_module
        AnnotationPresetManagementDialog = apm_module.AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            initial_pos="V"
        )
        assert dialog.initial_pos == "V"

    def test_dialog_initialization_with_initial_field_values(self, qapp, db_session):
        """Test dialog initialization with initial_field_values parameter."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        field_values = {"gender": "m", "number": "s"}
        dialog = AnnotationPresetManagementDialog(
            save_mode=True,
            initial_pos="N",
            initial_field_values=field_values,
        )
        assert dialog.initial_field_values == field_values

    def test_save_mode_hides_tabs(self, qapp, db_session):
        """Test save mode hides tabs and shows only form."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )
        # In save mode, tab_widget should not exist
        assert not hasattr(dialog, "tab_widget") or dialog.tab_widget is None

    def test_load_presets_for_pos_loads_into_list(self, qapp, db_session):
        """Test _load_presets_for_pos() loads presets into list widget."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        # Create test presets
        AnnotationPreset.create(name="Preset 1", pos="N")
        AnnotationPreset.create(name="Preset 2", pos="N")

        dialog = AnnotationPresetManagementDialog()
        dialog._load_presets_for_pos("N")

        preset_list = dialog._find_preset_list("N")
        assert preset_list is not None
        assert preset_list.count() == 2

    def test_validate_preset_name_required(self, qapp, db_session):
        """Test form validation (name required)."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )
        dialog.name_edit.setText("")  # Empty name

        is_valid, error_msg = dialog._validate_preset()
        assert not is_valid
        assert "required" in error_msg.lower()

    def test_validate_preset_checks_duplicates(self, qapp, db_session):
        """Test form validation checks for duplicate names."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        # Create existing preset
        AnnotationPreset.create(name="Existing", pos="N")

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )
        dialog.name_edit.setText("Existing")  # Duplicate name

        is_valid, error_msg = dialog._validate_preset()
        assert not is_valid
        assert "already exists" in error_msg.lower()

    def test_clear_option_in_combo_boxes(self, qapp, db_session):
        """Test that empty is first and 'Clear' is second in combo boxes."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )

        # Check that gender_combo has empty as first item and "Clear" as second
        assert hasattr(dialog, "gender_combo")
        assert dialog.gender_combo.count() > 1
        assert dialog.gender_combo.itemText(0) == ""  # Empty first
        assert dialog.gender_combo.itemText(1) == "Clear"  # Clear second

    def test_extract_field_values_with_clear_selected(self, qapp, db_session):
        """Test that selecting empty extracts as None and 'Clear' extracts as CLEAR_SENTINEL."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog
        from oeapp.ui.dialogs.annotation_preset_management import CLEAR_SENTINEL

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )

        # Set combo to empty (index 0)
        dialog.gender_combo.setCurrentIndex(0)
        # Set combo to "Clear" (index 1)
        dialog.number_combo.setCurrentIndex(1)

        # Set case to a real value (index 2, accounting for empty at 0 and Clear at 1)
        if dialog.case_combo.count() > 2:
            dialog.case_combo.setCurrentIndex(2)

        field_values = dialog._extract_field_values()

        # Empty (index 0) should extract as None (don't change)
        assert field_values.get("gender") is None
        # "Clear" (index 1) should extract as CLEAR_SENTINEL (explicitly clear field)
        assert field_values.get("number") == CLEAR_SENTINEL
        # Index 2+ should extract as actual value (with offset of 1)
        if dialog.case_combo.count() > 2:
            # Case at index 2 should map to REVERSE_MAP[1] (2-1=1)
            assert field_values.get("case") is not None

    def test_set_combo_value_sets_empty_for_none(self, qapp, db_session):
        """Test that setting None value sets combo to empty (index 0), not 'Clear' (index 1).

        When loading a preset with None, it should show as empty (index 0), not "Clear" (index 1).
        "Clear" is only used when explicitly clearing a field when applying a preset.
        """
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )

        # Set combo to a non-zero value first
        if dialog.gender_combo.count() > 2:
            dialog.gender_combo.setCurrentIndex(2)
            # Now set to None - should go to index 0 (empty), not index 1 ("Clear")
            dialog._set_combo_value(dialog.gender_combo, None, dialog.GENDER_REVERSE_MAP)
            assert dialog.gender_combo.currentIndex() == 0
            assert dialog.gender_combo.currentText() == ""  # Empty string, not "Clear"

    def test_save_preset_with_clear_values(self, qapp, db_session):
        """Test saving a preset with 'Clear' selected for some fields."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )

        dialog.name_edit.setText("Test Clear Preset")
        # Set gender to empty (index 0)
        dialog.gender_combo.setCurrentIndex(0)
        # Set number to a real value (index 2, accounting for empty at 0 and Clear at 1)
        if dialog.number_combo.count() > 2:
            dialog.number_combo.setCurrentIndex(2)

        # Save the preset
        dialog._save_preset()
        db_session.commit()

        # Verify preset was created
        from oeapp.models.annotation_preset import AnnotationPreset
        presets = AnnotationPreset.get_all_by_pos("N")
        preset = next((p for p in presets if p.name == "Test Clear Preset"), None)
        assert preset is not None
        # Gender should be None (from "Clear")
        assert preset.gender is None
        # Number should have a value (if we set it)
        if dialog.number_combo.count() > 2:
            assert preset.number is not None

    def test_set_combo_value_sets_actual_values_correctly(self, qapp, db_session):
        """Test that setting actual values (not None) sets combo to correct index."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            save_mode=True, initial_pos="N"
        )

        # Test setting gender to "m" (masculine)
        # REVERSE_MAP[1] = "m", so it should be at combo index 1 + 1 = 2
        dialog._set_combo_value(dialog.gender_combo, "m", dialog.GENDER_REVERSE_MAP)
        assert dialog.gender_combo.currentIndex() == 2
        assert "Masculine" in dialog.gender_combo.currentText()

        # Test setting number to "s" (singular)
        # REVERSE_MAP[1] = "s", so it should be at combo index 1 + 1 = 2
        dialog._set_combo_value(dialog.number_combo, "s", dialog.NUMBER_REVERSE_MAP)
        assert dialog.number_combo.currentIndex() == 2
        assert "Singular" in dialog.number_combo.currentText()

        # Test setting case to "d" (dative)
        # REVERSE_MAP[4] = "d" (after n, a, g, d), so it should be at combo index 4 + 1 = 5
        dialog._set_combo_value(dialog.case_combo, "d", dialog.CASE_REVERSE_MAP)
        assert dialog.case_combo.currentIndex() == 5
        assert "Dative" in dialog.case_combo.currentText()

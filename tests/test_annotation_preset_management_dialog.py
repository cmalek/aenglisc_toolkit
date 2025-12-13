"""Unit tests for AnnotationPresetManagementDialog."""

import sys
import pytest
from unittest.mock import Mock

# Ensure PySide6 is not mocked before importing
# This handles the case where test_annotation_modal.py runs first and mocks PySide6
_original_pyside6 = sys.modules.get('PySide6')
if isinstance(_original_pyside6, Mock):
    # Clear mocked PySide6 modules so we can import the real ones
    keys_to_remove = [k for k in list(sys.modules.keys()) if k.startswith('PySide6')]
    for key in keys_to_remove:
        del sys.modules[key]

# Now import PySide6 - it will be the real one
from PySide6.QtWidgets import QApplication

from oeapp.models.annotation_preset import AnnotationPreset


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for testing PySide6 widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def mock_main_window():
    """Create a mock main window with session."""
    import tempfile
    import os
    from pathlib import Path
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from oeapp.db import Base

    temp_db = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.db')
    temp_db.close()
    db_path = Path(temp_db.name)

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    main_window = Mock()
    main_window.session = session

    yield main_window

    session.close()
    engine.dispose()
    os.unlink(temp_db.name)


class TestAnnotationPresetManagementDialog:
    """Test cases for AnnotationPresetManagementDialog."""

    def test_dialog_initialization_default_state(self, qapp, mock_main_window):
        """Test dialog initialization with default state."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(mock_main_window)
        assert dialog is not None
        assert hasattr(dialog, "tab_widget")
        assert not dialog.save_mode

    def test_dialog_initialization_save_mode(self, qapp, mock_main_window):
        """Test dialog initialization with save_mode=True."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
        )
        assert dialog.save_mode
        assert dialog.initial_pos == "N"
        assert hasattr(dialog, "name_edit")

    def test_dialog_initialization_with_initial_pos(self, qapp, mock_main_window):
        """Test dialog initialization with initial_pos parameter."""
        import oeapp.ui.dialogs.annotation_preset_management as apm_module
        AnnotationPresetManagementDialog = apm_module.AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, initial_pos="V"
        )
        assert dialog.initial_pos == "V"

    def test_dialog_initialization_with_initial_field_values(self, qapp, mock_main_window):
        """Test dialog initialization with initial_field_values parameter."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        field_values = {"gender": "m", "number": "s"}
        dialog = AnnotationPresetManagementDialog(
            mock_main_window,
            save_mode=True,
            initial_pos="N",
            initial_field_values=field_values,
        )
        assert dialog.initial_field_values == field_values

    def test_save_mode_hides_tabs(self, qapp, mock_main_window):
        """Test save mode hides tabs and shows only form."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
        )
        # In save mode, tab_widget should not exist
        assert not hasattr(dialog, "tab_widget") or dialog.tab_widget is None

    def test_load_presets_for_pos_loads_into_list(self, qapp, mock_main_window):
        """Test _load_presets_for_pos() loads presets into list widget."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        # Create test presets
        AnnotationPreset.create(mock_main_window.session, name="Preset 1", pos="N")
        AnnotationPreset.create(mock_main_window.session, name="Preset 2", pos="N")
        mock_main_window.session.commit()

        dialog = AnnotationPresetManagementDialog(mock_main_window)
        dialog._load_presets_for_pos("N")

        preset_list = dialog._find_preset_list("N")
        assert preset_list is not None
        assert preset_list.count() == 2

    def test_validate_preset_name_required(self, qapp, mock_main_window):
        """Test form validation (name required)."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
        )
        dialog.name_edit.setText("")  # Empty name

        is_valid, error_msg = dialog._validate_preset()
        assert not is_valid
        assert "required" in error_msg.lower()

    def test_validate_preset_checks_duplicates(self, qapp, mock_main_window):
        """Test form validation checks for duplicate names."""
        from pathlib import Path
        file_path = Path(__file__).parent.parent / "oeapp" / "ui" / "dialogs" / "annotation_preset_management.py"
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        # Create existing preset
        AnnotationPreset.create(mock_main_window.session, name="Existing", pos="N")
        mock_main_window.session.commit()

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
        )
        dialog.name_edit.setText("Existing")  # Duplicate name

        is_valid, error_msg = dialog._validate_preset()
        assert not is_valid
        assert "already exists" in error_msg.lower()

    def test_clear_option_in_combo_boxes(self, qapp, mock_main_window):
        """Test that empty is first and 'Clear' is second in combo boxes."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
        )

        # Check that gender_combo has empty as first item and "Clear" as second
        assert hasattr(dialog, "gender_combo")
        assert dialog.gender_combo.count() > 1
        assert dialog.gender_combo.itemText(0) == ""  # Empty first
        assert dialog.gender_combo.itemText(1) == "Clear"  # Clear second

    def test_extract_field_values_with_clear_selected(self, qapp, mock_main_window):
        """Test that selecting empty extracts as None and 'Clear' extracts as CLEAR_SENTINEL."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog
        from oeapp.ui.dialogs.annotation_preset_management import CLEAR_SENTINEL

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
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

    def test_set_combo_value_sets_empty_for_none(self, qapp, mock_main_window):
        """Test that setting None value sets combo to empty (index 0), not 'Clear' (index 1).

        When loading a preset with None, it should show as empty (index 0), not "Clear" (index 1).
        "Clear" is only used when explicitly clearing a field when applying a preset.
        """
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
        )

        # Set combo to a non-zero value first
        if dialog.gender_combo.count() > 2:
            dialog.gender_combo.setCurrentIndex(2)
            # Now set to None - should go to index 0 (empty), not index 1 ("Clear")
            dialog._set_combo_value(dialog.gender_combo, None, dialog.GENDER_REVERSE_MAP)
            assert dialog.gender_combo.currentIndex() == 0
            assert dialog.gender_combo.currentText() == ""  # Empty string, not "Clear"

    def test_save_preset_with_clear_values(self, qapp, mock_main_window):
        """Test saving a preset with 'Clear' selected for some fields."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
        )

        dialog.name_edit.setText("Test Clear Preset")
        # Set gender to empty (index 0)
        dialog.gender_combo.setCurrentIndex(0)
        # Set number to a real value (index 2, accounting for empty at 0 and Clear at 1)
        if dialog.number_combo.count() > 2:
            dialog.number_combo.setCurrentIndex(2)

        # Save the preset
        dialog._save_preset()
        mock_main_window.session.commit()

        # Verify preset was created
        from oeapp.models.annotation_preset import AnnotationPreset
        presets = AnnotationPreset.get_all_by_pos(mock_main_window.session, "N")
        preset = next((p for p in presets if p.name == "Test Clear Preset"), None)
        assert preset is not None
        # Gender should be None (from "Clear")
        assert preset.gender is None
        # Number should have a value (if we set it)
        if dialog.number_combo.count() > 2:
            assert preset.number is not None

    def test_set_combo_value_sets_actual_values_correctly(self, qapp, mock_main_window):
        """Test that setting actual values (not None) sets combo to correct index."""
        from oeapp.ui.dialogs import AnnotationPresetManagementDialog

        dialog = AnnotationPresetManagementDialog(
            mock_main_window, save_mode=True, initial_pos="N"
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

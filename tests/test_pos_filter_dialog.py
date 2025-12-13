"""Unit tests for POSFilterDialog."""

import pytest

from oeapp.ui.dialogs.pos_filter import POSFilterDialog


class TestPOSFilterDialog:
    """Test cases for POSFilterDialog."""

    def test_pos_filter_dialog_initializes(self, qapp):
        """Test POSFilterDialog initializes correctly."""
        dialog = POSFilterDialog(parent=None)

        assert dialog.windowTitle() == "Select Parts of Speech to Highlight"
        assert len(dialog.pos_checkboxes) == 9  # N, V, A, R, D, B, C, E, I
        assert dialog._selected_pos == {"N", "V", "A", "R", "D", "B", "C", "E", "I"}

    def test_pos_filter_dialog_has_all_pos_selected_by_default(self, qapp):
        """Test POSFilterDialog has all POS tags selected by default."""
        dialog = POSFilterDialog(parent=None)

        for pos_code in ["N", "V", "A", "R", "D", "B", "C", "E", "I"]:
            assert pos_code in dialog.pos_checkboxes
            assert dialog.pos_checkboxes[pos_code].isChecked()

    def test_pos_filter_dialog_select_all(self, qapp):
        """Test POSFilterDialog select all functionality."""
        dialog = POSFilterDialog(parent=None)

        # Deselect all first
        dialog._deselect_all()
        assert dialog._selected_pos == set()

        # Select all
        dialog._select_all()
        assert dialog._selected_pos == {"N", "V", "A", "R", "D", "B", "C", "E", "I"}
        for checkbox in dialog.pos_checkboxes.values():
            assert checkbox.isChecked()

    def test_pos_filter_dialog_deselect_all(self, qapp):
        """Test POSFilterDialog deselect all functionality."""
        dialog = POSFilterDialog(parent=None)

        # Should start with all selected
        assert dialog._selected_pos == {"N", "V", "A", "R", "D", "B", "C", "E", "I"}

        # Deselect all
        dialog._deselect_all()
        assert dialog._selected_pos == set()
        for checkbox in dialog.pos_checkboxes.values():
            assert not checkbox.isChecked()

    def test_pos_filter_dialog_emits_pos_changed_signal(self, qapp):
        """Test POSFilterDialog emits pos_changed signal."""
        dialog = POSFilterDialog(parent=None)

        # Connect signal
        received_pos = None
        def on_pos_changed(pos):
            nonlocal received_pos
            received_pos = pos
        dialog.pos_changed.connect(on_pos_changed)

        # Toggle a checkbox - this will trigger stateChanged which calls _on_checkbox_changed
        checkbox = dialog.pos_checkboxes["N"]
        checkbox.setChecked(False)

        assert "N" not in received_pos
        assert received_pos is not None

    def test_pos_filter_dialog_handles_individual_pos_toggle(self, qapp):
        """Test POSFilterDialog handles individual POS toggling."""
        dialog = POSFilterDialog(parent=None)

        # Start with all selected
        assert "N" in dialog._selected_pos

        # Toggle off
        dialog.pos_checkboxes["N"].setChecked(False)
        # The checkbox stateChanged signal will call _on_checkbox_changed
        assert "N" not in dialog._selected_pos

        # Toggle back on
        dialog.pos_checkboxes["N"].setChecked(True)
        assert "N" in dialog._selected_pos


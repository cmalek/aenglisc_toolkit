"""Unit tests for CaseFilterDialog."""

from oeapp.ui.dialogs.case_filter import CaseFilterDialog


class TestCaseFilterDialog:
    """Test cases for CaseFilterDialog."""

    def test_case_filter_dialog_initializes(self, qapp):
        """Test CaseFilterDialog initializes correctly."""
        dialog = CaseFilterDialog(parent=None)

        assert dialog.windowTitle() == "Select Cases to Highlight"
        assert len(dialog.case_checkboxes) == 5  # n, a, g, d, i
        assert dialog._selected_cases == {"n", "a", "g", "d", "i"}

    def test_case_filter_dialog_has_all_cases_selected_by_default(self, qapp):
        """Test CaseFilterDialog has all cases selected by default."""
        dialog = CaseFilterDialog(parent=None)

        for case_code in ["n", "a", "g", "d", "i"]:
            assert case_code in dialog.case_checkboxes
            assert dialog.case_checkboxes[case_code].isChecked()

    def test_case_filter_dialog_select_all(self, qapp):
        """Test CaseFilterDialog select all functionality."""
        dialog = CaseFilterDialog(parent=None)

        # Deselect all first
        dialog._deselect_all()
        assert dialog._selected_cases == set()

        # Select all
        dialog._select_all()
        assert dialog._selected_cases == {"n", "a", "g", "d", "i"}
        for checkbox in dialog.case_checkboxes.values():
            assert checkbox.isChecked()

    def test_case_filter_dialog_deselect_all(self, qapp):
        """Test CaseFilterDialog deselect all functionality."""
        dialog = CaseFilterDialog(parent=None)

        # Should start with all selected
        assert dialog._selected_cases == {"n", "a", "g", "d", "i"}

        # Deselect all
        dialog._deselect_all()
        assert dialog._selected_cases == set()
        for checkbox in dialog.case_checkboxes.values():
            assert not checkbox.isChecked()

    def test_case_filter_dialog_emits_cases_changed_signal(self, qapp):
        """Test CaseFilterDialog emits cases_changed signal."""
        dialog = CaseFilterDialog(parent=None)

        # Connect signal
        received_cases = None
        def on_cases_changed(cases):
            nonlocal received_cases
            received_cases = cases
        dialog.cases_changed.connect(on_cases_changed)

        # Toggle a checkbox - this will trigger stateChanged which calls _on_checkbox_changed
        checkbox = dialog.case_checkboxes["n"]
        checkbox.setChecked(False)

        assert "n" not in received_cases
        assert received_cases is not None

    def test_case_filter_dialog_handles_individual_case_toggle(self, qapp):
        """Test CaseFilterDialog handles individual case toggling."""
        dialog = CaseFilterDialog(parent=None)

        # Start with all selected
        assert "n" in dialog._selected_cases

        # Toggle off
        dialog.case_checkboxes["n"].setChecked(False)
        # The checkbox stateChanged signal will call _on_checkbox_changed
        assert "n" not in dialog._selected_cases

        # Toggle back on
        dialog.case_checkboxes["n"].setChecked(True)
        assert "n" in dialog._selected_cases


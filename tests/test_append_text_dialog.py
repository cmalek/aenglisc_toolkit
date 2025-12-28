"""Unit tests for AppendTextDialog."""

from oeapp.ui.dialogs.append_text import AppendTextDialog


class TestAppendTextDialog:
    """Test cases for AppendTextDialog."""

    def test_append_text_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test AppendTextDialog initializes correctly."""
        dialog = AppendTextDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_append_text_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test AppendTextDialog builds correctly."""
        dialog = AppendTextDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Append OE Text"


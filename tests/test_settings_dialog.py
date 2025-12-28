"""Unit tests for SettingsDialog."""

from oeapp.ui.dialogs.settings import SettingsDialog

from tests.conftest import MockMainWindow

class TestSettingsDialog:
    """Test cases for SettingsDialog."""

    def test_settings_dialog_initializes(self, db_session, mock_main_window, qapp):
        """Test SettingsDialog initializes correctly."""

        dialog = SettingsDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_settings_dialog_builds(self, db_session, mock_main_window, qapp):
        """Test SettingsDialog builds correctly."""

        dialog = SettingsDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Preferences"  # Actual title is "Preferences"


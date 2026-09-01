"""Unit tests for SettingsDialog."""

from pathlib import Path
from unittest.mock import patch

import oeapp.ui.dialogs.settings as settings_module
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


class TestSettingsDialogThemeSwitching:
    """Test cases for live theme switching."""

    def test_theme_change_applies_theme_immediately(
        self, db_session, mock_main_window, qapp
    ):
        """Changing the theme applies it live, without requiring a restart."""
        dialog = SettingsDialog(mock_main_window)
        dialog.build()
        dialog.settings.setValue("theme/name", "dark")
        dialog.theme_combo.setCurrentText("light")

        with patch("oeapp.ui.dialogs.settings.apply_theme") as mock_apply:
            dialog._on_theme_changed()

        mock_apply.assert_called_once_with("light")

    def test_theme_change_shows_no_restart_dialog(
        self, db_session, mock_main_window, qapp
    ):
        """The obsolete 'quit and restart' message box is not shown."""
        dialog = SettingsDialog(mock_main_window)
        dialog.build()
        dialog.theme_combo.setCurrentText("light")

        source = Path(settings_module.__file__).read_text(encoding="utf-8")
        assert "QMessageBox" not in source

        with patch("oeapp.ui.dialogs.settings.apply_theme"):
            dialog._on_theme_changed()

    def test_get_theme_returns_qt_themes_name(
        self, db_session, mock_main_window, qapp
    ):
        """get_theme resolves the stored value to a qt_themes theme name."""
        dialog = SettingsDialog(mock_main_window)
        dialog.settings.setValue("theme/name", "light")

        assert dialog.get_theme() == "modern_light"


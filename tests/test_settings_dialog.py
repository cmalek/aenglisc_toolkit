"""Unit tests for SettingsDialog."""

import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QWidget

from oeapp.ui.dialogs.settings import SettingsDialog


class MockMainWindow(QWidget):
    """Mock main window that inherits from QWidget."""

    def __init__(self):
        super().__init__()
        self.show_information = MagicMock()


class TestSettingsDialog:
    """Test cases for SettingsDialog."""

    def test_settings_dialog_initializes(self, qapp):
        """Test SettingsDialog initializes correctly."""
        mock_main_window = MockMainWindow()

        dialog = SettingsDialog(mock_main_window)

        assert dialog.main_window == mock_main_window

    def test_settings_dialog_builds(self, qapp):
        """Test SettingsDialog builds correctly."""
        mock_main_window = MockMainWindow()

        dialog = SettingsDialog(mock_main_window)
        dialog.build()

        assert dialog.dialog is not None
        assert dialog.dialog.windowTitle() == "Preferences"  # Actual title is "Preferences"


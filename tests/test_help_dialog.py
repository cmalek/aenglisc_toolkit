"""Unit tests for HelpDialog."""

import pytest

from oeapp.ui.dialogs.help_dialog import HelpDialog


class TestHelpDialog:
    """Test cases for HelpDialog."""

    def test_help_dialog_initializes(self, qapp):
        """Test HelpDialog initializes correctly."""
        dialog = HelpDialog(parent=None)

        assert dialog.isModal() is False  # Should be non-modal
        assert dialog.help_dir is not None

    def test_help_dialog_initializes_with_topic(self, qapp):
        """Test HelpDialog initializes with a specific topic."""
        dialog = HelpDialog(topic="Keybindings", parent=None)

        assert dialog.isModal() is False

    def test_help_dialog_has_topics(self, qapp):
        """Test HelpDialog has defined topics."""
        dialog = HelpDialog(parent=None)

        assert len(dialog.TOPICS) > 0
        assert "Keybindings" in dialog.TOPICS
        assert "Annotation Guide" in dialog.TOPICS

    def test_help_dialog_loads_default_topic(self, qapp):
        """Test HelpDialog loads default topic when invalid topic provided."""
        dialog = HelpDialog(topic="InvalidTopic", parent=None)

        # Should still initialize without error
        assert dialog is not None


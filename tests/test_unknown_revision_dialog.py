"""UnknownRevisionDialog and its message."""

from oeapp.exc import UnknownDatabaseRevision
from oeapp.ui.dialogs.unknown_revision import (
    FAQ_URL,
    UnknownRevisionDialog,
    describe_unknown_revision,
)


def test_message_names_the_version_when_it_is_known():
    text = describe_unknown_revision("zzz", "1.9.0")
    assert "1.9.0" in text
    assert "zzz" in text
    assert "Can't determine" not in text


def test_message_says_it_cannot_determine_the_version_otherwise():
    text = describe_unknown_revision("zzz", None)
    assert "Can't determine app version to use with db revision zzz" in text
    assert FAQ_URL in text


def test_dialog_builds_with_the_message(mock_main_window, qapp):
    error = UnknownDatabaseRevision("zzz", "1.9.0")
    dialog = UnknownRevisionDialog(mock_main_window, error)

    dialog.build()

    assert "version" in dialog.dialog.windowTitle().lower()
    assert dialog.message_label.text() == describe_unknown_revision("zzz", "1.9.0")

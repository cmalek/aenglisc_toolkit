"""Unit tests for QtHelp-based Help Center dialog."""

from PySide6.QtCore import QUrl
from PySide6.QtGui import QTextDocument
from PySide6.QtHelp import QHelpLink

from oeapp.ui.dialogs.help_center_dialog import HelpCenterDialog


class TestHelpCenterDialog:
    """Test cases for HelpCenterDialog."""

    def test_help_center_dialog_initializes(self, qapp, tmp_path, monkeypatch):
        """Dialog should initialize in non-modal mode and load Start Here."""
        monkeypatch.setenv("OE_ANNOTATOR_DATA_PATH", str(tmp_path))
        dialog = HelpCenterDialog(parent=None)

        assert dialog.isModal() is False
        assert dialog.browser.source().scheme() == "qthelp"
        assert dialog.browser.source().toString().endswith("/start-here.html")

    def test_help_center_dialog_initializes_with_topic(
        self, qapp, tmp_path, monkeypatch
    ):
        """Dialog should open a requested topic URL when provided."""
        monkeypatch.setenv("OE_ANNOTATOR_DATA_PATH", str(tmp_path))
        dialog = HelpCenterDialog(topic="Keybindings", parent=None)

        assert dialog.browser.source().scheme() == "qthelp"
        assert dialog.browser.source().toString().endswith("/keybindings.html")

    def test_help_center_dialog_invalid_topic_falls_back_to_home(
        self, qapp, tmp_path, monkeypatch
    ):
        """Unknown topics should resolve to the help home page."""
        monkeypatch.setenv("OE_ANNOTATOR_DATA_PATH", str(tmp_path))
        dialog = HelpCenterDialog(topic="NotATopic", parent=None)

        assert dialog.browser.source().toString().endswith("/start-here.html")

    def test_help_center_dialog_renders_screenshot_surface(
        self, qapp, tmp_path, monkeypatch
    ):
        """Dialog should render a non-null pixmap for screenshot-based regression checks."""
        monkeypatch.setenv("OE_ANNOTATOR_DATA_PATH", str(tmp_path))
        dialog = HelpCenterDialog(topic="Keybindings", parent=None)
        dialog.show()
        qapp.processEvents()

        pixmap = dialog.grab()
        assert not pixmap.isNull()

    def test_help_center_dialog_document_activation_uses_qhelp_link_url(
        self, qapp, tmp_path, monkeypatch
    ):
        """Index/document activation should open QHelpLink URL, not label text."""
        monkeypatch.setenv("OE_ANNOTATOR_DATA_PATH", str(tmp_path))
        dialog = HelpCenterDialog(parent=None)
        captured: list[QUrl] = []
        monkeypatch.setattr(dialog, "_open_url", lambda url: captured.append(url))

        link = QHelpLink()
        link.title = "Start Here"
        link.url = QUrl("qthelp://org.placodermi.aenglisc_toolkit/doc/start-here.html")

        dialog._on_link_signal(link, "Start Here")

        assert captured
        assert captured[0].toString().endswith("/start-here.html")

    def test_help_center_dialog_ignores_non_url_string_payload(
        self, qapp, tmp_path, monkeypatch
    ):
        """Plain label strings should not be delegated to OS URL opening."""
        monkeypatch.setenv("OE_ANNOTATOR_DATA_PATH", str(tmp_path))
        dialog = HelpCenterDialog(parent=None)
        opened_urls: list[QUrl] = []
        monkeypatch.setattr("oeapp.ui.dialogs.help_center_dialog.QDesktopServices.openUrl", opened_urls.append)

        dialog._on_link_signal("totally-nonexistent-keyword")
        qapp.processEvents()

        assert opened_urls == []

    def test_help_center_dialog_injects_theme_override_css(
        self, qapp, tmp_path, monkeypatch
    ):
        """QtHelp HTML resources should receive runtime theme CSS overrides."""
        monkeypatch.setenv("OE_ANNOTATOR_DATA_PATH", str(tmp_path))
        dialog = HelpCenterDialog(parent=None)
        start_here_url = dialog.help_engine.page_url("start-here.html")

        payload = dialog.browser.loadResource(
            int(QTextDocument.ResourceType.HtmlResource),
            start_here_url,
        )

        html = bytes(payload).decode("utf-8", errors="replace")
        assert "qt-help-theme-override" in html

"""QtHelp-based Help Center dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QByteArray, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPalette, QTextDocument
from PySide6.QtHelp import QHelpLink
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from oeapp.help.help_engine import HelpEngine

if TYPE_CHECKING:
    from PySide6.QtHelp import QHelpEngine


class HelpTextBrowser(QTextBrowser):
    """QTextBrowser that resolves `qthelp://` resources through QHelpEngine."""

    def __init__(self, help_engine: QHelpEngine, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._help_engine = help_engine
        self._theme_override_css = ""

    def set_theme_override_css(self, css: str) -> None:
        """Set CSS appended to every rendered QtHelp HTML page."""
        self._theme_override_css = css

    def loadResource(self, resource_type: int, name: QUrl) -> Any:  # type: ignore[override]  # noqa: N802
        """
        Load resources from QtHelp when browsing `qthelp://` URLs.

        Args:
            resource_type: Resource category requested by QTextBrowser.
            name: Resource URL.

        Returns:
            Resource payload as bytes/Qt value.

        """
        if name.scheme() == "qthelp":
            payload = self._help_engine.fileData(name)
            if (
                resource_type == int(QTextDocument.ResourceType.HtmlResource)
                and self._theme_override_css
            ):
                return self._inject_theme_override_css(payload)
            return payload
        return super().loadResource(resource_type, name)

    def _inject_theme_override_css(self, payload: Any) -> QByteArray:
        """Append runtime CSS override so help pages match active app theme."""
        raw = bytes(payload) if payload is not None else b""
        if not raw:
            return payload if isinstance(payload, QByteArray) else QByteArray()

        html = raw.decode("utf-8", errors="replace")
        style_block = (
            '<style id="qt-help-theme-override">\n'
            f"{self._theme_override_css}\n"
            "</style>\n"
        )
        if "</head>" in html:
            html = html.replace("</head>", f"{style_block}</head>", 1)
        elif "<body" in html:
            html = html.replace("<body", f"{style_block}<body", 1)
        else:
            html = f"{style_block}{html}"
        return QByteArray(html.encode("utf-8"))


class HelpCenterDialog(QDialog):
    """
    Main help center with Contents, Index, and Search panes.

    Keyword Args:
        topic: Optional topic to display initially
        parent: Parent widget

    """

    def __init__(self, topic: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setModal(False)
        self.help_engine = HelpEngine()
        self._build_ui()
        self._wire_signals()
        self.show_topic(topic)

    def _build_ui(self) -> None:
        """
        Construct dialog widgets/layout.

        - Sets the window title, minimum size, and initial size
        - Creates the root layout
        - Creates the header label
        - Creates the splitter
        - Creates the left panel
        - Creates the left layout
        - Creates the left tabs
        - Creates the contents widget
        - Creates the index widget
        - Creates the search widget
        - Creates the right panel
        - Creates the right layout
        - Creates the browser
        - Sets the sizes of the splitter

        """
        self.setWindowTitle("Ænglisc Toolkit - Help Center")
        self.setMinimumSize(950, 650)
        self.resize(1200, 800)

        root_layout = QVBoxLayout(self)

        header = QLabel("Help Center")
        header.setStyleSheet("font-size: 18px; font-weight: 600;")
        root_layout.addWidget(header)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root_layout.addWidget(splitter, 1)

        left_panel = QWidget(splitter)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.left_tabs = QTabWidget(left_panel)
        left_layout.addWidget(self.left_tabs, 1)

        self.contents_widget = self.help_engine.content_widget
        self.left_tabs.addTab(self.contents_widget, "Contents")

        index_tab = QWidget()
        index_layout = QVBoxLayout(index_tab)
        index_layout.setContentsMargins(6, 6, 6, 6)
        index_layout.setSpacing(6)
        self.index_filter = QLineEdit(index_tab)
        self.index_filter.setPlaceholderText("Filter index...")
        index_layout.addWidget(self.index_filter)
        self.index_widget = self.help_engine.index_widget
        index_layout.addWidget(self.index_widget, 1)
        self.left_tabs.addTab(index_tab, "Index")

        search_tab = QWidget()
        search_layout = QVBoxLayout(search_tab)
        search_layout.setContentsMargins(6, 6, 6, 6)
        search_layout.setSpacing(6)
        self.search_query_widget = self.help_engine.search_query_widget
        self.search_result_widget = self.help_engine.search_result_widget
        search_layout.addWidget(self.search_query_widget)
        search_layout.addWidget(self.search_result_widget, 1)
        self.left_tabs.addTab(search_tab, "Search")

        right_panel = QWidget(splitter)
        right_layout = QHBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.browser = HelpTextBrowser(self.help_engine.qt_engine, right_panel)
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        self.browser.set_theme_override_css(self._theme_override_css())
        right_layout.addWidget(self.browser)

        splitter.setSizes([320, 880])

    def _wire_signals(self) -> None:
        """
        Connect QtHelp and browser signals.

        - Connects the contents widget link activated signal to the
          :meth:`_on_link_signal` method
        - Connects the index widget link activated signal to the
          :meth:`_on_link_signal` method
        - Connects the index widget document activated signal to the
          :meth:`_on_link_signal` method
        - Connects the search result widget request show link signal to the
          :meth:`_on_link_signal` method
        - Connects the browser anchor clicked signal to the
          :meth:`_open_url` method
        - Connects the index filter text changed signal to the
          :meth:`index_widget.filterIndices` method
        - Connects the search query widget search signal to the
          :meth:`help_engine.start_search` method

        """
        self.contents_widget.linkActivated.connect(self._on_link_signal)
        self.index_widget.linkActivated.connect(self._on_link_signal)
        self.index_widget.linksActivated.connect(self._on_link_signal)
        self.index_widget.documentActivated.connect(self._on_link_signal)
        self.index_widget.documentsActivated.connect(self._on_link_signal)
        self.search_result_widget.requestShowLink.connect(self._on_link_signal)
        self.browser.anchorClicked.connect(self._open_url)
        self.index_filter.textChanged.connect(self.index_widget.filterIndices)
        self.search_query_widget.search.connect(self.help_engine.start_search)

    def show_topic(self, topic: str | None) -> None:
        """
        Navigate to a topic by title.

        Args:
            topic: Topic to navigate to

        """
        self._open_url(self.help_engine.topic_url(topic))

    def _on_link_signal(self, *args: object) -> None:
        """
        Normalize QtHelp link-related signals into a URL navigation request.

        QtHelp index/content/search widgets emit slightly different signal payload
        shapes (URL only, URL+label, or mapping of label->URL).

        Args:
            args: Arguments from the signal

        """
        for arg in args:
            resolved = self._resolve_link_payload(arg)
            if resolved is not None:
                self._open_url(resolved)
                return

    def _open_url(self, url: QUrl) -> None:
        """
        Open an internal help URL or delegate external links to the OS.

        Args:
            url: URL to open

        """
        if not url.isValid() or url.isEmpty():
            return

        if url.scheme() == "qthelp":
            self.browser.setSource(url)
            return
        if not url.scheme():
            return
        QDesktopServices.openUrl(url)

    def _resolve_link_payload(  # noqa: PLR0911, PLR0912
        self, payload: object
    ) -> QUrl | None:
        """Extract a help URL from QtHelp signal payload variants."""
        if isinstance(payload, QUrl):
            return payload if payload.isValid() and not payload.isEmpty() else None
        if isinstance(payload, QHelpLink):
            return self._resolve_link_payload(payload.url)
        if isinstance(payload, str):
            direct_url = QUrl(payload)
            if direct_url.scheme():
                return direct_url
            by_identifier = self.help_engine.qt_engine.documentsForIdentifier(payload)
            resolved = self._resolve_link_payload(by_identifier)
            if resolved is not None:
                return resolved
            by_keyword = self.help_engine.qt_engine.documentsForKeyword(payload)
            return self._resolve_link_payload(by_keyword)
        if isinstance(payload, dict):
            for value in payload.values():
                resolved = self._resolve_link_payload(value)
                if resolved is not None:
                    return resolved
            return None
        if isinstance(payload, (list, tuple, set)):
            for value in payload:
                resolved = self._resolve_link_payload(value)
                if resolved is not None:
                    return resolved
            return None

        values_method = getattr(payload, "values", None)
        if callable(values_method):
            try:
                values = values_method()
            except TypeError:
                values = ()
            for value in values:
                resolved = self._resolve_link_payload(value)
                if resolved is not None:
                    return resolved

        url_attr = getattr(payload, "url", None)
        if isinstance(url_attr, QUrl):
            return self._resolve_link_payload(url_attr)
        return None

    def _theme_override_css(self) -> str:
        """Build runtime CSS overrides from the active Qt palette."""
        palette = self.palette()
        base = palette.color(QPalette.ColorRole.Base).name()
        text = palette.color(QPalette.ColorRole.Text).name()
        link = palette.color(QPalette.ColorRole.Link).name()
        link_visited = palette.color(QPalette.ColorRole.LinkVisited).name()
        border = palette.color(QPalette.ColorRole.Mid).name()
        alt_base = palette.color(QPalette.ColorRole.AlternateBase).name()
        return (
            "html, body { "
            f"background-color: {base} !important; color: {text} !important; "
            "}\n"
            "body, p, li, td, th, span, div, blockquote, code, pre, "
            "h1, h2, h3, h4, h5, h6 { "
            f"color: {text} !important; "
            "}\n"
            f"h1 {{ border-bottom-color: {border} !important; }}\n"
            f"a, a * {{ color: {link} !important; }}\n"
            f"a:visited, a:visited * {{ color: {link_visited} !important; }}\n"
            f"table, th, td {{ border-color: {border} !important; }}\n"
            f"th {{ background: {alt_base} !important; }}\n"
            "code, pre { "
            f"background: {alt_base} !important; color: {text} !important; "
            "}\n"
        )

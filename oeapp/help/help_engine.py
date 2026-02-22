"""QtHelp engine wrapper used by the help center UI."""

from __future__ import annotations

from typing import Final

from PySide6.QtCore import QUrl
from PySide6.QtHelp import (
    QHelpContentWidget,
    QHelpEngine,
    QHelpIndexWidget,
    QHelpSearchQueryWidget,
    QHelpSearchResultWidget,
)

from oeapp.help.help_paths import ensure_runtime_help_assets
from oeapp.help.topics import DEFAULT_HTML_PAGE, TOPIC_TO_HTML

HELP_NAMESPACE: Final[str] = "org.placodermi.aenglisc_toolkit"
HELP_VIRTUAL_FOLDER: Final[str] = "doc"


class HelpEngineError(RuntimeError):
    """Raised when QtHelp cannot initialize or register documentation."""


class HelpEngine:
    """Application-specific wrapper around :class:`QHelpEngine`."""

    def __init__(self) -> None:
        self.paths = ensure_runtime_help_assets()
        self.qt_engine = QHelpEngine(str(self.paths.runtime_collection_file))
        self._setup()
        self.search_engine = self.qt_engine.searchEngine()

    def _setup(self) -> None:
        """Initialize packaged QtHelp collection."""
        if not self.qt_engine.setupData():
            msg = self.qt_engine.error() or "Unknown QtHelp setup error."
            details = f"Failed to initialize help collection: {msg}"
            raise HelpEngineError(details)

        registered = set(self.qt_engine.registeredDocumentations())
        if HELP_NAMESPACE in registered:
            return

        details = (
            f"Help collection is missing namespace '{HELP_NAMESPACE}'. "
            "Rebuild help artifacts with "
            "`source .venv/bin/activate && python scripts/build_help.py`."
        )
        raise HelpEngineError(details)

    def topic_url(self, topic: str | None) -> QUrl:
        """Return the `qthelp://` URL for a named topic (or default home page)."""
        page = TOPIC_TO_HTML.get(topic or "", DEFAULT_HTML_PAGE)
        return self.page_url(page)

    def page_url(self, page: str) -> QUrl:
        """Return the `qthelp://` URL for a relative page path."""
        return QUrl(f"qthelp://{HELP_NAMESPACE}/{HELP_VIRTUAL_FOLDER}/{page}")

    @property
    def content_widget(self) -> QHelpContentWidget:
        """Return the contents tree widget."""
        return self.qt_engine.contentWidget()

    @property
    def index_widget(self) -> QHelpIndexWidget:
        """Return the keyword index widget."""
        return self.qt_engine.indexWidget()

    @property
    def search_query_widget(self) -> QHelpSearchQueryWidget:
        """Return the search-query input widget."""
        return self.search_engine.queryWidget()

    @property
    def search_result_widget(self) -> QHelpSearchResultWidget:
        """Return the search results widget."""
        return self.search_engine.resultWidget()

    def start_search(self) -> None:
        """Execute a help search using the current query widget values."""
        self.search_engine.search(self.search_query_widget.query())

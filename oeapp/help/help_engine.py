"""QtHelp engine wrapper used by the help center UI."""

from __future__ import annotations

from typing import Final

from PySide6.QtCore import QUrl
from PySide6.QtHelp import (
    QHelpContentWidget,
    QHelpEngine,
    QHelpIndexWidget,
    QHelpSearchQuery,
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

    #: Whether QtHelp full-text indexing has completed for this runtime.
    _search_index_ready: bool
    #: Whether a full-text indexing run has been requested.
    _search_index_requested: bool
    #: Query captured while indexing, to execute once indexing finishes.
    _pending_search_query: list[QHelpSearchQuery] | None

    def __init__(self) -> None:
        """Initialize QtHelp and prime all searchable/indexable models."""
        self.paths = ensure_runtime_help_assets()
        self.qt_engine = QHelpEngine(str(self.paths.runtime_collection_file))
        self._setup()
        self.search_engine = self.qt_engine.searchEngine()
        self._search_index_ready = False
        self._search_index_requested = False
        self._pending_search_query = None
        self._prepare_indexes()

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

    def _prepare_indexes(self) -> None:
        """
        Build QtHelp content/index models and start full-text indexing.

        Returns:
            None

        """
        self.search_engine.indexingFinished.connect(self._on_search_indexing_finished)
        self.qt_engine.contentModel().createContentsForCurrentFilter()
        self.qt_engine.indexModel().createIndex("")
        self._request_search_index()

    def _request_search_index(self) -> None:
        """
        Trigger full-text indexing when it has not already been requested.

        Returns:
            None

        """
        if self._search_index_requested:
            return
        self._search_index_requested = True
        self.search_engine.reindexDocumentation()

    def _on_search_indexing_finished(self) -> None:
        """
        Mark search index ready and execute any queued query.

        Returns:
            None

        """
        self._search_index_ready = True
        self._search_index_requested = False
        if self._pending_search_query is None:
            return
        query = self._pending_search_query
        self._pending_search_query = None
        self.search_engine.search(query)

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

    @property
    def search_index_ready(self) -> bool:
        """
        Report whether full-text search indexing is complete.

        Returns:
            True if full-text indexing has completed, else False.

        """
        return self._search_index_ready

    def start_search(self) -> None:
        """
        Execute a help search using current query widget values.

        If indexing has not completed yet, the query is queued and executed
        when QtHelp emits ``indexingFinished``.

        Returns:
            None

        """
        query = self.search_query_widget.query()
        if self._search_index_ready:
            self.search_engine.search(query)
            return
        self._pending_search_query = query
        self._request_search_index()

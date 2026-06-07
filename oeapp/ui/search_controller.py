"""Search UI state, navigation, and highlight coordination."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt

from oeapp.models.project import Project
from oeapp.models.search_result import ProjectSearchMatches, SearchResult
from oeapp.ui.mixins import ThemeMixin
from oeapp.utils import normalize_old_english

if TYPE_CHECKING:
    from oeapp.state import AppContext
    from oeapp.ui.main_window import MainWindow
    from oeapp.ui.sentence_card import SentenceCard


class SearchController(ThemeMixin):
    """
    Manage project search UI state and navigation.

    Args:
        main_window: Main window hosting search widgets and sentence cards.
        app_context: Shared application context for project state.

    """

    def __init__(
        self, main_window: MainWindow, app_context: AppContext
    ) -> None:
        """
        Initialize search controller state.

        Args:
            main_window: Main window hosting search widgets.
            app_context: Shared application context.

        """
        #: Main window hosting search widgets and sentence cards.
        self.main_window = main_window
        #: Shared application context for project state.
        self.app_context = app_context

        #: Ordered search results across the entire project.
        self.search_results: list[SearchResult] = []
        #: Total number of matched occurrences across all results.
        self.search_total_matches: int = 0
        #: Current match index in search_results.
        self.current_match_index: int = -1
        #: Sentence-to-token map for OE normalized matches.
        self._search_token_map: dict[int, set[int]] = {}
        #: Starting location when search mode first becomes active.
        self._search_origin: tuple[int, int, int] | None = None

    @property
    def sentence_cards(self) -> list[SentenceCard]:
        """
        Get the current sentence cards from the main window.

        Returns:
            Sentence cards currently loaded in the workspace.

        """
        return self.main_window.sentence_cards

    def perform_search(self, pattern: str, scope: str) -> None:
        """
        Perform project-wide search and update visible highlights.

        Args:
            pattern: Search pattern.
            scope: Search scope ("OE Text", "ModE text", "Notes", "All").

        """
        if not pattern.strip():
            self._reset_search_matches()
            self._search_origin = None
            self._apply_visible_highlights("", scope, None, {})
            self._update_search_ui(0)
            return

        self._capture_search_origin()
        matches = self._project_search_matches(pattern, scope)
        self.search_results = matches.results
        self.search_total_matches = matches.total_match_count
        self._search_token_map = matches.token_map
        self.current_match_index = -1 if not matches.results else 0
        normalized_oe = self._normalized_oe_query(pattern, scope)
        self._apply_visible_highlights(
            pattern, scope, normalized_oe, matches.token_map
        )
        self._update_search_ui(matches.total_match_count)

    def next_match(self) -> None:
        """Navigate to the next matching search result."""
        if not self.search_results:
            return

        self.current_match_index = (self.current_match_index + 1) % len(
            self.search_results
        )
        self._focus_current_match()

    def prev_match(self) -> None:
        """Navigate to the previous matching search result."""
        if not self.search_results:
            return

        self.current_match_index = (self.current_match_index - 1) % len(
            self.search_results
        )
        self._focus_current_match()

    def focus_first_match(self) -> None:
        """Focus the first match in search results."""
        if self.search_results:
            self.current_match_index = 0
            self._focus_current_match()

    def clear_search(self, restore_origin_focus: bool = False) -> None:
        """
        Clear search state, highlights, and optionally restore origin focus.

        Keyword Args:
            restore_origin_focus: Whether to restore focus to search origin ModE field.

        """
        scope = self.main_window.search_scope_combo.currentText()
        self.main_window.search_input.blockSignals(True)  # noqa: FBT003
        self.main_window.search_input.clear()
        self.main_window.search_input.blockSignals(False)  # noqa: FBT003
        self._reset_search_matches()
        self._apply_visible_highlights("", scope, None, {})
        self._update_search_ui(0)
        self.main_window.search_input.setStyleSheet("")
        if restore_origin_focus:
            self._restore_origin_focus()
        else:
            self._search_origin = None

    def _project_search_matches(
        self, pattern: str, scope: str
    ) -> ProjectSearchMatches:
        """
        Load current project matches via fat-ORM search helpers.

        Args:
            pattern: Raw search pattern.
            scope: Search scope.

        Returns:
            Ordered project matches and highlight metadata.

        """
        project_id = self.app_context.current_project_id
        if project_id is None:
            return ProjectSearchMatches()
        project = Project.get(project_id)
        if project is None:
            return ProjectSearchMatches()
        return project.search_matches(pattern, scope)

    def _update_search_ui(self, total_matches: int) -> None:
        """
        Update search UI elements based on search results.

        Args:
            total_matches: Total number of matches.

        """
        current = self.current_match_index + 1 if self.current_match_index >= 0 else 0
        self.main_window.search_counter_label.setText(f"{current} / {total_matches}")

        if self.main_window.search_input.text():
            if total_matches == 0:
                self.main_window.search_input.setStyleSheet(
                    f"background-color: {self.reddish.name()};"
                )
            else:
                self.main_window.search_input.setStyleSheet("")
        else:
            self.main_window.search_input.setStyleSheet("")

    def _focus_current_match(self) -> None:
        """Focus the current search result and update the search counter."""
        if 0 <= self.current_match_index < len(self.search_results):
            result = self.search_results[self.current_match_index]
            self._focus_result(result)
            self._update_search_ui(self.search_total_matches)

    def _reset_search_matches(self) -> None:
        """Reset in-memory search results and counters."""
        self.search_results = []
        self.search_total_matches = 0
        self.current_match_index = -1
        self._search_token_map = {}

    def _capture_search_origin(self) -> None:
        """Capture the sentence location where search mode started."""
        if self._search_origin is not None:
            return
        card = self._focused_or_selected_card()
        if card is None:
            return
        sentence = card.sentence
        if not sentence.paragraph:
            return
        section = sentence.paragraph.section
        chapter = section.chapter
        self._search_origin = (chapter.id, section.id, sentence.id)

    def _focused_or_selected_card(self) -> SentenceCard | None:
        """
        Find the best sentence card candidate for focus restoration.

        Returns:
            Focused, selected, or first visible sentence card, if any.

        """
        for card in self.sentence_cards:
            if card.has_focus:
                return card
        project_ui = getattr(self.main_window, "project_ui", None)
        selected = (
            project_ui.get_selected_sentence_card()
            if project_ui is not None
            else None
        )
        if selected is not None:
            return selected
        return self.sentence_cards[0] if self.sentence_cards else None

    def _normalized_oe_query(self, pattern: str, scope: str) -> str | None:
        """
        Return normalized OE search query for OE-aware scopes.

        Args:
            pattern: Raw search pattern.
            scope: Search scope.

        Returns:
            Normalized OE query, or None when scope disables OE matching.

        """
        if scope not in {"OE Text", "Notes", "All"}:
            return None
        normalized = normalize_old_english(pattern)
        return normalized or None

    def _apply_visible_highlights(
        self,
        pattern: str,
        scope: str,
        normalized_oe: str | None,
        token_map: dict[int, set[int]],
    ) -> None:
        """
        Apply search highlights on currently loaded sentence cards.

        Args:
            pattern: Raw search pattern.
            scope: Search scope.
            normalized_oe: Normalized OE query, if enabled.
            token_map: Sentence id to matched token ids.

        """
        for card in self.sentence_cards:
            token_ids = token_map.get(card.sentence.id, set())
            card.highlight_search(pattern, scope, normalized_oe, token_ids)

    def _focus_result(self, result: SearchResult) -> None:
        """
        Navigate to and focus a specific search result.

        Args:
            result: Search result to focus.

        """
        card = self.main_window.project_ui.navigate_to_sentence(
            result.chapter_id, result.section_id, result.sentence_id
        )
        if card is None:
            return
        query = self.main_window.search_input.text()
        scope = self.main_window.search_scope_combo.currentText()
        normalized_oe = self._normalized_oe_query(query, scope)
        self._apply_visible_highlights(
            query, scope, normalized_oe, self._search_token_map
        )
        self.main_window.ensure_visible(card)
        if result.match_kind in {"oe_surface", "oe_root"}:
            card.focus_token_by_id(result.token_id)
            return
        if result.match_kind == "mode_text":
            card.focus_translation()
            return
        card.setFocus(Qt.FocusReason.OtherFocusReason)

    def _restore_origin_focus(self) -> None:
        """Restore focus to the ModE field where search mode began."""
        if self._search_origin is not None:
            chapter_id, section_id, sentence_id = self._search_origin
            card = self.main_window.project_ui.navigate_to_sentence(
                chapter_id, section_id, sentence_id
            )
            if card is not None:
                card.focus_translation()
                self._search_origin = None
                return
        if self.sentence_cards:
            self.sentence_cards[0].focus_translation()
        self._search_origin = None

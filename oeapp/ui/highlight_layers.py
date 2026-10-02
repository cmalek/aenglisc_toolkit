from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING

from PySide6.QtGui import QColor, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import QTextEdit

from oeapp.ui.mixins import AnnotationLookupsMixin

if TYPE_CHECKING:
    from oeapp.ui.oe_text_edit import OldEnglishTextEdit


class HighlightLayer(IntEnum):
    """
    The highlight layers of a sentence's Old English text, in paint order.

    A later layer paints on top of an earlier one.
    """

    #: The current highlighting mode (part of speech, case, number, idiom)
    MODE = 0
    #: The selected token, idiom or note span
    SPAN = 1
    #: The current search matches
    SEARCH = 2


@dataclass(frozen=True)
class HighlightStyle:
    """
    A semantic highlight style, resolved to a colour at compose time.

    Args:
        source: Name of an :class:`~oeapp.ui.mixins.AnnotationLookupsMixin`
            attribute: a colour map name when ``key`` is given, otherwise a
            single :class:`~PySide6.QtGui.QColor` constant.

    Keyword Args:
        key: Key into the colour map named by ``source``.

    """

    #: Name of the colour map or colour constant
    source: str
    #: Key into the colour map, or ``None`` for a single colour constant
    key: str | None = None


@dataclass(frozen=True)
class HighlightEntry:
    """
    One highlighted run of tokens in a layer.

    Args:
        first_token_id: Id of the first token in the run.
        last_token_id: Id of the last token in the run (same as the first for
            a single token).
        style: How to colour the run.

    """

    #: Id of the first token in the run
    first_token_id: int
    #: Id of the last token in the run
    last_token_id: int
    #: How to colour the run
    style: HighlightStyle


#: Style for search matches.
SEARCH_STYLE: HighlightStyle = HighlightStyle("SEARCH_COLOR")


class HighlightLayers:
    """
    Layered highlight state for one Old English text editor.

    Layers hold declarative, token-anchored entries. :meth:`compose` resolves
    them to document offsets through the editor's ``token_to_position`` map and
    to colours through the current palette, so entries survive a document
    rebuild and a live theme switch. The search layer holds either token
    entries or a text pattern, never both.

    Args:
        editor: The editor whose layers this object manages.

    """

    def __init__(self, editor: "OldEnglishTextEdit") -> None:
        """
        Initialize the instance.

        Args:
            editor: The editor whose layers this object manages.

        """
        #: The editor whose layers we manage
        self.editor = editor
        #: Palette and colour lookups
        self._lookups = AnnotationLookupsMixin()
        #: Token entries per layer
        self._entries: dict[HighlightLayer, list[HighlightEntry]] = {
            layer: [] for layer in HighlightLayer
        }
        #: Text pattern for the search layer, if the search is a text search
        self._search_pattern: str | None = None
        #: Cached ``(start, end)`` matches of the search pattern
        self._search_ranges: list[tuple[int, int]] | None = None

    def set_layer(self, layer: HighlightLayer, entries: list[HighlightEntry]) -> None:
        """
        Replace a layer's entries.

        Setting the search layer drops any search pattern.

        Args:
            layer: Layer to replace.
            entries: New entries for the layer.

        """
        self._entries[layer] = list(entries)
        if layer is HighlightLayer.SEARCH:
            self._search_pattern = None
            self._search_ranges = None

    def clear_layer(self, layer: HighlightLayer) -> None:
        """
        Remove everything from a layer.

        Args:
            layer: Layer to clear.

        """
        self.set_layer(layer, [])

    def set_search_pattern(self, pattern: str | None) -> None:
        """
        Make the search layer a text search, dropping any token entries.

        Args:
            pattern: Text to match case-insensitively, or ``None`` to clear.

        """
        self._entries[HighlightLayer.SEARCH] = []
        self._search_pattern = pattern or None
        self._search_ranges = None

    def invalidate_search_cache(self) -> None:
        """
        Forget cached search matches; call after the document is rebuilt.
        """
        self._search_ranges = None

    def match_count(self, layer: HighlightLayer) -> int:
        """
        Count the runs a layer currently resolves to.

        Args:
            layer: Layer to count.

        Returns:
            Number of resolvable runs (stale token ids are not counted).

        """
        return len(self._resolve(layer))

    def compose(self) -> list[QTextEdit.ExtraSelection]:
        """
        Compose all layers into one ExtraSelection list in paint order.

        Returns:
            The selections, or an empty list while the editor is editable
            (document offsets mean nothing then).

        """
        if self.editor.in_edit_mode:
            return []
        selections: list[QTextEdit.ExtraSelection] = []
        for layer in HighlightLayer:
            selections.extend(
                self._selection(start, end, style)
                for start, end, style in self._resolve(layer)
            )
        return selections

    def _resolve(self, layer: HighlightLayer) -> list[tuple[int, int, HighlightStyle]]:
        """
        Resolve a layer to ``(start, end, style)`` document runs.

        Args:
            layer: Layer to resolve.

        Returns:
            The runs; entries whose token ids are not in the editor's
            ``token_to_position`` map are skipped.

        """
        positions = self.editor.token_to_position
        runs: list[tuple[int, int, HighlightStyle]] = []
        for entry in self._entries[layer]:
            first = positions.get(entry.first_token_id)
            last = positions.get(entry.last_token_id)
            if first is None or last is None:
                continue
            runs.append((first[0], last[1], entry.style))
        if layer is HighlightLayer.SEARCH:
            runs.extend(
                (start, end, SEARCH_STYLE) for start, end in self._pattern_ranges()
            )
        return runs

    def _pattern_ranges(self) -> list[tuple[int, int]]:
        """
        Find the search pattern in the rendered document, caching the result.

        Returns:
            ``(start, end)`` offsets of each match.

        """
        if not self._search_pattern:
            return []
        if self._search_ranges is None:
            document = self.editor.document()
            cursor = QTextCursor(document)
            ranges: list[tuple[int, int]] = []
            while True:
                cursor = document.find(self._search_pattern, cursor)
                if cursor.isNull():
                    break
                ranges.append((cursor.selectionStart(), cursor.selectionEnd()))
            self._search_ranges = ranges
        return self._search_ranges

    def _color(self, style: HighlightStyle) -> QColor:
        """
        Resolve a style to a colour against the current palette.

        Args:
            style: Style to resolve.

        Returns:
            The colour.

        """
        if style.key is not None:
            colors = self._lookups.color_map(style.source)
            return QColor(colors.get(style.key, colors[None]))
        return QColor(getattr(AnnotationLookupsMixin, style.source))

    def _selection(
        self, start: int, end: int, style: HighlightStyle
    ) -> QTextEdit.ExtraSelection:
        """
        Build one ExtraSelection for a run.

        Args:
            start: Start offset in the document.
            end: End offset in the document.
            style: How to colour the run.

        Returns:
            The selection.

        """
        cursor = QTextCursor(self.editor.document())
        cursor.setPosition(start)
        cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        char_format = QTextCharFormat()
        char_format.setBackground(self._color(style))
        if self._lookups.is_dark_theme:
            char_format.setForeground(self._lookups.theme_base_color)
        selection = QTextEdit.ExtraSelection()
        selection.cursor = cursor  # type: ignore[attr-defined]
        selection.format = char_format  # type: ignore[attr-defined]
        return selection

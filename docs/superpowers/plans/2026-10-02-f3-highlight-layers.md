# F3 Highlight Layers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the competing `setExtraSelections` writers on a sentence card's Old English text editor with one layered compositor (mode, span, search) owned by `OldEnglishTextEdit`.

**Architecture:** A small collaborator class `HighlightLayers` (new file `oeapp/ui/highlight_layers.py`) stores declarative, token-anchored layer entries and composes them into one ExtraSelection list in a fixed paint order. `OldEnglishTextEdit` owns an instance and exposes `set_layer`, `clear_layer`, `set_search_pattern`, `recompose_highlights`. The three existing writers (`WholeSentenceHighlighter`, `SingleInstanceHighlighter`, `SearchHighlighter`) only set or clear their own layer. Editors that do not opt in (`uses_highlight_layers`), such as the full translation window's, keep today's direct path.

**Tech Stack:** Python 3.14, PySide6 (Qt `QTextEdit.ExtraSelection`), pytest + pytest-qt, ruff, mypy. Always use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`.

**Spec:** `doc/source/architecture/adr_0004_highlight_layers.rst` (ADR 0004) and `CONTEXT.md` (Highlighting section). Task 6 corrects three small points in the ADR that this plan found while reading the code.

## Global Constraints

- Run Python tooling from the repo root with `.venv/bin/...`; set `QT_QPA_PLATFORM=offscreen` for pytest. Use `/usr/bin/cd`, not bare `cd` (AGENTS.md).
- Test baseline before starting: `1012 passed, 1 skipped`. Every task must end with the full suite green (`QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -p no:cacheprovider`).
- Docstring contract (AGENTS.md): class docstrings include constructor `Args:`; function docstrings have a brief description and only the sections that apply (`Args:`, `Keyword Args:`, `Returns:`, `Raises:`, `Side Effects:`); never an empty or "None" section. Document class attributes, instance attributes assigned in `__init__`, and module globals with `#:` comments.
- Prefer cohesive classes over loose functions (AGENTS.md). The one exception in this plan is `normalized_oe_query`, an existing private method promoted to a module function so two callers can share it.
- Implement the real product change in the correct file even if it has noisy docs (AGENTS.md). Do not monkey-patch to dodge `make napoleon-gate`.
- Quality gate after the last code task: `.venv/bin/ruff check` and `.venv/bin/mypy` on touched files, `make napoleon-gate`, `graphify update .`. Per project memory `make napoleon-gate` fails today because its baseline is keyed by line number; report its result separately and do not "fix" it by changing code.
- Paint order is `MODE < SPAN < SEARCH` (search on top). Mode and span become independent layers.
- `SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY` (1002) is **kept**: the direct path for editors without layers still tags search selections with it. Only `SingleInstanceHighlighter.HIGHLIGHT_PROPERTY` (1001) and `existing_selections` are removed.
- Commit messages end with: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.

## Review Focus

Failure modes the ADR implies that the headline tests would miss, most likely first. Each has a test in the owning task.

1. A token id that no longer exists (split, delete, retokenize) between `set_layer` and compose must be skipped without error. (Task 1)
2. An empty search pattern must clear the search layer and report 0 matches, not highlight everything. (Task 3)
3. Calling the mode command's `highlight()` twice must not accumulate duplicate selections. (Task 3)
4. Changing the highlighting mode or searching while the editor is in edit mode must write nothing and not crash. (Task 4)
5. Layers whose tokens are all gone (a token-less sentence leaves `token_to_position` empty) must compose to an empty list without errors. (Task 4)

## File Structure

| File | Responsibility |
|---|---|
| `oeapp/ui/highlight_layers.py` (create) | `HighlightLayer`, `HighlightStyle`, `HighlightEntry`, `HighlightLayers`: layer state, token-to-offset resolution, style-to-format resolution, compose. |
| `oeapp/ui/mixins.py` (modify) | Add `SPAN_COLOR`, `SPAN_IDIOM_COLOR`, `SEARCH_COLOR` constants next to `IDIOM_HIGHLIGHT_COLOR`. |
| `oeapp/ui/oe_text_edit.py` (modify) | Own a `HighlightLayers`; add `uses_highlight_layers`, `set_layer`, `clear_layer`, `set_search_pattern`, `recompose_highlights`; clear layers on edit-mode entry; recompose at the end of `render_readonly_text`. |
| `oeapp/ui/full_translation_window.py` (modify, 1 line) | `FullProjectOldEnglishTextEdit.uses_highlight_layers = False`. |
| `oeapp/ui/highlighting.py` (modify) | Migrate `SearchHighlighter`, `SingleInstanceHighlighter`, `WholeSentenceHighlighter` and the command classes to layers; delete dead selection-building code. |
| `oeapp/ui/sentence_card.py` (modify) | `_highlight_oe_search` uses token-id search; `reapply_search()`; `refresh_theme()` recomposes; connect `edit_mode_finished`. |
| `oeapp/ui/search_controller.py` (modify) | Promote `_normalized_oe_query` to module function `normalized_oe_query`. |
| `tests/test_highlight_layers.py` (create) | Unit tests for `HighlightLayers`, the editor API, layer coexistence, edit-mode and theme behaviour. |
| `tests/test_highlighting.py` (modify) | Rewrite tests that asserted on property tags / `existing_selections`. |
| `tests/test_full_translation_window.py` (modify) | Regression test: the full window's editor keeps the direct search path. |
| `doc/source/architecture/adr_0004_highlight_layers.rst` (modify) | Three small corrections. |

---

### Task 1: `HighlightLayers` core (types, resolution, compose)

**Files:**
- Create: `oeapp/ui/highlight_layers.py`
- Modify: `oeapp/ui/mixins.py` (constants, near line 416)
- Test: `tests/test_highlight_layers.py` (create)

**Interfaces:**
- Consumes: `OldEnglishTextEdit.token_to_position: dict[int, tuple[int, int]]`, `OldEnglishTextEdit.in_edit_mode: bool`, `OldEnglishTextEdit.document()`; `AnnotationLookupsMixin.color_map(name)`, `.is_dark_theme`, `.theme_base_color`.
- Produces (used by Tasks 2-5):
  - `HighlightLayer(IntEnum)`: `MODE = 0`, `SPAN = 1`, `SEARCH = 2`.
  - `HighlightStyle(source: str, key: str | None = None)` frozen dataclass.
  - `HighlightEntry(first_token_id: int, last_token_id: int, style: HighlightStyle)` frozen dataclass.
  - `SEARCH_STYLE: HighlightStyle` module constant (`HighlightStyle("SEARCH_COLOR")`).
  - `HighlightLayers(editor)` with: `set_layer(layer, entries) -> None`, `clear_layer(layer) -> None`, `set_search_pattern(pattern: str | None) -> None`, `invalidate_search_cache() -> None`, `match_count(layer) -> int`, `compose() -> list[QTextEdit.ExtraSelection]`.

- [ ] **Step 1: Add the colour constants to `AnnotationLookupsMixin`**

In `oeapp/ui/mixins.py`, directly after the existing `IDIOM_HIGHLIGHT_COLOR` definition (line ~416), add:

```python
    #: Color for the selected token or span (translucent yellow)
    SPAN_COLOR: Final[QColor] = QColor(200, 200, 0, 150)
    #: Color for the selected idiom span (translucent pale magenta)
    SPAN_IDIOM_COLOR: Final[QColor] = QColor(255, 200, 255, 150)
    #: Color for search matches (bright yellow)
    SEARCH_COLOR: Final[QColor] = QColor(255, 255, 0)
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_highlight_layers.py`:

```python
import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTextEdit

from oeapp.commands import CommandManager
from oeapp.ui.highlight_layers import (
    SEARCH_STYLE,
    HighlightEntry,
    HighlightLayer,
    HighlightLayers,
    HighlightStyle,
)
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.ui.sentence_card import SentenceCard
from tests.conftest import create_test_project


def selection_ranges(selections):
    """Return ``(start, end)`` for each ExtraSelection."""
    return [(s.cursor.selectionStart(), s.cursor.selectionEnd()) for s in selections]


@pytest.fixture
def card(db_session, qapp, qtbot, mock_main_window):
    """A rendered sentence card: Se (0-2), cyning (3-9), fēoll (10-15)."""
    project = create_test_project(db_session, name="Layers", text="Se cyning fēoll.")
    card = SentenceCard(
        project.sentences[0],
        command_manager=CommandManager(db_session),
        main_window=mock_main_window,
        parent=None,
    )
    qtbot.addWidget(card)
    card.oe_text_edit.render_readonly_text()
    return card


@pytest.fixture
def token_ids(card):
    return [t.id for t in card.oe_text_edit.tokens]


class TestHighlightLayers:
    def test_entry_resolves_to_token_range_and_colour(self, card, token_ids):
        layers = HighlightLayers(card.oe_text_edit)
        style = HighlightStyle("SPAN_COLOR")
        layers.set_layer(
            HighlightLayer.SPAN, [HighlightEntry(token_ids[1], token_ids[1], style)]
        )

        selections = layers.compose()

        assert selection_ranges(selections) == [(3, 9)]
        assert (
            selections[0].format.background().color() == AnnotationLookupsMixin.SPAN_COLOR
        )

    def test_range_entry_spans_first_to_last_token(self, card, token_ids):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_layer(
            HighlightLayer.MODE,
            [HighlightEntry(token_ids[0], token_ids[1], HighlightStyle("IDIOM_HIGHLIGHT_COLOR"))],
        )

        assert selection_ranges(layers.compose()) == [(0, 9)]

    def test_colour_map_style_uses_the_map_value(self, card, token_ids):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_layer(
            HighlightLayer.MODE,
            [HighlightEntry(token_ids[1], token_ids[1], HighlightStyle("POS_COLORS", "N"))],
        )

        expected = AnnotationLookupsMixin().color_map("POS_COLORS")["N"]
        assert layers.compose()[0].format.background().color() == expected

    def test_missing_token_id_is_skipped(self, card, token_ids):
        """Review focus 1: a stale token id must not raise."""
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_layer(
            HighlightLayer.SPAN,
            [
                HighlightEntry(999_999, 999_999, HighlightStyle("SPAN_COLOR")),
                HighlightEntry(token_ids[0], token_ids[0], HighlightStyle("SPAN_COLOR")),
            ],
        )

        assert selection_ranges(layers.compose()) == [(0, 2)]

    def test_paint_order_is_mode_then_span_then_search(self, card, token_ids):
        layers = HighlightLayers(card.oe_text_edit)
        # Set in reverse order to prove order comes from the enum, not call order.
        layers.set_layer(
            HighlightLayer.SEARCH, [HighlightEntry(token_ids[1], token_ids[1], SEARCH_STYLE)]
        )
        layers.set_layer(
            HighlightLayer.SPAN,
            [HighlightEntry(token_ids[1], token_ids[1], HighlightStyle("SPAN_COLOR"))],
        )
        layers.set_layer(
            HighlightLayer.MODE,
            [HighlightEntry(token_ids[1], token_ids[1], HighlightStyle("POS_COLORS", "N"))],
        )

        colours = [s.format.background().color() for s in layers.compose()]

        assert colours[1] == AnnotationLookupsMixin.SPAN_COLOR
        assert colours[2] == AnnotationLookupsMixin.SEARCH_COLOR

    def test_compose_is_empty_while_editable(self, card, token_ids, monkeypatch):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_layer(
            HighlightLayer.SPAN,
            [HighlightEntry(token_ids[0], token_ids[0], HighlightStyle("SPAN_COLOR"))],
        )
        monkeypatch.setattr(
            type(card.oe_text_edit), "in_edit_mode", property(lambda self: True)
        )

        assert layers.compose() == []

    def test_search_pattern_matches_case_insensitively(self, card):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_search_pattern("ING")

        assert selection_ranges(layers.compose()) == [(6, 9)]
        assert layers.match_count(HighlightLayer.SEARCH) == 1

    def test_pattern_and_token_entries_replace_each_other(self, card, token_ids):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_search_pattern("ing")
        layers.set_layer(
            HighlightLayer.SEARCH, [HighlightEntry(token_ids[0], token_ids[0], SEARCH_STYLE)]
        )
        assert selection_ranges(layers.compose()) == [(0, 2)]

        layers.set_search_pattern("ing")
        assert selection_ranges(layers.compose()) == [(6, 9)]

    def test_search_ranges_are_cached_until_invalidated(self, card):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_search_pattern("ing")
        assert selection_ranges(layers.compose()) == [(6, 9)]

        card.oe_text_edit.document().setPlainText("ing ing")
        assert selection_ranges(layers.compose()) == [(6, 9)]  # stale on purpose

        layers.invalidate_search_cache()
        assert selection_ranges(layers.compose()) == [(0, 3), (4, 7)]

    def test_clear_layer_removes_pattern_too(self, card):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_search_pattern("ing")
        layers.clear_layer(HighlightLayer.SEARCH)

        assert layers.compose() == []
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py -q -p no:cacheprovider`
Expected: collection error `ModuleNotFoundError: No module named 'oeapp.ui.highlight_layers'`.

- [ ] **Step 4: Write the implementation**

Create `oeapp/ui/highlight_layers.py`:

```python
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py -q -p no:cacheprovider`
Expected: `10 passed`.

If `test_compose_is_empty_while_editable` fails because `in_edit_mode` is not a plain property on the class, read `OldEnglishTextEdit.in_edit_mode` (`oeapp/ui/oe_text_edit.py:~594`) and adjust the monkeypatch to match; the behaviour under test (empty while editable) must not change.

- [ ] **Step 6: Commit**

```bash
git add oeapp/ui/highlight_layers.py oeapp/ui/mixins.py tests/test_highlight_layers.py
git commit -m "feat: add HighlightLayers token-anchored layer compositor" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Editor owns the layers (API + capability flag)

**Files:**
- Modify: `oeapp/ui/oe_text_edit.py` (imports; `__init__` near line 513; new methods near the highlighter section)
- Modify: `oeapp/ui/full_translation_window.py:88` (class `FullProjectOldEnglishTextEdit`)
- Test: `tests/test_highlight_layers.py` (append)

**Interfaces:**
- Consumes: `HighlightLayer`, `HighlightEntry`, `HighlightLayers` from Task 1.
- Produces (used by Tasks 3-5): on `OldEnglishTextEdit`: class attribute `uses_highlight_layers: ClassVar[bool] = True`; instance attribute `highlight_layers: HighlightLayers`; methods `set_layer(layer: HighlightLayer, entries: list[HighlightEntry]) -> None`, `clear_layer(layer: HighlightLayer) -> None`, `set_search_pattern(pattern: str | None) -> None`, `recompose_highlights() -> None`. `FullProjectOldEnglishTextEdit.uses_highlight_layers` is `False`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_highlight_layers.py`:

```python
from oeapp.ui.full_translation_window import FullProjectOldEnglishTextEdit
from oeapp.ui.oe_text_edit import OldEnglishTextEdit


class TestEditorLayerApi:
    def test_capability_flag(self):
        assert OldEnglishTextEdit.uses_highlight_layers is True
        assert FullProjectOldEnglishTextEdit.uses_highlight_layers is False

    def test_set_layer_writes_composed_selections(self, card, token_ids):
        edit = card.oe_text_edit
        edit.set_layer(
            HighlightLayer.SPAN,
            [HighlightEntry(token_ids[1], token_ids[1], HighlightStyle("SPAN_COLOR"))],
        )

        assert selection_ranges(edit.extraSelections()) == [(3, 9)]

    def test_clear_layer_removes_only_that_layer(self, card, token_ids):
        edit = card.oe_text_edit
        edit.set_layer(
            HighlightLayer.SPAN,
            [HighlightEntry(token_ids[1], token_ids[1], HighlightStyle("SPAN_COLOR"))],
        )
        edit.set_layer(
            HighlightLayer.SEARCH, [HighlightEntry(token_ids[0], token_ids[0], SEARCH_STYLE)]
        )

        edit.clear_layer(HighlightLayer.SPAN)

        assert selection_ranges(edit.extraSelections()) == [(0, 2)]

    def test_set_search_pattern_writes_selections(self, card):
        edit = card.oe_text_edit
        edit.set_search_pattern("ing")

        assert selection_ranges(edit.extraSelections()) == [(6, 9)]

        edit.set_search_pattern(None)
        assert edit.extraSelections() == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py::TestEditorLayerApi -q -p no:cacheprovider`
Expected: FAIL with `AttributeError: ... has no attribute 'uses_highlight_layers'`.

- [ ] **Step 3: Implement the editor API**

In `oeapp/ui/oe_text_edit.py`:

1. Add to the imports from `oeapp.ui.highlighting`'s neighbours (top of file, with the other `oeapp.ui` imports):

```python
from oeapp.ui.highlight_layers import HighlightEntry, HighlightLayer, HighlightLayers
```

2. In the `OldEnglishTextEdit` class body, directly under its docstring and before `__init__`, add (add `ClassVar` to the `typing` import if missing):

```python
    #: Whether this editor composes its highlights through
    #: :class:`~oeapp.ui.highlight_layers.HighlightLayers`. Subclasses that keep
    #: their own ExtraSelection writers set this to ``False``.
    uses_highlight_layers: ClassVar[bool] = True
```

3. In `__init__`, directly after the `self.token_to_position` line (`oeapp/ui/oe_text_edit.py:513`), add:

```python
        #: Layered highlight state; composed into this editor's ExtraSelections
        self.highlight_layers = HighlightLayers(self)
```

4. Add these methods to the class (next to `highlight_sentence`/`unhighlight`, around line 810):

```python
    def set_layer(self, layer: HighlightLayer, entries: list[HighlightEntry]) -> None:
        """
        Replace a highlight layer and recompose.

        Args:
            layer: Layer to replace.
            entries: New entries for the layer.

        """
        self.highlight_layers.set_layer(layer, entries)
        self.recompose_highlights()

    def clear_layer(self, layer: HighlightLayer) -> None:
        """
        Clear a highlight layer and recompose.

        Args:
            layer: Layer to clear.

        """
        self.highlight_layers.clear_layer(layer)
        self.recompose_highlights()

    def set_search_pattern(self, pattern: str | None) -> None:
        """
        Make the search layer a text search and recompose.

        Args:
            pattern: Text to match, or ``None`` to clear the search layer.

        """
        self.highlight_layers.set_search_pattern(pattern)
        self.recompose_highlights()

    def recompose_highlights(self) -> None:
        """
        Write the composed layers as this editor's ExtraSelections.
        """
        self.setExtraSelections(self.highlight_layers.compose())
```

In `oeapp/ui/full_translation_window.py`, inside `class FullProjectOldEnglishTextEdit(ThemeMixin, OldEnglishTextEdit):` directly under its docstring add:

```python
    #: This editor keeps its own ExtraSelection writers and position map; it
    #: does not use the sentence card's highlight layers (finding F9).
    uses_highlight_layers: ClassVar[bool] = False
```

(add `ClassVar` to that file's `typing` import if missing).

- [ ] **Step 4: Run to verify they pass**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py -q -p no:cacheprovider`
Expected: `14 passed`.

- [ ] **Step 5: Full suite**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -p no:cacheprovider`
Expected: `1026 passed, 1 skipped` (baseline 1012 plus the 14 new tests).

- [ ] **Step 6: Commit**

```bash
git add oeapp/ui/oe_text_edit.py oeapp/ui/full_translation_window.py tests/test_highlight_layers.py
git commit -m "feat: OldEnglishTextEdit owns highlight layers" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Migrate the three writers to layers (atomic)

This task migrates `SearchHighlighter`, `SingleInstanceHighlighter` and `WholeSentenceHighlighter` together on purpose. Once any one of them goes through `recompose_highlights`, the others' direct `setExtraSelections` writes would be overwritten, so migrating them one at a time cannot keep the suite green. Do the failing tests first, then the three migrations, then fix the old tests, then one commit.

**Files:**
- Modify: `oeapp/ui/highlighting.py`
- Modify: `oeapp/ui/sentence_card.py` (`_highlight_oe_search`, around line 311-323)
- Test: `tests/test_highlight_layers.py` (append), `tests/test_highlighting.py` (rewrite listed tests), `tests/test_full_translation_window.py` (append)

**Interfaces:**
- Consumes: Task 1 types, Task 2 editor API.
- Produces:
  - `SearchHighlighter.highlight_token_ids(text_edit: "OldEnglishTextEdit", token_ids: set[int]) -> int`.
  - `WholeSentenceHighlighter.set_highlights(entries: list[HighlightEntry]) -> None`.
  - `SingleInstanceHighlighter.STYLES: ClassVar[dict[str, HighlightStyle]]`.
  - Command `COLORS` for the idiom command becomes the string `"IDIOM_HIGHLIGHT_COLOR"`.

- [ ] **Step 1: Write the failing coexistence tests**

Append to `tests/test_highlight_layers.py`:

```python
from PySide6.QtWidgets import QTextEdit as PlainTextEdit

from oeapp.models.annotation import Annotation
from oeapp.models.idiom import Idiom
from oeapp.ui.dialogs.sentence_filters import SentenceFilterDialog
from oeapp.ui.highlighting import SearchHighlighter


def annotate_pos(card, db_session, pos_by_index):
    """Give tokens a POS annotation and tell the sentence highlighter."""
    tokens = card.oe_text_edit.tokens
    for index, pos in pos_by_index.items():
        tokens[index].annotation = Annotation(token_id=tokens[index].id, pos=pos)
    db_session.commit()
    card.sentence_highlighter.annotations = {
        t.id: t.annotation for t in tokens if t.id
    }


def backgrounds(edit):
    return [s.format.background().color() for s in edit.extraSelections()]


class TestLayerCoexistence:
    @pytest.fixture(autouse=True)
    def patch_dialog_exec(self, monkeypatch):
        monkeypatch.setattr(SentenceFilterDialog, "exec", lambda self: self.show())

    @pytest.fixture
    def combo(self, card, db_session):
        annotate_pos(card, db_session, {0: "D", 1: "N"})
        return card.sentence_highlighter.build_combo_box()

    def test_search_and_mode_coexist(self, card, combo):
        """The card's required test: search plus mode."""
        edit = card.oe_text_edit
        combo.setCurrentIndex(1)  # Part of Speech
        assert len(edit.extraSelections()) == 2

        SearchHighlighter.highlight_text(edit, "fēoll")

        assert selection_ranges(edit.extraSelections())[-1] == (10, 15)
        assert len(edit.extraSelections()) == 3
        assert backgrounds(edit)[-1] == AnnotationLookupsMixin.SEARCH_COLOR

        combo.setCurrentIndex(0)  # None
        assert selection_ranges(edit.extraSelections()) == [(10, 15)]

    def test_search_and_span_coexist(self, card):
        edit = card.oe_text_edit
        edit.span_highlighter.highlight(1)
        SearchHighlighter.highlight_text(edit, "fēoll")
        assert len(edit.extraSelections()) == 2

        edit.span_highlighter.unhighlight()

        assert selection_ranges(edit.extraSelections()) == [(10, 15)]

    def test_mode_unhighlight_keeps_search_and_span(self, card, combo):
        """Regression for the setExtraSelections([]) wipe in unhighlight."""
        edit = card.oe_text_edit
        combo.setCurrentIndex(1)
        edit.span_highlighter.highlight(0)
        SearchHighlighter.highlight_text(edit, "fēoll")

        card.sentence_highlighter.unhighlight()

        assert selection_ranges(edit.extraSelections()) == [(0, 2), (10, 15)]

    def test_switching_mode_replaces_mode_layer(self, card, combo):
        edit = card.oe_text_edit
        combo.setCurrentIndex(1)  # POS: two tokens
        assert len(edit.extraSelections()) == 2

        combo.setCurrentIndex(4)  # Idiom: no idioms in this sentence

        assert edit.extraSelections() == []

    def test_mode_change_preserves_selected_span(self, card, combo):
        edit = card.oe_text_edit
        edit.span_highlighter.highlight(2)

        combo.setCurrentIndex(1)

        assert (10, 15) in selection_ranges(edit.extraSelections())

    def test_stacking_order_mode_span_search(self, card, combo):
        edit = card.oe_text_edit
        combo.setCurrentIndex(1)
        edit.span_highlighter.highlight(1)
        SearchHighlighter.highlight_text(edit, "ing")

        colours = backgrounds(edit)

        assert colours[-2] == AnnotationLookupsMixin.SPAN_COLOR
        assert colours[-1] == AnnotationLookupsMixin.SEARCH_COLOR

    def test_repeated_mode_highlight_does_not_accumulate(self, card, combo):
        """Review focus 3."""
        edit = card.oe_text_edit
        combo.setCurrentIndex(1)
        before = len(edit.extraSelections())

        card.sentence_highlighter.highlight()
        card.sentence_highlighter.highlight()

        assert len(edit.extraSelections()) == before

    def test_idiom_mode_and_span_use_distinct_alpha(self, card, db_session):
        edit = card.oe_text_edit
        tokens = edit.tokens
        idiom = Idiom(
            sentence_id=card.sentence.id,
            start_token_id=tokens[0].id,
            end_token_id=tokens[1].id,
        )
        idiom.start_token = tokens[0]
        idiom.end_token = tokens[1]
        card.sentence_highlighter.idioms = [idiom]
        card.sentence_highlighter.build_combo_box().setCurrentIndex(4)

        mode_colours = backgrounds(edit)
        assert len(mode_colours) == 2
        assert all(c.alpha() == 255 for c in mode_colours)

        edit.span_highlighter.highlight(0, 1, color_name="idiom")
        span_colours = backgrounds(edit)[2:]
        assert [c.alpha() for c in span_colours] == [150, 150]
        assert not any(s.format.fontItalic() for s in edit.extraSelections())


class TestSearchLayerEntryPoints:
    def test_empty_pattern_clears_and_returns_zero(self, card):
        """Review focus 2."""
        edit = card.oe_text_edit
        assert SearchHighlighter.highlight_text(edit, "ing") == 1

        assert SearchHighlighter.highlight_text(edit, "") == 0
        assert edit.extraSelections() == []

    def test_token_ids_search_skips_unknown_ids(self, card, token_ids):
        edit = card.oe_text_edit

        count = SearchHighlighter.highlight_token_ids(
            edit, {token_ids[0], token_ids[2], 999_999}
        )

        assert count == 2
        assert selection_ranges(edit.extraSelections()) == [(0, 2), (10, 15)]

    def test_clear_highlight_clears_search_layer(self, card):
        edit = card.oe_text_edit
        SearchHighlighter.highlight_text(edit, "ing")

        SearchHighlighter.clear_highlight(edit)

        assert edit.extraSelections() == []

    def test_plain_text_edit_keeps_direct_path(self, qapp):
        plain = PlainTextEdit()
        plain.setPlainText("one two one")

        assert SearchHighlighter.highlight_text(plain, "one") == 2
        assert all(
            s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)
            for s in plain.extraSelections()
        )
        SearchHighlighter.clear_highlight(plain)
        assert plain.extraSelections() == []
```

Append to `tests/test_full_translation_window.py`, inside the existing `TestFullTranslationWindow`-style class that owns the `full_window` fixture (place it next to `test_search_notes`; match that class's indentation):

```python
    def test_oe_edit_search_keeps_direct_path(self, full_window):
        """The full window's editor must not be captured by the layer path."""
        from oeapp.ui.highlighting import SearchHighlighter

        edit = full_window.oe_edit
        assert edit.uses_highlight_layers is False
        pattern = full_window.project.sentences[0].text_oe.split()[0][:2]

        assert SearchHighlighter.highlight_text(edit, pattern) > 0
        assert any(
            s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)
            for s in edit.extraSelections()
        )

        SearchHighlighter.clear_highlight(edit)
        assert not any(
            s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)
            for s in edit.extraSelections()
        )
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py::TestLayerCoexistence tests/test_highlight_layers.py::TestSearchLayerEntryPoints -q -p no:cacheprovider`
Expected: FAIL (e.g. `test_mode_unhighlight_keeps_search_and_span` fails because `unhighlight` still wipes everything; `highlight_token_ids` does not exist).

- [ ] **Step 3: Migrate `highlighting.py`**

Make these edits in `oeapp/ui/highlighting.py`.

3a. Imports. Replace the top-of-file imports with:

```python
from typing import TYPE_CHECKING, ClassVar, cast

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QPalette, QTextCharFormat, QTextCursor, QTextDocument
from PySide6.QtWidgets import QComboBox, QTextEdit
from qtpy.QtWidgets import QApplication

from oeapp.ui.dialogs import (
    CaseFilterDialog,
    NumberFilterDialog,
    PartOfSpeechFilterDialog,
)
from oeapp.ui.highlight_layers import (
    SEARCH_STYLE,
    HighlightEntry,
    HighlightLayer,
    HighlightStyle,
)

from .mixins import AnnotationLookupsMixin
```

and in the `TYPE_CHECKING` block add `from oeapp.ui.oe_text_edit import OldEnglishTextEdit`.

3b. `SelectTokensMixin`: change the annotation of `self.oe_text_edit` to `"OldEnglishTextEdit"`:

```python
        #: The Old English text edit
        self.oe_text_edit: OldEnglishTextEdit = card.oe_text_edit
```

and **delete** the methods `select_tokens` and `highlight_positions` (lines ~88-153). Keep `get_token_positions` and `refresh_token_views`.

3c. `HighlighterCommandBase`: update the `COLORS` doc comment to say "name of a colour map or of a single colour constant on :class:`~oeapp.ui.mixins.AnnotationLookupsMixin`" and change its annotation to `COLORS: ClassVar[str] = ""`. Replace `HighlighterCommandBase.highlight` with:

```python
    def highlight(self) -> None:
        """
        Apply the highlighting for the command.
        """
        self.refresh_command_views()
        colors = self.color_map(self.COLORS)
        self.unhighlight()
        text = self.highlighter.get_oe_text()
        if not text or not self.tokens:
            return

        entries: list[HighlightEntry] = []
        for token in self.tokens:
            if not token.id:
                continue
            annotation = self.annotations.get(cast("int", token.id))
            if not annotation:
                continue
            value = self.get_value(annotation)
            if not value:
                # Don't highlight if there is no value for the annotation
                continue
            if not self.dialog or value in self.filter_selection:
                if colors.get(value, colors[None]) == colors[None]:
                    # Don't highlight if the value is the default
                    continue
                entries.append(
                    HighlightEntry(
                        token.id, token.id, HighlightStyle(self.COLORS, value)
                    )
                )

        self.highlighter.set_highlights(entries)
```

3d. `IdiomHighlighterCommand`: set `COLORS: ClassVar[str] = "IDIOM_HIGHLIGHT_COLOR"` (update its comment: "Name of the idiom colour constant") and replace its `highlight` body (keep the docstring) with:

```python
        self.unhighlight()
        text = self.highlighter.get_oe_text()
        if not text or not self.tokens or not self.idioms:
            return

        style = HighlightStyle(self.COLORS)
        entries: list[HighlightEntry] = []
        for idiom in self.idioms:
            # Highlight every token in the idiom
            for order_idx in range(
                idiom.start_token.order_index, idiom.end_token.order_index + 1
            ):
                token = self.tokens_by_index.get(order_idx)
                if token and token.id in self.token_positions:
                    entries.append(HighlightEntry(token.id, token.id, style))

        self.highlighter.set_highlights(entries)
```

The other command subclasses (`NoneHighlighterCommand`, POS, Case, Number) need no change: their `COLORS` are already strings.

3e. `WholeSentenceHighlighter.unhighlight` — replace the `setExtraSelections([])` line:

```python
        # Block signals temporarily to avoid triggering change signal
        self.highlighting_combo.blockSignals(True)  # noqa: FBT003
        self.card.oe_text_edit.clear_layer(HighlightLayer.MODE)
        self.highlighting_combo.blockSignals(False)  # noqa: FBT003
```

and update its docstring to "Clear the mode layer of our associated sentence card's OE text edit.".

3f. Replace `WholeSentenceHighlighter.set_highlights` with:

```python
    def set_highlights(self, entries: list[HighlightEntry]) -> None:
        """
        Set the mode layer for the sentence.

        Args:
            entries: Entries for the mode layer

        """
        assert self.card, "Sentence card is required"  # noqa: S101
        self.card.oe_text_edit.set_layer(HighlightLayer.MODE, entries)
```

3g. `SingleInstanceHighlighter` — replace the class attributes and the methods `__init__` (drop `existing_selections`), `set_existing_selections` (delete), `unhighlight`, and `highlight`:

```python
    #: Color for highlighting tokens
    COLORS: ClassVar[dict[str, QColor]] = {
        "default": AnnotationLookupsMixin.SPAN_COLOR,
        "idiom": AnnotationLookupsMixin.SPAN_IDIOM_COLOR,
    }
    #: Highlight style for each color name
    STYLES: ClassVar[dict[str, HighlightStyle]] = {
        "default": HighlightStyle("SPAN_COLOR"),
        "idiom": HighlightStyle("SPAN_IDIOM_COLOR"),
    }
```

(delete `HIGHLIGHT_PROPERTY`). In `__init__` remove the `self.existing_selections` lines. Then:

```python
    def unhighlight(self) -> None:
        """
        Unhighlight the tokens in the sentence by clearing the span layer.
        """
        self.oe_text_edit.clear_layer(HighlightLayer.SPAN)
        self.reset()

    def highlight(
        self,
        start_order: int,
        end_order: int | None = None,
        color_name: str = "default",
    ) -> None:
        """
        Highlight the token(s) in the sentence.

        Args:
            start_order: Starting token order_index (inclusive)

        Keyword Args:
            end_order: Ending token order_index (inclusive)
            color_name: Color to use for highlighting. Defaults to "default".

        """
        assert color_name in self.STYLES, "Invalid color name"  # noqa: S101
        style = self.STYLES[color_name]

        if end_order is None:
            end_order = start_order

        assert start_order is not None, "Start order must be provided"  # noqa: S101
        assert start_order <= end_order, (  # noqa: S101
            "Start order must be less or equal to end order"
        )
        assert start_order >= 0, "Start order must be greater than 0"  # noqa: S101

        self.unhighlight()

        if not self.tokens:
            return

        token_positions = self.get_token_positions(start_order, end_order)
        if not token_positions:
            return

        # One entry per token, so note superscripts between tokens stay unhighlighted
        entries = [
            HighlightEntry(token.id, token.id, style)
            for order_idx in range(start_order, end_order + 1)
            if (token := self.tokens_by_index.get(order_idx))
            and token.id in self.token_positions
        ]
        self.oe_text_edit.set_layer(HighlightLayer.SPAN, entries)

        # Store range for is_highlighted
        first_start = token_positions[0][0]
        last_end = token_positions[-1][1]
        self._current_highlight_start = first_start
        self._current_highlight_length = last_end - first_start
```

3h. `SearchHighlighter`. Change `SEARCH_COLOR` to `ClassVar[QColor] = AnnotationLookupsMixin.SEARCH_COLOR`. Add a helper and layer branches. Add at the top of the class (after the constants):

```python
    @staticmethod
    def _uses_layers(text_edit: QTextEdit) -> bool:
        """
        Whether a text edit composes its highlights through highlight layers.

        Args:
            text_edit: Text edit to check.

        Returns:
            True for editors that opt in with ``uses_highlight_layers``.

        """
        return bool(getattr(text_edit, "uses_highlight_layers", False))
```

At the very start of `highlight_text` (before the `settings = QSettings()` line) add:

```python
        if SearchHighlighter._uses_layers(text_edit):
            editor = cast("OldEnglishTextEdit", text_edit)
            editor.set_search_pattern(pattern or None)
            return editor.highlight_layers.match_count(HighlightLayer.SEARCH)
```

Add the new method after `highlight_text`:

```python
    @staticmethod
    def highlight_token_ids(text_edit: "OldEnglishTextEdit", token_ids: set[int]) -> int:
        """
        Highlight tokens as search matches in a layered editor.

        Args:
            text_edit: Editor whose search layer to set.
            token_ids: Ids of the tokens that matched.

        Returns:
            Number of highlighted tokens (ids unknown to the editor are skipped).

        """
        positions = text_edit.token_to_position
        known = sorted(
            (token_id for token_id in token_ids if token_id in positions),
            key=lambda token_id: positions[token_id][0],
        )
        text_edit.set_layer(
            HighlightLayer.SEARCH,
            [HighlightEntry(token_id, token_id, SEARCH_STYLE) for token_id in known],
        )
        return len(known)
```

At the start of `clear_highlight` (before `selections = text_edit.extraSelections()`) add:

```python
        if SearchHighlighter._uses_layers(text_edit):
            cast("OldEnglishTextEdit", text_edit).clear_layer(HighlightLayer.SEARCH)
            return
```

Leave `highlight_token_ranges` and the direct-path bodies unchanged; they still serve editors that do not use layers.

- [ ] **Step 4: Route the card's token search through the layer**

In `oeapp/ui/sentence_card.py`, in `_highlight_oe_search` (around line 311-323) replace the token branch:

```python
        if token_ids:
            return SearchHighlighter.highlight_token_ids(self.oe_text_edit, token_ids)
        return SearchHighlighter.highlight_text(self.oe_text_edit, pattern)
```

Then run `grep -rn "_token_ranges_for_ids" oeapp tests`. If the only remaining hit is its own definition, delete that method; if a test uses it, keep the method.

- [ ] **Step 5: Rewrite the old `TestSingleInstanceHighlighter` tests**

In `tests/test_highlighting.py` these tests assert on the removed `HIGHLIGHT_PROPERTY` or `existing_selections`. Replace them with:

```python
    def test_highlight_single_token(self, span_highlighter, card):
        """Test highlighting a single token."""
        span_highlighter.highlight(0)
        assert span_highlighter.is_highlighted
        assert span_highlighter._current_highlight_start == 0
        assert span_highlighter._current_highlight_length == 2

        selections = card.oe_text_edit.extraSelections()
        assert [(s.cursor.selectionStart(), s.cursor.selectionEnd()) for s in selections] == [(0, 2)]

    def test_highlight_range(self, span_highlighter, card):
        """Test highlighting a range of tokens."""
        span_highlighter.highlight(0, 1)
        assert span_highlighter.is_highlighted
        # Range covers "Se cyning" (0 to 9)
        assert span_highlighter._current_highlight_start == 0
        assert span_highlighter._current_highlight_length == 9

        selections = card.oe_text_edit.extraSelections()
        assert len(selections) == 2  # One for each token in range

    def test_unhighlight(self, span_highlighter, card):
        """Test clearing highlights."""
        span_highlighter.highlight(0)
        assert span_highlighter.is_highlighted

        span_highlighter.unhighlight()
        assert not span_highlighter.is_highlighted
        assert card.oe_text_edit.extraSelections() == []

    def test_unhighlight_preserves_other_layers(self, span_highlighter, card):
        """Unhighlighting the span leaves the search layer alone."""
        SearchHighlighter.highlight_text(card.oe_text_edit, "fēoll")
        span_highlighter.highlight(1)  # "cyning"
        assert len(card.oe_text_edit.extraSelections()) == 2

        span_highlighter.unhighlight()

        remaining = card.oe_text_edit.extraSelections()
        assert len(remaining) == 1
        assert remaining[0].format.background().color() == SearchHighlighter.SEARCH_COLOR

    def test_highlight_different_colors(self, span_highlighter, card):
        """Test highlighting with different defined colors."""
        span_highlighter.highlight(0, color_name="idiom")
        highlight = card.oe_text_edit.extraSelections()[0]
        assert highlight.format.background().color() == span_highlighter.COLORS["idiom"]

    def test_highlight_clears_previous_own_highlight(self, span_highlighter, card):
        """Test that new highlights replace old ones from the same highlighter."""
        span_highlighter.highlight(0)
        assert span_highlighter._current_highlight_start == 0

        span_highlighter.highlight(1)
        assert span_highlighter._current_highlight_start == 3  # "cyning" starts at 3

        selections = card.oe_text_edit.extraSelections()
        assert [(s.cursor.selectionStart(), s.cursor.selectionEnd()) for s in selections] == [(3, 9)]
```

(`test_highlight_clears_previous_own_highlight` currently reads the removed `HIGHLIGHT_PROPERTY` at about line 407-416; replace it with the version above. Search the file for every remaining `HIGHLIGHT_PROPERTY` reference with `grep -n "HIGHLIGHT_PROPERTY" tests/test_highlighting.py` and rewrite each one the same way; `SEARCH_HIGHLIGHT_PROPERTY` references in `TestSearchHighlighterClear` stay.)

Leave `test_initialization`, `test_get_token_positions`, `test_highlight_invalid_color` and `test_highlight_invalid_range` as they are. Remove the now-unused `QColor`/`QTextCursor`/`QTextEdit` imports from the file only if ruff reports them unused after the whole file is reviewed (other tests in the file still use `QTextEdit` and `QTextCursor` in `TestSearchHighlighterClear`).

`test_idiom_highlighting` in `TestHighlighting` patches `set_highlights` and asserts `len(args[0]) == 2`; with entries that still holds (one entry per idiom token). `IdiomHighlighterCommand.highlight` now requires `token.id in self.token_positions`, so call `card.oe_text_edit.render_readonly_text()` at the start of that test if it fails with 0 entries.

- [ ] **Step 6: Run the focused tests**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py tests/test_highlighting.py tests/test_full_translation_window.py -q -p no:cacheprovider`
Expected: all pass. The full-window guard test added in Step 1 passes even before the migration (it protects against the layer path capturing that editor); that is expected.

Typing: `Token.id` is `int | None`. Wherever the code above builds a `HighlightEntry` from a token that was not narrowed by an `if not token.id: continue` check (the idiom command and `SingleInstanceHighlighter.highlight`), write `cast("int", token.id)`, matching how this repo handles token ids elsewhere.

Behaviour changes to expect and keep (they are in the ADR or are consequences of it): a selected span now survives a mode change; the search layer's dark-theme foreground now follows `ThemeMixin.is_dark_theme` (palette lightness) in layered editors instead of the `theme/name` QSettings value (no existing test asserts on it).

- [ ] **Step 7: Full suite**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -p no:cacheprovider`
Expected: all pass, 1 skipped.

- [ ] **Step 8: Commit**

```bash
git add oeapp/ui/highlighting.py oeapp/ui/sentence_card.py tests/test_highlight_layers.py tests/test_highlighting.py tests/test_full_translation_window.py
git commit -m "refactor: route mode, span and search highlights through layers" -m "Fixes the setExtraSelections([]) wipe in WholeSentenceHighlighter.unhighlight (audit finding F3)." -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Edit mode, re-render and `reapply_search`

**Files:**
- Modify: `oeapp/ui/oe_text_edit.py` (`in_edit_mode` setter ~line 645; `render_readonly_text` ~line 856-922)
- Modify: `oeapp/ui/search_controller.py` (promote `_normalized_oe_query`)
- Modify: `oeapp/ui/sentence_card.py` (`reapply_search`, signal connection)
- Test: `tests/test_highlight_layers.py` (append)

**Interfaces:**
- Consumes: Task 2 editor API.
- Produces: `normalized_oe_query(pattern: str, scope: str) -> str | None` module function in `oeapp/ui/search_controller.py`; `SentenceCard.reapply_search() -> int`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_highlight_layers.py`:

```python
from PySide6.QtWidgets import QComboBox, QLineEdit

from oeapp.ui.search_controller import normalized_oe_query


class TestEditModeAndRerender:
    @pytest.fixture(autouse=True)
    def patch_dialog_exec(self, monkeypatch):
        monkeypatch.setattr(SentenceFilterDialog, "exec", lambda self: self.show())

    @pytest.fixture
    def search_ui(self, mock_main_window):
        mock_main_window.search_input = QLineEdit("cyning")
        mock_main_window.search_scope_combo = QComboBox()
        mock_main_window.search_scope_combo.addItems(["OE Text", "ModE text", "Notes", "All"])
        return mock_main_window

    def test_normalized_oe_query_depends_on_scope(self):
        assert normalized_oe_query("Cyning", "OE Text") == "cyning"
        assert normalized_oe_query("Cyning", "ModE text") is None

    def test_entering_edit_mode_clears_all_layers(self, card, search_ui):
        edit = card.oe_text_edit
        card.sentence_highlighter.build_combo_box()  # unhighlight() needs the combo
        edit.span_highlighter.highlight(0)
        SearchHighlighter.highlight_text(edit, "cyning")
        assert edit.extraSelections()

        edit.in_edit_mode = True

        assert edit.extraSelections() == []
        # Review focus 4: nothing is composed while editable, and nothing crashes.
        edit.set_search_pattern("cyning")
        edit.span_highlighter.highlight(1)
        assert edit.extraSelections() == []

    def test_leaving_edit_mode_reapplies_search(self, card, search_ui):
        edit = card.oe_text_edit
        card.sentence_highlighter.build_combo_box()
        edit.in_edit_mode = True
        edit.in_edit_mode = False

        card.edit_mode_finished.emit()

        assert (3, 9) in selection_ranges(edit.extraSelections())

    def test_reapply_search_without_search_ui_is_a_no_op(self, card):
        assert card.reapply_search() == 0

    def test_reapply_search_with_empty_query_is_a_no_op(self, card, search_ui):
        search_ui.search_input.setText("")
        assert card.reapply_search() == 0
        assert card.oe_text_edit.extraSelections() == []

    def test_rerender_keeps_span_and_search_layers(self, card, search_ui):
        edit = card.oe_text_edit
        edit.span_highlighter.highlight(0)
        SearchHighlighter.highlight_text(edit, "fēoll")

        edit.render_readonly_text()

        assert selection_ranges(edit.extraSelections()) == [(0, 2), (10, 15)]

    def test_composing_with_no_token_positions_is_empty(self, card, search_ui):
        """Review focus 5: layers whose tokens are all gone compose to nothing."""
        edit = card.oe_text_edit
        edit.span_highlighter.highlight(0)
        SearchHighlighter.highlight_token_ids(edit, {edit.tokens[1].id})
        assert edit.extraSelections()

        edit.token_to_position.clear()  # what a render of a token-less sentence leaves
        edit.recompose_highlights()

        assert edit.extraSelections() == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py::TestEditModeAndRerender -q -p no:cacheprovider`
Expected: FAIL (`ImportError: cannot import name 'normalized_oe_query'`).

If `test_rendering_a_sentence_with_no_tokens_composes_empty` errors in setup because blanking `text_oe` on the ORM object is not enough to make `render_readonly_text` render zero tokens, change only the setup lines so the editor ends up with no tokens (for example set `edit.sentence.tokens` to `[]` before rendering); the assertion (composes empty, no exception) must stay.

- [ ] **Step 3: Promote the normalized-query helper**

In `oeapp/ui/search_controller.py`, add a module-level function above the `SearchController` class (the file already imports `normalize_old_english`):

```python
def normalized_oe_query(pattern: str, scope: str) -> str | None:
    """
    Return the normalized OE search query for OE-aware scopes.

    Args:
        pattern: Raw search pattern.
        scope: Search scope.

    Returns:
        Normalized OE query, or None when the scope disables OE matching.

    """
    if scope not in {"OE Text", "Notes", "All"}:
        return None
    return normalize_old_english(pattern) or None
```

and make `SearchController._normalized_oe_query` delegate to it:

```python
    def _normalized_oe_query(self, pattern: str, scope: str) -> str | None:
        """
        Return normalized OE search query for OE-aware scopes.

        Args:
            pattern: Raw search pattern.
            scope: Search scope.

        Returns:
            Normalized OE query, or None when scope disables OE matching.

        """
        return normalized_oe_query(pattern, scope)
```

- [ ] **Step 4: Add `reapply_search` to `SentenceCard` and connect it**

In `oeapp/ui/sentence_card.py` add the import `from oeapp.ui.search_controller import normalized_oe_query` (check for an import cycle: `search_controller` already imports `SentenceCard` only under `TYPE_CHECKING`; if a runtime cycle appears, import inside the method instead). Add this method next to `highlight_search`:

```python
    def reapply_search(self) -> int:
        """
        Re-run the main window's active search against this card.

        Called after edit mode ends, because saving re-tokenizes the sentence
        and the search layer is a cache that is not trusted across a token
        change.

        Returns:
            Number of matches found, or 0 when there is no active search.

        """
        search_input = getattr(self.main_window, "search_input", None)
        scope_combo = getattr(self.main_window, "search_scope_combo", None)
        if search_input is None or scope_combo is None:
            return 0
        pattern = search_input.text()
        if not pattern:
            return 0
        scope = scope_combo.currentText()
        return self.highlight_search(
            pattern, scope, normalized_oe_query(pattern, scope), None
        )
```

In `SentenceCard.__init__`, next to where the card wires its other signals (near `self.sentence_highlighter._on_edit_oe_clicked` at line ~132), add:

```python
        self.edit_mode_finished.connect(self.reapply_search)
```

(Place it after `edit_mode_finished` exists as a class-level `Signal`, which it is at line 88.)

- [ ] **Step 5: Edit mode entry and re-render in the editor**

In `oeapp/ui/oe_text_edit.py`, in the `in_edit_mode` setter's `if value:` branch, after the two `unhighlight()` lines add:

```python
            self.clear_layer(HighlightLayer.SEARCH)
```

In `render_readonly_text`:
- Delete the local `highlighter = cast("SingleInstanceHighlighter", self.span_highlighter)` line.
- Delete the block that starts `# Restore highlight if a token was selected` and the block that starts `# Re-apply search highlighting if needed` (the span and search layers persist across the rebuild and are recomposed).
- Immediately before `self.resize_to_fit_text()` at the end, add:

```python
        # The document was rebuilt: layer entries are token-anchored, so drop
        # cached offsets and recompose against the fresh token_to_position map.
        self.highlight_layers.invalidate_search_cache()
        self.recompose_highlights()
```

Then run `.venv/bin/ruff check oeapp/ui/oe_text_edit.py` and remove any import that became unused (`SearchHighlighter`, possibly `SingleInstanceHighlighter` if no other use remains).

- [ ] **Step 6: Run the tests**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py -q -p no:cacheprovider`
Expected: all pass.

- [ ] **Step 7: Full suite**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -p no:cacheprovider`
Expected: all pass, 1 skipped.

- [ ] **Step 8: Commit**

```bash
git add oeapp/ui/oe_text_edit.py oeapp/ui/sentence_card.py oeapp/ui/search_controller.py tests/test_highlight_layers.py
git commit -m "feat: clear layers on edit mode, recompose on render, re-run search on exit" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Theme switching recomposes all layers

**Files:**
- Modify: `oeapp/ui/sentence_card.py` (`refresh_theme`, ~line 691)
- Test: `tests/test_highlight_layers.py` (append)

**Interfaces:**
- Consumes: `OldEnglishTextEdit.recompose_highlights()` from Task 2.
- Produces: none.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_highlight_layers.py`:

```python
from PySide6.QtGui import QTextFormat

from oeapp.ui.mixins import ThemeMixin


class TestThemeSwitch:
    def test_refresh_theme_recolours_span_and_search_layers(self, card, monkeypatch):
        edit = card.oe_text_edit
        edit.span_highlighter.highlight(0)
        SearchHighlighter.highlight_text(edit, "fēoll")
        has_foreground = QTextFormat.Property.ForegroundBrush
        assert not any(s.format.hasProperty(has_foreground) for s in edit.extraSelections())

        monkeypatch.setattr(ThemeMixin, "is_dark_theme", property(lambda self: True))
        card.refresh_theme()

        assert all(s.format.hasProperty(has_foreground) for s in edit.extraSelections())

    def test_refresh_theme_without_active_command_does_not_crash(self, card):
        card.sentence_highlighter.build_combo_box()
        card.refresh_theme()
```

- [ ] **Step 2: Run to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py::TestThemeSwitch -q -p no:cacheprovider`
Expected: the first test FAILS (`refresh_theme` only re-runs the active mode command, which does nothing when no mode is active, so the span and search layers keep their light-theme formats).

- [ ] **Step 3: Implement**

In `oeapp/ui/sentence_card.py`, `refresh_theme`, replace the body's last line and extend the docstring:

```python
        self._apply_verse_background_style()
        self.sentence_highlighter.highlight()
        # Layer entries hold semantic styles, so recomposing recolours the
        # mode, span and search layers against the new palette.
        self.oe_text_edit.recompose_highlights()
```

Keep the existing docstring and add one sentence to it: "The highlight layers resolve their styles at compose time, so recomposing them is enough."

The `self.sentence_highlighter.highlight()` call stays on purpose, even though ADR D6 says `refresh_theme` "no longer has to rebuild the mode highlight": re-running the command also re-applies its "skip values that equal the default colour" filter against the new palette, and it is cheap. The ADR wording is "no longer has to", not "must not".

- [ ] **Step 4: Run to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest tests/test_highlight_layers.py::TestThemeSwitch -q -p no:cacheprovider`
Expected: `2 passed`.

- [ ] **Step 5: Full suite**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -p no:cacheprovider`
Expected: all pass, 1 skipped.

- [ ] **Step 6: Commit**

```bash
git add oeapp/ui/sentence_card.py tests/test_highlight_layers.py
git commit -m "fix: live theme switch recolours all highlight layers" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Clean up, correct the ADR, quality gate

**Files:**
- Modify: `oeapp/ui/highlighting.py` (dead code), `doc/source/architecture/adr_0004_highlight_layers.rst`
- Verify: all touched files

**Interfaces:**
- Consumes: everything above.
- Produces: none.

- [ ] **Step 1: Find and remove dead code**

Run: `grep -rn "HIGHLIGHT_PROPERTY\|existing_selections\|set_existing_selections\|highlight_positions\|select_tokens(\|1001" oeapp tests | grep -v "SEARCH_HIGHLIGHT_PROPERTY\|full_translation_window\|oe_text_edit.py.*def select_tokens"`
Expected: no remaining references to `SingleInstanceHighlighter.HIGHLIGHT_PROPERTY`, `existing_selections`, `set_existing_selections`, `highlight_positions`, or the mixin's `select_tokens`. Delete any that remain (they are dead after Task 3). `SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY` and the full window's own `*_HIGHLIGHT_PROPERTY` constants stay.

- [ ] **Step 1b: Audit the now-redundant re-highlight calls (ADR consequence)**

Run: `grep -n "sentence_highlighter.highlight()\|span_highlighter.highlight(" oeapp/ui/oe_text_edit.py oeapp/ui/sentence_card.py`
Known sites: `oe_text_edit.py` after leaving edit mode (`in_edit_mode` setter, `sentence_highlighter.highlight()`) and `sentence_card.py` after an annotation is applied. Both re-run the mode command, which is idempotent (Task 3 tests it) and still needed, because the mode layer is cleared on edit-mode entry and annotation changes alter which tokens a mode colours. Leave them. The `_current_highlight_start` and `_current_highlight_length` numbers on `SingleInstanceHighlighter` can be stale after a re-render that moves offsets; they only back `is_highlighted`, so this is harmless, but do not start reading them for geometry.

- [ ] **Step 2: Correct the ADR**

In `doc/source/architecture/adr_0004_highlight_layers.rst` make these three edits:

1. D6, the paragraph beginning "Mode entries are one per token": replace "Span entries for an idiom or note span use its end tokens, so the highlight covers any superscripts between them." with "Span entries are also one per token, as today, so note superscripts between tokens stay unhighlighted; the ``(first, last)`` shape allows a contiguous run if a future layer needs one."
2. D7, the paragraph beginning "Highlighter commands build entries": replace "The property tags ``1001`` and ``1002``, ``existing_selections``, and the merge code in ``set_highlights`` and ``set_existing_selections`` are removed." with "The property tag ``1001``, ``existing_selections``, and the merge code in ``set_highlights`` and ``set_existing_selections`` are removed. Tag ``1002`` (``SEARCH_HIGHLIGHT_PROPERTY``) stays, because the direct path for editors without layers still uses it."
3. D6, the style sentence: replace "``style`` is a semantic key (for example ``MODE_POS``, ``MODE_IDIOM``, ``SPAN``, ``SPAN_IDIOM``, ``SEARCH``)." with "``style`` is a ``HighlightStyle(source, key)``: the name of an ``AnnotationLookupsMixin`` colour map plus a key (for example ``HighlightStyle(\"POS_COLORS\", \"N\")``), or the name of a single colour constant (for example ``HighlightStyle(\"SPAN_COLOR\")``)."

Validate: `.venv/bin/python -c "import docutils.core,io,sys; e=io.StringIO(); docutils.core.publish_string(open('doc/source/architecture/adr_0004_highlight_layers.rst',encoding='utf-8').read(), writer_name='null', settings_overrides={'warning_stream': e, 'report_level': 2}); print(e.getvalue() or 'no warnings')"`
Expected: `no warnings`.

- [ ] **Step 3: Lint and types on touched files**

Run:
```bash
.venv/bin/ruff check oeapp/ui/highlight_layers.py oeapp/ui/highlighting.py oeapp/ui/oe_text_edit.py oeapp/ui/sentence_card.py oeapp/ui/search_controller.py oeapp/ui/mixins.py oeapp/ui/full_translation_window.py tests/test_highlight_layers.py
.venv/bin/mypy oeapp/ui/highlight_layers.py oeapp/ui/highlighting.py oeapp/ui/oe_text_edit.py oeapp/ui/sentence_card.py oeapp/ui/search_controller.py
```
Expected: no new findings in the touched files. The repo has thousands of pre-existing ruff findings (mostly in tests) and three pre-existing mypy errors outside alembic (`oeapp/ui/application.py:35`, `oeapp/ui/dialogs/pos_form_system.py:486` and `:509`). To tell old from new, run the same commands on the files before your change with `git stash` or on a `master` checkout, and fix every finding this work introduced (docstring sections, `#:` attribute comments, unused imports, typing).

- [ ] **Step 4: Napoleon gate (report separately)**

Run: `make napoleon-gate`
Expected: per project memory this fails today because its baseline is keyed by line number. Record the output, state which failures are pre-existing, and do not change production code to satisfy it.

- [ ] **Step 5: Full suite and graph**

Run:
```bash
QT_QPA_PLATFORM=offscreen .venv/bin/pytest -q -p no:cacheprovider
graphify update .
```
Expected: all tests pass (1 skipped); graphify reports `Code graph updated`.

- [ ] **Step 6: Commit**

```bash
git add -A oeapp tests doc graphify-out
git commit -m "chore: remove dead selection code, correct ADR 0004, refresh graph" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage (ADR 0004 and the test list):** D1/D7 owner and API (Tasks 1-2); D2 stacking and independence (Tasks 1, 3); D3 single mode slot (Task 3, `test_switching_mode_replaces_mode_layer`); D4 idiom contract (Task 3, `test_idiom_mode_and_span_use_distinct_alpha`); D5 capability flag and full-window regression (Tasks 2, 3); D6 declarative entries, theme resolution, search cache, edit-mode clear and `reapply_search` (Tasks 1, 4, 5); the 13 follow-up tests are covered by the named tests above (search+mode, search+span, per-layer clear, mode exclusivity, stacking, idiom, edit-mode entry, `reapply_search` on exit, re-render, missing token, plain `QTextEdit`, full window, theme, mode-change-preserves-span).

**Known gap, flagged:** the ADR's save-versus-cancel difference ("at new coordinates on save, at the original ones on cancel") is exercised only through `edit_mode_finished` with unchanged text. A true re-tokenizing save is covered by existing `EditSentenceCommand` tests plus the unit-level guarantee that stale token ids are skipped (Task 1). If the implementer wants an end-to-end save test, build it on `SentenceCardController.on_save_oe_clicked` after the layers land.

**Open question carried from the ADR:** whether the span layer is ever used for a whole-sentence note. This plan does not add a whole-sentence form; check `oe_text_edit.py` callers of `span_highlighter.highlight` (lines ~305, 368, 385, 727, 793) while doing Task 3 and raise it if any pass a range that is not a token run.

**Type consistency:** `HighlightLayer`, `HighlightStyle(source, key)`, `HighlightEntry(first_token_id, last_token_id, style)`, `SEARCH_STYLE`, `HighlightLayers.set_layer/clear_layer/set_search_pattern/invalidate_search_cache/match_count/compose`, `OldEnglishTextEdit.set_layer/clear_layer/set_search_pattern/recompose_highlights/highlight_layers/uses_highlight_layers`, `SearchHighlighter.highlight_token_ids`, `WholeSentenceHighlighter.set_highlights(entries)`, `SingleInstanceHighlighter.STYLES`, `normalized_oe_query`, `SentenceCard.reapply_search` are named identically in every task that uses them.

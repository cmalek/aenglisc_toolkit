# Usability Overhaul — Ready Slices Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the app usable by non-programmers by fixing live theme switching, the confirmed UI affordance defects, and the help-build correctness gaps — without destabilizing the maintainer's daily driver.

**Architecture:** Six independent, individually revertible tasks on the `usability-overhaul` branch. Each is a self-contained commit with its own test. No task depends on another's implementation except Task 2, which depends on Task 1's `apply_theme()` helper. Nothing here touches the deferred 60-site stylesheet migration.

**Tech Stack:** PySide6 (Qt 6), `qt_themes`, pytest + pytest-qt, GNU Make, uv.

**Spec:** `docs/adr/0001-usability-overhaul.md`

## Global Constraints

- Python 3.13 only. **Always `uv sync --python 3.13`** — a bare `uv sync` recreates the venv on 3.14 and fails (`spacy` has no cp314 wheel).
- `.venv` is shared across git branches. Never leave a dependency change unreverted at end of session — it breaks `master` too.
- Do **not** add dependencies. No new packages for anything in this plan.
- Napoleon docstrings are gate-enforced. Every new function/method needs `Args:`/`Returns:` sections where applicable. Verify with `make napoleon-gate`.
- Test baseline is **315 passed, 1 skipped, 1 failed**. The one failure is `tests/test_export_pdf.py::TestFullTranslationPDFExporter::test_fixture_seafarer_tex_contains_new_layout_and_long_ash`, caused by the pre-existing deleted fixture `texts/The_Seafarer.json`. It is unrelated to this work. Do not "fix" it; do not let it block a task.
- Run tests with `.venv/bin/python -m pytest`.
- Theme names: user-facing values are `"dark"` and `"light"`; `qt_themes` names are `"nord"` and `"modern_light"`. The mapping lives in `SettingsDialog.THEMES` (`oeapp/ui/dialogs/settings.py:30-32`).
- Do not modify `oeapp/ui/full_translation_window.py`'s own `SIDEBAR_WIDTH` (`:842`) — it is a separate constant on a separate class.

---

## File Structure

| File | Responsibility | Tasks |
|---|---|---|
| `oeapp/ui/theming.py` (new) | Single source of truth for resolving + applying a theme at runtime | 1 |
| `oeapp/ui/application.py` | Startup theme application — delegates to `theming.py` | 1 |
| `oeapp/ui/dialogs/settings.py` | Settings dialog; applies theme live instead of demanding restart | 2 |
| `oeapp/ui/dialogs/help_center_dialog.py` | Re-applies its own CSS on live theme change | 2 |
| `oeapp/ui/main_window.py` | Error severity, empty-state CSS typo, nav button tooltips, resizable sidebar | 3, 4, 5 |
| `Makefile` | Help artifact rebuild correctness | 6 |
| `tests/test_theming.py` (new) | Tests for the theming helper | 1 |
| `tests/test_settings_dialog.py` | Tests for live theme application | 2 |
| `tests/test_main_window.py` | Tests for error severity, tooltips, splitter | 3, 4, 5 |

---

### Task 1: Extract a single theme-resolution/application helper

**Why:** The `"dark"→"nord"` mapping is currently duplicated — inline at `oeapp/ui/application.py:30-34` and as `SettingsDialog.THEMES` at `oeapp/ui/dialogs/settings.py:30-32`. Live switching (Task 2) needs one shared entry point. There is also a latent bug: `settings.py:86` reads the stored theme with default `"nord"`, while `:169` and `:211` use default `"dark"` — `"nord"` is not a valid combo value.

**Files:**
- Create: `oeapp/ui/theming.py`
- Create: `tests/test_theming.py`
- Modify: `oeapp/ui/application.py:29-33`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `THEMES: Final[dict[str, str]]` — `{"dark": "nord", "light": "modern_light"}`
  - `resolve_theme_name(stored: str) -> str` — maps a stored settings value to a `qt_themes` name; returns the `qt_themes` name unchanged if it is already one; falls back to `"nord"` for unknown input.
  - `apply_theme(stored: str) -> str` — resolves then calls `qt_themes.set_theme(...)`; returns the resolved name.

- [ ] **Step 1: Write the failing test**

Create `tests/test_theming.py`:

```python
"""Unit tests for theme resolution and application."""

from unittest.mock import patch

from oeapp.ui.theming import THEMES, apply_theme, resolve_theme_name


class TestResolveThemeName:
    """Test cases for resolve_theme_name."""

    def test_maps_user_facing_names_to_qt_themes_names(self):
        """User-facing setting values map to qt_themes theme names."""
        assert resolve_theme_name("dark") == "nord"
        assert resolve_theme_name("light") == "modern_light"

    def test_passes_through_qt_themes_names_unchanged(self):
        """An already-resolved qt_themes name is returned as-is."""
        assert resolve_theme_name("nord") == "nord"
        assert resolve_theme_name("modern_light") == "modern_light"

    def test_falls_back_to_nord_for_unknown_value(self):
        """An unrecognized stored value falls back to the default theme."""
        assert resolve_theme_name("chartreuse") == "nord"

    def test_themes_mapping_covers_both_user_facing_values(self):
        """THEMES exposes exactly the two user-selectable themes."""
        assert THEMES == {"dark": "nord", "light": "modern_light"}


class TestApplyTheme:
    """Test cases for apply_theme."""

    def test_calls_qt_themes_set_theme_with_resolved_name(self):
        """apply_theme resolves the name before handing it to qt_themes."""
        with patch("oeapp.ui.theming.qt_themes.set_theme") as mock_set_theme:
            result = apply_theme("light")

        mock_set_theme.assert_called_once_with("modern_light")
        assert result == "modern_light"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_theming.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'oeapp.ui.theming'`

- [ ] **Step 3: Write minimal implementation**

Create `oeapp/ui/theming.py`:

```python
"""Single source of truth for resolving and applying application themes."""

from __future__ import annotations

from typing import Final

import qt_themes

#: Map of user-facing setting values to ``qt_themes`` theme names.
THEMES: Final[dict[str, str]] = {
    "dark": "nord",
    "light": "modern_light",
}

#: Theme applied when the stored setting value is unrecognized.
DEFAULT_THEME: Final[str] = "nord"


def resolve_theme_name(stored: str) -> str:
    """
    Resolve a stored settings value to a ``qt_themes`` theme name.

    Accepts either a user-facing value (``"dark"``/``"light"``) or an
    already-resolved ``qt_themes`` name, so callers need not know which form
    was persisted.

    Args:
        stored: Value read from ``QSettings`` under ``theme/name``.

    Returns:
        A ``qt_themes`` theme name.

    """
    if stored in THEMES:
        return THEMES[stored]
    if stored in THEMES.values():
        return stored
    return DEFAULT_THEME


def apply_theme(stored: str) -> str:
    """
    Apply a theme to the running application.

    Safe to call after startup: ``qt_themes.set_theme`` sets the application
    palette, which Qt propagates to existing widgets.

    Args:
        stored: Value read from ``QSettings`` under ``theme/name``.

    Returns:
        The ``qt_themes`` theme name that was applied.

    """
    resolved = resolve_theme_name(stored)
    qt_themes.set_theme(resolved)
    return resolved
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_theming.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Switch application startup to the helper**

In `oeapp/ui/application.py`, replace these lines (currently at `:29-33`):

```python
    settings = QSettings()
    theme = settings.value("theme/name", "dark", type=str)
    if theme == "dark":
        theme = "nord"
    elif theme == "light":
        theme = "modern_light"
    qt_themes.set_theme(theme)
```

with:

```python
    settings = QSettings()
    apply_theme(settings.value("theme/name", "dark", type=str))
```

Update the imports at the top of the file: remove `import qt_themes` (no longer used there — verify with a search before deleting) and add:

```python
from .theming import apply_theme
```

- [ ] **Step 6: Verify startup path still works**

Run: `.venv/bin/python -m pytest tests/ -q -p no:randomly 2>&1 | tail -3`
Expected: 316 passed, 1 skipped, 1 failed (the known pre-existing `test_export_pdf` failure)

Run: `make napoleon-gate`
Expected: no new violations

- [ ] **Step 7: Commit**

```bash
git add oeapp/ui/theming.py tests/test_theming.py oeapp/ui/application.py
git commit -m "refactor: extract single theme resolution/application helper"
```

---

### Task 2: Apply theme changes live instead of demanding a restart

**Why:** ADR D5. `SettingsDialog._on_theme_changed` (`oeapp/ui/dialogs/settings.py:176-197`) only pops a "quit and restart" `QMessageBox`; `qt_themes.set_theme()` is never called again after boot. This is a manufactured limitation.

**Files:**
- Modify: `oeapp/ui/dialogs/settings.py:30-32` (drop local `THEMES`), `:86`, `:163-197`, `:207-212`
- Modify: `oeapp/ui/dialogs/help_center_dialog.py` (re-apply CSS on live change)
- Test: `tests/test_settings_dialog.py`

**Interfaces:**
- Consumes: `apply_theme(stored: str) -> str` and `THEMES` from `oeapp/ui/theming.py` (Task 1).
- Produces: `SettingsDialog._on_theme_changed()` now applies the theme rather than showing a restart dialog.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_settings_dialog.py`:

```python
class TestSettingsDialogThemeSwitching:
    """Test cases for live theme switching."""

    def test_theme_change_applies_theme_immediately(
        self, db_session, mock_main_window, qapp
    ):
        """Changing the theme applies it live, without requiring a restart."""
        dialog = SettingsDialog(mock_main_window)
        dialog.build()
        dialog.settings.setValue("theme/name", "dark")
        dialog.theme_combo.setCurrentText("light")

        with patch("oeapp.ui.dialogs.settings.apply_theme") as mock_apply:
            dialog._on_theme_changed()

        mock_apply.assert_called_once_with("light")

    def test_theme_change_shows_no_restart_dialog(
        self, db_session, mock_main_window, qapp
    ):
        """The obsolete 'quit and restart' message box is not shown."""
        dialog = SettingsDialog(mock_main_window)
        dialog.build()
        dialog.theme_combo.setCurrentText("light")

        with (
            patch("oeapp.ui.dialogs.settings.apply_theme"),
            patch("oeapp.ui.dialogs.settings.QMessageBox") as mock_msg_box,
        ):
            dialog._on_theme_changed()

        mock_msg_box.assert_not_called()

    def test_get_theme_returns_qt_themes_name(
        self, db_session, mock_main_window, qapp
    ):
        """get_theme resolves the stored value to a qt_themes theme name."""
        dialog = SettingsDialog(mock_main_window)
        dialog.settings.setValue("theme/name", "light")

        assert dialog.get_theme() == "modern_light"
```

Add to the imports at the top of `tests/test_settings_dialog.py`:

```python
from unittest.mock import patch
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_settings_dialog.py -v -k Theme`
Expected: FAIL — `AttributeError: <module 'oeapp.ui.dialogs.settings'> does not have the attribute 'apply_theme'`

- [ ] **Step 3: Rewrite `_on_theme_changed` to apply the theme**

In `oeapp/ui/dialogs/settings.py`, replace the whole `_on_theme_changed` method (currently `:176-197`) with:

```python
    def _on_theme_changed(self) -> None:
        """
        Apply the newly selected theme to the running application.

        ``qt_themes.set_theme`` sets the application palette, which Qt
        propagates to already-constructed widgets, so no restart is needed.

        Returns:
            None

        """
        apply_theme(self.theme_combo.currentText())
        self.main_window.refresh_theme_dependent_widgets()
```

- [ ] **Step 4: Delete the now-duplicated THEMES map and fix the mismatched default**

In `oeapp/ui/dialogs/settings.py`:

Delete the class attribute at `:29-32`:

```python
    #: Themes
    THEMES: Final[dict[str, str]] = {
        "dark": "nord",
        "light": "modern_light",
    }
```

Change `:86` from:

```python
        theme = self.get_str_value("theme/name", "nord")
```

to (`"nord"` is not a valid combo value — the combo offers `"dark"`/`"light"`):

```python
        theme = self.get_str_value("theme/name", "dark")
```

Replace `get_theme` (`:207-212`) with:

```python
    def get_theme(self) -> str:
        """
        Get the ``qt_themes`` theme name for the stored theme setting.

        Returns:
            The ``qt_themes`` theme name.

        """
        return resolve_theme_name(self.get_str_value("theme/name", "dark"))
```

Update imports at the top of the file — add:

```python
from oeapp.ui.theming import apply_theme, resolve_theme_name
```

Then check whether `Final` and `QMessageBox` are still used anywhere in the file; remove them from the imports only if they are not. Verify with:

```bash
grep -n "Final\|QMessageBox" oeapp/ui/dialogs/settings.py
```

- [ ] **Step 5: Add the main-window refresh hook**

In `oeapp/ui/main_window.py`, add this method to the `MainWindow` class (place it next to the other public helper methods):

```python
    def refresh_theme_dependent_widgets(self) -> None:
        """
        Re-apply styling that does not follow the application palette.

        Most widgets restyle automatically when the palette changes, but the
        help center renders its own CSS into a ``QTextBrowser`` at construction
        time and must be told to re-render.

        Returns:
            None

        """
        if self.help_center_dialog is not None:
            self.help_center_dialog.refresh_theme()
```

Before writing this, confirm the attribute name that holds the open help center dialog:

```bash
grep -n "help_center" oeapp/ui/main_window.py
```

Use the actual attribute name found there. If the dialog is not retained on the window, store it on the instance when it is created (around `main_window.py:610-630`) so it can be refreshed.

- [ ] **Step 6: Add `refresh_theme` to the help center dialog**

In `oeapp/ui/dialogs/help_center_dialog.py`, find where `_theme_override_css` is applied (around `:171`) and factor that application into a public method:

```python
    def refresh_theme(self) -> None:
        """
        Re-apply theme-derived CSS to the help browser.

        Called when the application theme changes while this dialog is open,
        since the browser's CSS is rendered once at construction time and does
        not follow the application palette.

        Returns:
            None

        """
        self.browser.document().setDefaultStyleSheet(self._theme_override_css())
        self.browser.reload()
```

Match the actual attribute name for the browser and the actual call used at `:171` — read that region first and mirror it rather than assuming. If the existing code sets the CSS by a different mechanism, use the same mechanism here.

- [ ] **Step 7: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_settings_dialog.py tests/test_help_center_dialog.py tests/test_main_window.py -v`
Expected: PASS

- [ ] **Step 8: Manually verify the live switch**

Run: `make dev`

Then, in the running app:
1. Open Preferences, change Theme from dark to light, click OK. The main window must restyle immediately, with no restart prompt.
2. With the Help Center open, change the theme again. The help content must restyle too.
3. Open an annotation modal, change the theme. Confirm no panel is left visibly stale.

If any panel stays stale, note exactly which widget in the commit message — ADR D5 flags this as the known risk (widgets caching `ThemeMixin.theme_base_color`/`is_dark_theme` results at `__init__`). Fixing those specific widgets is in scope for this task.

- [ ] **Step 9: Commit**

```bash
git add oeapp/ui/dialogs/settings.py oeapp/ui/dialogs/help_center_dialog.py oeapp/ui/main_window.py tests/test_settings_dialog.py
git commit -m "feat: apply theme changes live instead of requiring a restart"
```

---

### Task 3: Fix the two confirmed one-line UI bugs

**Why:** ADR D4 items confirmed by direct read. `show_error` uses the warning icon so users cannot distinguish an error from a warning; the empty-state label's colour rule silently no-ops on a misspelled `pallete`.

**Files:**
- Modify: `oeapp/ui/main_window.py:411`, `oeapp/ui/main_window.py:1437`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing new — behaviour fix only.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_main_window.py` (match the file's existing import style and add `from unittest.mock import patch` if absent):

```python
class TestMessagesSeverity:
    """Test cases for error/warning message severity."""

    def test_show_error_uses_critical_severity(self, db_session, mock_main_window, qapp):
        """show_error renders with the critical icon, not the warning icon."""
        messages = Messages(mock_main_window)

        with patch("oeapp.ui.main_window.QMessageBox.critical") as mock_critical:
            messages.show_error("disk on fire")

        mock_critical.assert_called_once()


class TestEmptyStateStyling:
    """Test cases for the welcome/empty-state label styling."""

    def test_welcome_label_stylesheet_uses_valid_palette_function(self):
        """The empty-state stylesheet uses palette(), not the misspelled pallete()."""
        source = Path("oeapp/ui/main_window.py").read_text(encoding="utf-8")

        assert "pallete(" not in source
```

Add to the imports of `tests/test_main_window.py` as needed:

```python
from pathlib import Path
from unittest.mock import patch

from oeapp.ui.main_window import Messages
```

Confirm the real class name that owns `show_error` before writing this — read `oeapp/ui/main_window.py:1424-1440` and use the actual class and constructor signature.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_main_window.py -v -k "Severity or EmptyState"`
Expected: FAIL — `mock_critical` not called (still calls `warning`), and `pallete(` found in source

- [ ] **Step 3: Fix both lines**

In `oeapp/ui/main_window.py:411`, change:

```python
            "font-size: 14pt; color: pallete(text-muted); padding: 50px;"
```

to:

```python
            "font-size: 14pt; color: palette(text); padding: 50px;"
```

(`text-muted` is not a Qt palette role; `text` is. Qt's palette functions accept role names like `text`, `window`, `base`, `highlight`.)

In `oeapp/ui/main_window.py:1437`, change:

```python
        QMessageBox.warning(self.main_window, title, message)
```

to:

```python
        QMessageBox.critical(self.main_window, title, message)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_main_window.py -v -k "Severity or EmptyState"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/main_window.py tests/test_main_window.py
git commit -m "fix: use critical severity for errors and correct palette() typo"
```

---

### Task 4: Add tooltips and accessible names to icon-only navigation buttons

**Why:** ADR D4. The four glyph-only `<`/`>` chapter and section buttons (`oeapp/ui/main_window.py:278-310`) carry no tooltip and no accessible name — only 2 `setToolTip()` calls exist in the entire `oeapp/ui/` tree.

**Files:**
- Modify: `oeapp/ui/main_window.py:278-310`
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: nothing.
- Produces: nothing new — the four buttons gain `toolTip()` and `accessibleName()` values.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_main_window.py`:

```python
class TestNavigationButtonAffordances:
    """Test cases for chapter/section navigation button discoverability."""

    def test_navigation_buttons_have_tooltips_and_accessible_names(
        self, db_session, mock_main_window, qapp
    ):
        """Every glyph-only nav button exposes a tooltip and an accessible name."""
        expected = {
            "chapter_prev_button": "Previous chapter",
            "chapter_next_button": "Next chapter",
            "section_prev_button": "Previous section",
            "section_next_button": "Next section",
        }

        for attribute, label in expected.items():
            button = getattr(mock_main_window, attribute)
            assert button.toolTip() == label
            assert button.accessibleName() == label
```

If `mock_main_window` does not build the navigation toolbar, construct the real `MainWindow` in the test instead, or call `build_navigation_toolbar` directly — read `tests/conftest.py:156` and the existing `tests/test_main_window.py` cases to see which pattern this suite already uses, and follow it.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_main_window.py -v -k NavigationButtonAffordances`
Expected: FAIL — `assert '' == 'Previous chapter'`

- [ ] **Step 3: Add the tooltips and accessible names**

In `oeapp/ui/main_window.py`, in `build_navigation_toolbar`, add two lines after each of the four button constructions. For the chapter previous button (currently `:278-280`):

```python
        self.chapter_prev_button = QPushButton("<")
        self.chapter_prev_button.setFixedWidth(30)
        self.chapter_prev_button.setToolTip("Previous chapter")
        self.chapter_prev_button.setAccessibleName("Previous chapter")
        self.chapter_prev_button.clicked.connect(self._on_prev_chapter_clicked)
```

For the chapter next button:

```python
        self.chapter_next_button = QPushButton(">")
        self.chapter_next_button.setFixedWidth(30)
        self.chapter_next_button.setToolTip("Next chapter")
        self.chapter_next_button.setAccessibleName("Next chapter")
        self.chapter_next_button.clicked.connect(self._on_next_chapter_clicked)
```

For the section previous button:

```python
        self.section_prev_button = QPushButton("<")
        self.section_prev_button.setFixedWidth(30)
        self.section_prev_button.setToolTip("Previous section")
        self.section_prev_button.setAccessibleName("Previous section")
        self.section_prev_button.clicked.connect(self._on_prev_section_clicked)
```

For the section next button:

```python
        self.section_next_button = QPushButton(">")
        self.section_next_button.setFixedWidth(30)
        self.section_next_button.setToolTip("Next section")
        self.section_next_button.setAccessibleName("Next section")
        self.section_next_button.clicked.connect(self._on_next_section_clicked)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_main_window.py -v -k NavigationButtonAffordances`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/main_window.py tests/test_main_window.py
git commit -m "feat: add tooltips and accessible names to navigation buttons"
```

---

### Task 5: Make the token details sidebar resizable

**Why:** ADR D4. The sidebar is pinned at `SIDEBAR_WIDTH = 350` via `setFixedWidth` (`oeapp/ui/main_window.py:466`) with no `QSplitter` anywhere in the main window, so the user cannot trade space between the sentence column and the annotation sidebar.

**Blast radius (already checked):** `SIDEBAR_WIDTH` appears at `oeapp/ui/main_window.py:76,466` and `oeapp/ui/full_translation_window.py:842,1227,1230`. The latter is a separate constant on a separate class — **do not touch it**.

**Files:**
- Modify: `oeapp/ui/main_window.py:141-184` (`build_main_window`), `:452-469` (`build_sidebar_area`)
- Test: `tests/test_main_window.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `MainWindow.main_splitter: QSplitter` — the splitter holding the content column and the sidebar.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_main_window.py`:

```python
class TestSidebarResizing:
    """Test cases for the resizable token details sidebar."""

    def test_sidebar_lives_in_a_splitter(self, db_session, mock_main_window, qapp):
        """The sidebar and content column share a user-draggable splitter."""
        assert isinstance(mock_main_window.main_splitter, QSplitter)
        assert mock_main_window.main_splitter.count() == 2

    def test_sidebar_is_not_fixed_width(self, db_session, mock_main_window, qapp):
        """The sidebar can be resized: its min and max widths are not pinned equal."""
        sidebar = mock_main_window.sidebar

        assert sidebar.minimumWidth() != sidebar.maximumWidth()

    def test_sidebar_starts_at_default_width(self, db_session, mock_main_window, qapp):
        """The sidebar still opens at its established default width."""
        assert mock_main_window.main_splitter.sizes()[1] == MainWindow.SIDEBAR_WIDTH
```

Add to the imports of `tests/test_main_window.py`:

```python
from PySide6.QtWidgets import QSplitter
```

Use whatever attribute name the window already uses for the sidebar — check with `grep -n "self.sidebar" oeapp/ui/main_window.py` and adjust the test to match.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_main_window.py -v -k SidebarResizing`
Expected: FAIL — `AttributeError: 'MainWindow' object has no attribute 'main_splitter'`

- [ ] **Step 3: Replace the fixed-width layout with a splitter**

In `oeapp/ui/main_window.py`, change `build_sidebar_area` (`:452-469`) so it no longer pins the width and no longer adds itself to the parent layout:

```python
    def build_sidebar_area(self) -> TokenDetailsSidebar:
        """
        Build the token details sidebar.

        The sidebar is sized by the enclosing splitter rather than pinned to a
        fixed width, so the user can trade space with the sentence column.

        Returns:
            The token details sidebar widget.

        """
        sidebar = TokenDetailsSidebar()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(200)
        sidebar.setStyleSheet(self.SIDEBAR_STYLE)
        return sidebar
```

Then, in `build_main_window`, wrap the content column and the sidebar in a `QSplitter` instead of adding both to the `QHBoxLayout` directly. Read `:141-184` first, then replace the part that builds `column_container` and calls `build_sidebar_area(...)` with:

```python
        content_column = QWidget()
        content_column.setLayout(column_layout)

        self.sidebar = self.build_sidebar_area()

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(content_column)
        self.main_splitter.addWidget(self.sidebar)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 0)
        self.main_splitter.setSizes([
            self.WINDOW_WIDTH - self.SIDEBAR_WIDTH,
            self.SIDEBAR_WIDTH,
        ])
        main_layout.addWidget(self.main_splitter)
```

Adapt the surrounding variable names to whatever `build_main_window` actually uses — read the method before editing rather than assuming `column_layout`/`main_layout`. If there is no `WINDOW_WIDTH` constant on the class, use the window's current width or a literal that matches the existing default window size.

Add to the imports at the top of `oeapp/ui/main_window.py`:

```python
from PySide6.QtWidgets import QSplitter
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_main_window.py -v -k SidebarResizing`
Expected: PASS

- [ ] **Step 5: Verify the full suite and the real window**

Run: `.venv/bin/python -m pytest tests/ -q -p no:randomly 2>&1 | tail -3`
Expected: no regressions against the baseline

Run: `make dev` — confirm the splitter handle is draggable, the sidebar starts at its usual width, and the sentence cards still lay out correctly at both extremes.

- [ ] **Step 6: Commit**

```bash
git add oeapp/ui/main_window.py tests/test_main_window.py
git commit -m "feat: make token details sidebar resizable via splitter"
```

---

### Task 6: Fix the help-artifact rebuild rule's known defects

**Why:** ADR D2. The Make rule tracks only `.qch`, so deleting `.qhc` alone leaves the app raising `HelpEngineError` while `make` refuses to rebuild. `$(wildcard)` also cannot detect a *deleted* topic, so removing a topic ships stale help.

**Files:**
- Modify: `Makefile` (the `HELP_*` variables and the `$(HELP_QCH)` rule)

**Interfaces:**
- Consumes: nothing.
- Produces: nothing consumed by other tasks.

- [ ] **Step 1: Write the check (shell, not pytest — this is build tooling)**

Create `scripts/check_help_rebuild.sh`:

```bash
#!/usr/bin/env bash
# Verify the help-asset Make rule rebuilds when it should and skips when it shouldn't.
set -euo pipefail

QCH="oeapp/help/assets/aenglisc_toolkit_help.qch"
QHC="oeapp/help/assets/aenglisc_toolkit_help.qhc"

make help-assets >/dev/null

# 1. Unchanged sources: must not rebuild.
if ! make -q help-assets; then
    echo "FAIL: rebuild triggered with unchanged sources"
    exit 1
fi

# 2. Missing .qhc: must rebuild.
rm -f "$QHC"
if make -q help-assets; then
    echo "FAIL: no rebuild triggered when $QHC was missing"
    exit 1
fi

make help-assets >/dev/null
test -f "$QHC" || { echo "FAIL: $QHC not regenerated"; exit 1; }
test -f "$QCH" || { echo "FAIL: $QCH not regenerated"; exit 1; }

# 3. Changed topic: must rebuild.
touch oeapp/help/topics/*.md
if make -q help-assets; then
    echo "FAIL: no rebuild triggered after touching a topic"
    exit 1
fi

make help-assets >/dev/null
echo "PASS: help rebuild rule behaves correctly"
```

Make it executable:

```bash
chmod +x scripts/check_help_rebuild.sh
```

- [ ] **Step 2: Run the check to verify it fails**

Run: `./scripts/check_help_rebuild.sh`
Expected: `FAIL: no rebuild triggered when oeapp/help/assets/aenglisc_toolkit_help.qhc was missing`

- [ ] **Step 3: Make the rule track both artifacts and detect deleted topics**

In `Makefile`, replace the current help block:

```makefile
HELP_TOPICS_DIR := oeapp/help/topics
HELP_QCH := oeapp/help/assets/aenglisc_toolkit_help.qch
HELP_SOURCES := $(wildcard $(HELP_TOPICS_DIR)/*.md) scripts/build_help.py oeapp/help/topics.py

$(HELP_QCH): $(HELP_SOURCES)
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python scripts/build_help.py; \
	else \
		python scripts/build_help.py; \
	fi

help-assets:: $(HELP_QCH) ## Build QtHelp assets from markdown help topics (skipped if already up to date).
```

with:

```makefile
HELP_TOPICS_DIR := oeapp/help/topics
HELP_ASSETS_DIR := oeapp/help/assets
HELP_QCH := $(HELP_ASSETS_DIR)/aenglisc_toolkit_help.qch
HELP_QHC := $(HELP_ASSETS_DIR)/aenglisc_toolkit_help.qhc
HELP_TOPIC_SOURCES := $(wildcard $(HELP_TOPICS_DIR)/*.md)
HELP_SOURCES := $(HELP_TOPIC_SOURCES) scripts/build_help.py oeapp/help/topics.py
# A deleted topic shrinks the wildcard without touching any surviving file, so
# mtime comparison alone would miss it. Encode the topic list as a hash in a
# marker filename: delete or add a topic and the marker no longer exists, which
# makes it newer than the artifacts and forces one rebuild. When the list is
# unchanged the marker already exists and is old, so nothing rebuilds.
HELP_TOPICS_HASH := $(shell ls $(HELP_TOPICS_DIR)/*.md 2>/dev/null | shasum | cut -c1-12)
HELP_MARKER := $(HELP_ASSETS_DIR)/.topics-$(HELP_TOPICS_HASH)

$(HELP_MARKER):
	@mkdir -p $(HELP_ASSETS_DIR)
	@rm -f $(HELP_ASSETS_DIR)/.topics-*
	@touch $@

# GNU Make 3.81 (what macOS ships) has no grouped-target `&:` syntax, so the
# recipe is defined once and attached to both artifacts.
# ponytail: if both artifacts are stale at once the build runs twice; harmless,
# and cheaper than a stamp file that would reintroduce the missing-.qhc bug.
define build_help
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python scripts/build_help.py; \
	else \
		python scripts/build_help.py; \
	fi
endef

$(HELP_QCH): $(HELP_SOURCES) $(HELP_MARKER)
	$(build_help)

$(HELP_QHC): $(HELP_SOURCES) $(HELP_MARKER)
	$(build_help)

help-assets:: $(HELP_QCH) $(HELP_QHC) ## Build QtHelp assets from markdown help topics (skipped if already up to date).
```

Notes for the implementer:
- **Do not make the marker `.PHONY`.** A phony prerequisite forces every dependent to rebuild on every run, which would silently undo the whole point of this rule. The hashed-filename trick achieves change detection without phoniness.
- This repo has GNU Make 3.81 (verified). Do not use `&:`, `.ONESHELL`, or other Make 4.x features.

- [ ] **Step 4: Run the check to verify it passes**

Run: `./scripts/check_help_rebuild.sh`
Expected: `PASS: help rebuild rule behaves correctly`

- [ ] **Step 5: Verify deleted-topic detection by hand**

```bash
make help-assets
cp oeapp/help/topics/start-here.md /tmp/start-here.md.bak
rm oeapp/help/topics/start-here.md
make -q help-assets; echo "exit=$? (expected non-zero: rebuild needed)"
cp /tmp/start-here.md.bak oeapp/help/topics/start-here.md
make help-assets
```

Adjust the filename if `start-here.md` is not present — list the directory first.

- [ ] **Step 6: Add the manifest to .gitignore**

Append to `.gitignore`:

```
oeapp/help/assets/.topics-manifest
```

- [ ] **Step 7: Commit**

```bash
git add Makefile scripts/check_help_rebuild.sh .gitignore
git commit -m "fix: track both help artifacts and detect deleted topics in rebuild rule"
```

---

## Out of scope for this plan

These ADR items are deliberately excluded, with the reason:

- **D3 (tectonic/spec slimming)** — blocked on measuring a real built `.app`. Planning an edit against an unmeasured target is how the original misdiagnosis happened. Needs its own plan after the audit.
- **D3a (ML dependency bloat)** — blocked upstream in `wyrdcraeft` (`cmalek/oe_json_extractor`); not fixable in this repo.
- **D4 item 4 (60-site `setStyleSheet` migration)** — deferred behind a visual regression safety net, per the ADR. Do not start it as part of these tasks.
- **D4 item 3 (non-modal log viewer / backups view, and deleting the dead `oeapp/themes/default.qss`)** — small and safe, but independent of everything here. The `.qss` file is loaded nowhere (verified: no `.qss` reference in any Python source); deleting it is a one-line change best done alongside the stylesheet consolidation in D4 item 4, so the deletion and the migration are reviewed together. Fold into a follow-up plan, or add as a seventh task if desired.
- **D2 startup cost (`ensure_runtime_help_assets` SHA-256 hashing on every launch)** — needs a measurement of actual startup cost before optimizing.

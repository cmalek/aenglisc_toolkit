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

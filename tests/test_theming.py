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

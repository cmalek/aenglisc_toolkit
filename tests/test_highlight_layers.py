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

        card.oe_text_edit.document().setPlainText("ing ing ing")
        assert selection_ranges(layers.compose()) == [(6, 9)]  # stale on purpose

        layers.invalidate_search_cache()
        assert selection_ranges(layers.compose()) == [(0, 3), (4, 7), (8, 11)]

    def test_clear_layer_removes_pattern_too(self, card):
        layers = HighlightLayers(card.oe_text_edit)
        layers.set_search_pattern("ing")
        layers.clear_layer(HighlightLayer.SEARCH)

        assert layers.compose() == []

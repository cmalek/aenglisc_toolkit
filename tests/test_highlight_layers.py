import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QLineEdit, QTextEdit
from PySide6.QtWidgets import QTextEdit as PlainTextEdit

from oeapp.commands import CommandManager
from oeapp.models.annotation import Annotation
from oeapp.models.idiom import Idiom
from oeapp.ui.dialogs.sentence_filters import SentenceFilterDialog
from oeapp.ui.full_translation_window import FullProjectOldEnglishTextEdit
from oeapp.ui.highlight_layers import (
    SEARCH_STYLE,
    HighlightEntry,
    HighlightLayer,
    HighlightLayers,
    HighlightStyle,
)
from oeapp.ui.highlighting import SearchHighlighter
from oeapp.ui.search_controller import normalized_oe_query
from oeapp.ui.mixins import AnnotationLookupsMixin
from oeapp.ui.oe_text_edit import OldEnglishTextEdit
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

    def test_save_with_retokenize_reresolves_search_at_new_offsets(
        self, card, search_ui
    ):
        """Saving a split re-runs the search against the new tokens."""
        edit = card.oe_text_edit
        search_ui.search_input.setText("cyn")
        search_ui.search_scope_combo.setCurrentText("OE Text")
        card.sentence_highlighter.build_combo_box()
        card.highlight_search("cyn", "OE Text", normalized_oe_query("cyn", "OE Text"), None)
        assert selection_ranges(edit.extraSelections()) == [(3, 9)]

        card._on_edit_oe_clicked()
        assert edit.extraSelections() == []
        edit.setPlainText("Se cyn ing")
        card._on_save_oe_clicked()

        assert not edit.in_edit_mode
        assert selection_ranges(edit.extraSelections()) == [(3, 6)]

    def test_cancel_edit_restores_search_at_original_offsets(self, card, search_ui):
        edit = card.oe_text_edit
        search_ui.search_scope_combo.setCurrentText("OE Text")
        card.sentence_highlighter.build_combo_box()
        card.highlight_search("cyning", "OE Text", "cyning", None)
        assert selection_ranges(edit.extraSelections()) == [(3, 9)]

        card._on_edit_oe_clicked()
        edit.setPlainText("Se cyn ing")
        card._on_cancel_edit_clicked()

        assert not edit.in_edit_mode
        assert selection_ranges(edit.extraSelections()) == [(3, 9)]

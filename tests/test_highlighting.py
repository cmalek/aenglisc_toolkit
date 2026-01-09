import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QComboBox, QTextEdit
from unittest.mock import MagicMock, patch

from oeapp.models.annotation import Annotation
from oeapp.models.token import Token
from oeapp.ui.highlighting import (
    SentenceHighligher,
    POSHighligherCommand,
    CaseHighligherCommand,
    NumberHighligherCommand,
    IdiomHighligherCommand,
    NoneHighligherCommand,
)
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.dialogs.sentence_filters import SentenceFilterDialog
from tests.conftest import create_test_project, create_test_token, create_test_sentence


class TestHighlighting:
    @pytest.fixture(autouse=True)
    def patch_dialog_exec(self, monkeypatch):
        """Patch SentenceFilterDialog.exec to show() so it doesn't block tests."""
        monkeypatch.setattr(SentenceFilterDialog, "exec", lambda self: self.show())

    @pytest.fixture
    def card(self, db_session, qapp, qtbot):
        project = create_test_project(db_session, name="Test Highlighting", text="Se cyning fēoll.")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)
        qtbot.addWidget(card)
        return card

    @pytest.fixture
    def highlighter(self, card):
        return card.highligher

    def test_highlighter_initialization(self, highlighter, card):
        """Test that SentenceHighligher initializes correctly."""
        assert highlighter.card == card
        assert len(highlighter.tokens) == 3
        assert highlighter.active_command is None
        assert isinstance(highlighter.item_selections, dict)
        # Should have selections for POS, Case, Number (those with FILTER_DIALOG_CLASS)
        assert len(highlighter.item_selections) == 3

    def test_build_combo_box(self, highlighter):
        """Test that build_combo_box creates a valid QComboBox."""
        combo = highlighter.build_combo_box()
        assert isinstance(combo, QComboBox)
        assert combo.count() == len(highlighter.HIGHLIGHTERS)
        assert combo.itemText(0) == "None"
        assert combo.itemText(1) == "Part of Speech"

    def test_on_highlighting_changed(self, highlighter, qtbot):
        """Test switching highlighting modes via combo box."""
        combo = highlighter.build_combo_box()

        # Switch to POS
        with qtbot.waitSignal(combo.currentIndexChanged):
            combo.setCurrentIndex(1)

        assert isinstance(highlighter.active_command, POSHighligherCommand)
        pos_dialog = highlighter.active_command.dialog
        assert pos_dialog is not None
        assert pos_dialog.isVisible()

        # Switch to None
        with qtbot.waitSignal(combo.currentIndexChanged):
            combo.setCurrentIndex(0)

        assert isinstance(highlighter.active_command, NoneHighligherCommand)
        # Previous dialog should be hidden
        assert not pos_dialog.isVisible()

    def test_pos_highlighter_get_value(self, highlighter):
        """Test POSHighligherCommand value extraction."""
        command = POSHighligherCommand(highlighter)
        annotation = Annotation(pos="N")
        assert command.get_value(annotation) == "N"

        annotation.pos = "V"
        assert command.get_value(annotation) == "V"

    def test_case_highlighter_get_value(self, highlighter):
        """Test CaseHighligherCommand value extraction."""
        command = CaseHighligherCommand(highlighter)

        # Noun with nominative case
        annotation = Annotation(pos="N", case="n")
        assert command.get_value(annotation) == "n"

        # Preposition with dative case
        annotation = Annotation(pos="E", prep_case="d")
        assert command.get_value(annotation) == "d"

        # Verb should not be highlighted for case
        annotation = Annotation(pos="V", case="n")
        assert command.get_value(annotation) is None

    def test_number_highlighter_get_value(self, highlighter):
        """Test NumberHighligherCommand value extraction."""
        command = NumberHighligherCommand(highlighter)

        # Noun with singular
        annotation = Annotation(pos="N", number="s")
        assert command.get_value(annotation) == "s"

        # Pronoun with plural (using pronoun_number)
        annotation = Annotation(pos="R", pronoun_number="pl")
        assert command.get_value(annotation) == "pl"

        # Preposition should not be highlighted for number
        annotation = Annotation(pos="E", number="s")
        assert command.get_value(annotation) is None

    def test_filter_selection_persistence(self, highlighter, qtbot):
        """Test that filter selections are saved when switching modes."""
        combo = highlighter.build_combo_box()

        # 1. Switch to POS
        combo.setCurrentIndex(1)
        pos_command = highlighter.active_command

        # Modify POS filter: deselect some items
        new_selection = {"V", "A"}
        pos_command.dialog.set_selected_items(new_selection)

        # 2. Switch to Case
        combo.setCurrentIndex(2)
        # Check that POS selection was saved in item_selections
        assert highlighter.item_selections[1] == new_selection

        # 3. Switch back to POS
        combo.setCurrentIndex(1)
        # Check that it was restored to the command
        assert highlighter.active_command.filter_selection == new_selection

    def test_highlight_application(self, highlighter, card, db_session):
        """Test that highlight() actually applies extra selections to the text edit."""
        # Setup tokens with annotations
        tokens = card.tokens
        # Token ids are assigned when saved
        db_session.add_all(tokens)
        db_session.commit()

        tokens[0].annotation = Annotation(token_id=tokens[0].id, pos="D", case="n", number="s")
        tokens[1].annotation = Annotation(token_id=tokens[1].id, pos="N", case="n", number="s")
        db_session.commit()

        # Update highlighter's reference to annotations
        highlighter.annotations = {t.id: t.annotation for t in tokens if t.id}

        # Switch to POS highlighting
        combo = highlighter.build_combo_box()
        combo.setCurrentIndex(1) # POS

        # Check if extra selections are set on the text edit
        selections = card.oe_text_edit.extraSelections()
        # "Se" (D) and "cyning" (N) should be highlighted
        assert len(selections) >= 2

    def test_idiom_highlighting(self, card, db_session, highlighter):
        """Test idiom highlighting logic."""
        from oeapp.models.idiom import Idiom

        tokens = card.tokens
        db_session.add_all(tokens)
        db_session.commit()

        idiom = Idiom(
            sentence_id=card.sentence.id,
            start_token_id=tokens[0].id,
            end_token_id=tokens[1].id
        )
        idiom.start_token = tokens[0]
        idiom.end_token = tokens[1]
        card.idioms = [idiom]
        highlighter.idioms = [idiom]

        command = IdiomHighligherCommand(highlighter)

        # Mock set_highlights to see if it gets called with correct number of selections
        with patch.object(highlighter, 'set_highlights') as mock_set:
            command.highlight()
            # Should have called set_highlights with 2 selections (tokens 0 and 1)
            assert mock_set.called
            args, _ = mock_set.call_args
            assert len(args[0]) == 2

    def test_clear_highlights(self, highlighter, card):
        """Test clearing highlights."""
        highlighter.build_combo_box()

        # Mock card._clear_all_highlights
        with patch.object(card, '_clear_all_highlights') as mock_clear:
            highlighter.clear_highlights()
            assert mock_clear.called

    def test_show_hide_filter_dialog(self, highlighter, qtbot):
        """Test showing and hiding filter dialog from highlighter."""
        highlighter.build_combo_box()
        highlighter.highlighting_combo.setCurrentIndex(1) # POS

        active_cmd = highlighter.active_command
        assert active_cmd.dialog.isVisible()

        highlighter.hide_filter_dialog()
        assert not active_cmd.dialog.isVisible()

        highlighter.show_filter_dialog()
        assert active_cmd.dialog.isVisible()

    def test_filter_dialog_interaction(self, highlighter, card, db_session, qtbot):
        """Test that toggling a checkbox in the filter dialog updates highlights."""
        # Setup tokens with annotations
        tokens = card.tokens
        db_session.add_all(tokens)
        db_session.commit()

        tokens[0].annotation = Annotation(token_id=tokens[0].id, pos="D", case="n", number="s")
        tokens[1].annotation = Annotation(token_id=tokens[1].id, pos="N", case="n", number="s")
        db_session.commit()
        highlighter.annotations = {t.id: t.annotation for t in tokens if t.id}

        # 1. Switch to POS highlighting
        combo = highlighter.build_combo_box()
        combo.setCurrentIndex(1) # POS

        # Initially 2 highlights
        assert len(card.oe_text_edit.extraSelections()) >= 2

        # 2. Deselect Nouns (N) in the dialog
        pos_dialog = highlighter.active_command.dialog
        noun_checkbox = pos_dialog.checkboxes["N"]

        # Clicking checkbox should trigger highlight update
        noun_checkbox.setChecked(False)

        # Now only 1 highlight (D) should remain
        # Note: Depending on how markers/other highlights are handled, it might be exactly 1 or more
        # But it should definitely be less than before.
        selections = card.oe_text_edit.extraSelections()
        assert len(selections) == 1
        # The remaining selection should be for "Se" (D)
        # We can't easily check the text of the selection without more complex inspection,
        # but the count change is a good indicator.

        # 3. Reselect Nouns
        noun_checkbox.setChecked(True)
        assert len(card.oe_text_edit.extraSelections()) == 2

    def test_number_highlighting_plural_verb(self, highlighter, card, db_session):
        """Test that plural verbs are correctly highlighted (handling p/pl discrepancy)."""
        # Setup token with plural verb
        tokens = card.tokens
        db_session.add_all(tokens)
        db_session.commit()

        # "fēoll" is singular, but let's make it plural for testing
        tokens[2].annotation = Annotation(token_id=tokens[2].id, pos="V", number="p")
        db_session.commit()
        highlighter.annotations = {t.id: t.annotation for t in tokens if t.id}

        # Switch to Number highlighting
        combo = highlighter.build_combo_box()
        combo.setCurrentIndex(3) # Number

        # Check if the plural verb is highlighted
        # If there's a bug, it won't be highlighted because 'p' is not in the dialog's 's', 'd', 'pl'
        selections = card.oe_text_edit.extraSelections()

        # We also need to account for D and N which are also highlighted for number
        # tokens[0] (D) and tokens[1] (N) might not have annotations yet in this test
        # Let's ensure they don't or do.

        # The previous tests might have left annotations? No, new fixture per test.

        # Currently only tokens[2] has a number annotation.
        assert len(selections) > 0, "Plural verb 'p' should be highlighted"

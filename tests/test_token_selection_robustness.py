
import pytest
from PySide6.QtCore import QPoint, Qt
from oeapp.ui.sentence_card import SentenceCard
from oeapp.models.token import Token
from oeapp.models.note import Note
from tests.conftest import create_test_project, create_test_sentence

class TestTokenSelectionRobustness:
    """Test cases for robust token selection."""

    def test_token_selection_with_notes_and_spaces(self, db_session, qapp, qtbot):
        """
        Test that tokens are correctly selected even with superscripts and extra spaces.
        This reproduces the problematic sentence provided by the user.
        """
        text = "Men ða lēofstan, manað ūs and myngaþ þeos hāliġe bōc þæt wē sīen  ġe-myndiġe ymb ūre sawle þearfe, ond ēac swā ūres þæs nēhstan dæġes ond þǣre tō-scadednesse ūre sāwle þonne hīo of ðam liċ-homan lǣdde bīo."
        project = create_test_project(db_session, name="Test Project", text=text)
        sentence = project.sentences[0]

        # Add some notes to trigger superscripts
        # 'of' is at tokens[32] (0-indexed)
        # last 'ūre' is at tokens[28]
        tokens = sentence.tokens
        of_token = tokens[32]
        ure_token = tokens[28]

        note1 = Note(sentence_id=sentence.id, start_token=of_token.id, end_token=of_token.id, note_text_md="Note on of")
        note2 = Note(sentence_id=sentence.id, start_token=ure_token.id, end_token=ure_token.id, note_text_md="Note on ure")
        db_session.add(note1)
        db_session.add(note2)
        db_session.commit()

        # VERY IMPORTANT: Re-fetch everything from DB using the session card will use
        # or at least ensure IDs are stable and objects are not detached
        db_session.refresh(sentence)
        for t in sentence.tokens:
            db_session.refresh(t)

        card = SentenceCard(sentence, parent=None)
        card.show()
        qtbot.addWidget(card)

        # Force a render
        card._render_oe_text_with_superscripts()

        print(f"Token positions keys: {list(card._token_positions.keys())}")
        print(f"of_token id: {of_token.id}")

        # Find 'of' in the editor using positions
        # Use the ID from the card's tokens to be sure
        card_of_token = card.tokens[32]
        assert card_of_token.id in card._token_positions
        of_start, of_end = card._token_positions[card_of_token.id]

        # Middle of 'of'
        of_mid = (of_start + of_end) // 2

        token_idx = card._find_token_at_position(of_mid)
        assert token_idx == 32

        # Test selection of 'ūre'
        card_ure_token = card.tokens[28]
        assert card_ure_token.id in card._token_positions
        ure_start, ure_end = card._token_positions[card_ure_token.id]
        ure_mid = (ure_start + ure_end) // 2
        token_idx = card._find_token_at_position(ure_mid)
        assert token_idx == 28

    def test_global_deselection(self, db_session, qapp, qtbot):
        """
        Test that selecting a token in one card clears selections in other cards.
        """
        from oeapp.ui.main_window import MainWindow
        from oeapp.models.project import Project
        from oeapp.state import ApplicationState

        text1 = "Sentence one."
        text2 = "Sentence two."
        project = create_test_project(db_session, name="Test Project", text=text1 + " " + text2)
        db_session.commit()
        db_session.refresh(project)
        project_id = project.id

        # Ensure ApplicationState has the right session
        state = ApplicationState()
        state.session = db_session

        window = MainWindow()
        # MainWindow also resets state, so we might need to set it again or
        # let MainWindow use the db_session.
        window.application_state.session = db_session

        project = Project.get(project.id)
        window.load_project(project)
        window.show()
        qtbot.addWidget(window)

        project_ui = window.project_ui
        assert len(project_ui.sentence_cards) == 2

        card1 = project_ui.sentence_cards[0]
        card2 = project_ui.sentence_cards[1]

        # Ensure rendered
        card1._render_oe_text_with_superscripts()
        card2._render_oe_text_with_superscripts()

        # Select token in card1
        token1 = card1.tokens[0]
        card1.selected_token_index = 0
        card1.span_highlighter.highlight(token1.order_index)
        card1.token_selected_for_details.emit(token1, card1.sentence, card1)

        assert card1.selected_token_index == 0
        assert card1.span_highlighter.is_highlighted

        # Select token in card2
        token2 = card2.tokens[0]
        card2.selected_token_index = 0
        card2.span_highlighter.highlight(token2.order_index)
        card2.token_selected_for_details.emit(token2, card2.sentence, card2)

        # Card1 should be deselected
        assert card1.selected_token_index is None
        assert card1.span_highlighter.is_highlighted is False

        # Card2 should be selected
        assert card2.selected_token_index == 0
        assert card2.span_highlighter.is_highlighted


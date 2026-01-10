import pytest
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCursor, QTextCharFormat
from oeapp.ui.sentence_card import SentenceCard
from oeapp.models.token import Token
from tests.conftest import create_test_project

def test_token_selection_edge_cases(db_session, qapp, mock_main_window):
    text = "word1 word2"
    project = create_test_project(db_session, name="Test", text=text)
    sentence = project.sentences[0]
    card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
    card.show()

    # Ensure rendered
    card.oe_text_edit.render_readonly_text()

    # Text: "word1 word2"
    # word1 (0): 0-5
    # space: 5-6
    # word2 (1): 6-11

    # Test click on START of word2 (pos 6)
    # find_token_at_position should return 1 (word2)
    res = card.oe_text_edit.find_token_at_position(6)
    assert res == 1

    # Test click on END of word1 (pos 5)
    # This is exactly between '1' and ' '.
    res = card.oe_text_edit.find_token_at_position(5)
    assert res == 0

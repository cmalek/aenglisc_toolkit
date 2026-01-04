
import pytest
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCursor, QTextCharFormat
from oeapp.ui.sentence_card import SentenceCard
from oeapp.models.token import Token
from tests.conftest import create_test_project

def test_token_selection_edge_cases(db_session, qapp):
    text = "word1 word2"
    project = create_test_project(db_session, name="Test", text=text)
    sentence = project.sentences[0]
    card = SentenceCard(sentence, parent=None)
    card.show()

    # Ensure rendered
    card._render_oe_text_with_superscripts()

    # Text: "word1 word2"
    # word1 (0): 0-5
    # space: 5-6
    # word2 (1): 6-11

    # Test click on START of word2 (pos 6)
    # _find_token_at_position should return 1 (word2)
    # In previous version it returned None or 0.
    res = card._find_token_at_position(6)
    assert res == 1

    # Test click on END of word1 (pos 5)
    # This is exactly between '1' and ' '.
    # _find_token_at_position should return 0 (word1)
    res = card._find_token_at_position(5)
    assert res == 0

    # Test click on space (pos 5.5? no, cursors are integers)
    # If we click at pos 5, it's either before or after the char.
    # QTextEdit.cursorForPosition(point) gives a cursor.
    # If point is on space, cursor is either at 5 or 6.

    # If cursor is at 5 (start of space):
    # AFTER is space (no property)
    # BEFORE is '1' (property 0)
    # Should return 0.

    # If cursor is at 6 (end of space):
    # AFTER is 'w' (property 1)
    # BEFORE is space (no property)
    # Should return 1.

    # This behavior handles the "near the edge" requirement.



import pytest
from oeapp.ui.sentence_card import SentenceCard
from oeapp.models.token import Token
from tests.conftest import create_test_project

def test_user_problematic_sentence_clicks(db_session, qapp):
    text = "Men ða lēofstan, manað ūs and myngaþ þeos hāliġe bōc þæt wē sīen  ġe-myndiġe ymb ūre sawle þearfe, ond ēac swā ūres þæs nēhstan dæġes ond þǣre tō-scadednesse ūre sāwle þonne hīo of ðam liċ-homan lǣdde bīo."
    project = create_test_project(db_session, name="Test", text=text)
    sentence = project.sentences[0]
    card = SentenceCard(sentence, parent=None)
    card.show()
    card._render_oe_text_with_superscripts()

    # "of" is at order_index 32
    # Find its position in the editor
    of_token = [t for t in card.tokens if t.order_index == 32][0]
    start, end = card._token_positions[of_token.id]

    # Test click at START of "of"
    res = card._find_token_at_position(text, start)
    assert res == 32, f"Expected 32 at start of 'of' (pos {start}), got {res}"

    # Test click in MIDDLE of "of"
    res = card._find_token_at_position(text, start + 1)
    assert res == 32, f"Expected 32 in middle of 'of' (pos {start+1}), got {res}"

    # Test click at END of "of"
    res = card._find_token_at_position(text, end)
    assert res == 32, f"Expected 32 at end of 'of' (pos {end}), got {res}"

    # "hīo" is at order_index 31
    hio_token = [t for t in card.tokens if t.order_index == 31][0]
    h_start, h_end = card._token_positions[hio_token.id]

    res = card._find_token_at_position(text, h_start)
    assert res == 31


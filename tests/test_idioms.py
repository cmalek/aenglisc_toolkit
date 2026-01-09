"""Tests for idiom management."""

import pytest
from PySide6.QtWidgets import QPushButton
from oeapp.models.idiom import Idiom
from oeapp.models.annotation import Annotation
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.dialogs.annotation_modal import AnnotationModal

@pytest.fixture
def sentence(db_session, sample_sentence):
    """Update sample sentence for idiom tests."""
    # Merge into current session to avoid InvalidRequestError
    sample_sentence = db_session.merge(sample_sentence)
    text_oe = "swā hwæt swā"
    sample_sentence.update(text_oe)
    db_session.commit()
    db_session.refresh(sample_sentence)
    return sample_sentence

def test_idiom_creation(db_session, sentence):
    """Test creating an idiom."""
    # Ensure tokens are loaded and bound to session
    sentence = db_session.merge(sentence)
    tokens = list(sentence.tokens)
    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[2].id,
    )
    idiom.save()

    annotation = Annotation(idiom_id=idiom.id, pos="R")
    annotation.save()

    db_session.commit()
    db_session.refresh(sentence)

    assert len(sentence.idioms) == 1
    assert sentence.idioms[0].annotation.pos == "R"
    assert sentence.idioms[0].start_token.surface == "swā"
    assert sentence.idioms[0].end_token.surface == "swā"

def test_idiom_deletion_on_token_removal(db_session, sentence):
    """Test that idiom is deleted when one of its tokens is removed."""
    sentence = db_session.merge(sentence)
    # Ensure tokens are loaded
    tokens = list(sentence.tokens)
    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[2].id,
    )
    idiom.save()
    Annotation(idiom_id=idiom.id, pos="R").save()
    db_session.commit()
    db_session.refresh(sentence)

    # Remove the middle token "hwæt"
    new_text = "swā swā"
    messages = sentence.update(new_text)
    db_session.commit()
    db_session.refresh(sentence)

    assert len(sentence.idioms) == 0
    assert any("Idiom annotation deleted" in m for m in messages)

def test_idiom_preservation_on_token_modification(db_session, sentence):
    """Test that idiom is preserved when a token is modified but not removed."""
    sentence = db_session.merge(sentence)
    tokens = list(sentence.tokens)
    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[2].id,
    )
    idiom.save()
    Annotation(idiom_id=idiom.id, pos="R").save()
    db_session.commit()
    db_session.refresh(sentence)

    # Modify "hwæt" to "hwat" (typo fix)
    new_text = "swā hwat swā"
    messages = sentence.update(new_text)
    db_session.commit()
    db_session.refresh(sentence)

    assert len(sentence.idioms) == 1
    assert len(messages) == 0
    assert sentence.tokens[1].surface == "hwat"

def test_idiom_preservation_on_insertion_in_middle(db_session, sentence):
    """Test that idiom is preserved and includes new token when inserted in middle."""
    sentence = db_session.merge(sentence)
    tokens = list(sentence.tokens)
    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[2].id,
    )
    idiom.save()
    Annotation(idiom_id=idiom.id, pos="R").save()
    db_session.commit()
    db_session.refresh(sentence)

    # Insert "þæt" in middle: "swā þæt hwæt swā"
    new_text = "swā þæt hwæt swā"
    sentence.update(new_text)
    db_session.commit()
    db_session.refresh(sentence)

    assert len(sentence.idioms) == 1
    # Rendering should now include 4 tokens
    start_order = sentence.idioms[0].start_token.order_index
    end_order = sentence.idioms[0].end_token.order_index
    tokens_in_range = [t for t in sentence.tokens if start_order <= t.order_index <= end_order]
    assert len(tokens_in_range) == 4

@pytest.mark.qt_no_exception_capture
def test_idiom_selection_ui(qtbot, db_session, sentence, mock_main_window):
    """Test idiom selection in SentenceCard."""
    sentence = db_session.merge(sentence)
    db_session.refresh(sentence)
    # Trigger loading of relationships
    _ = list(sentence.tokens)
    _ = list(sentence.idioms)

    card = SentenceCard(sentence, main_window=mock_main_window)
    qtbot.addWidget(card)

    # Simulate Cmd+Click on first token
    card._handle_idiom_selection_click(0)
    assert card._selected_token_range == (0, 0)

    # Simulate Cmd+Click on third token
    card._handle_idiom_selection_click(2)
    assert card._selected_token_range == (0, 2)
    assert card.selected_token_index is None

@pytest.mark.qt_no_exception_capture
def test_idiom_modal_navigation(qtbot, db_session, sentence, mock_main_window):
    """Test navigation from idiom modal to token modal."""
    sentence = db_session.merge(sentence)
    db_session.refresh(sentence)
    tokens = list(sentence.tokens)
    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[2].id,
    )
    idiom.save()
    db_session.commit()
    db_session.refresh(sentence)

    card = SentenceCard(sentence, main_window=mock_main_window)
    qtbot.addWidget(card)

    modal = AnnotationModal(idiom=sentence.idioms[0], parent=card)
    qtbot.addWidget(modal)

    # Find the first token link button
    token_btn = None
    for btn in modal.findChildren(QPushButton):
        if btn.text() == tokens[0].surface:
            token_btn = btn
            break

    assert token_btn is not None

    # Mock _open_token_modal to avoid blocking on exec()
    opened_token = None
    def mock_open_token_modal(token):
        nonlocal opened_token
        opened_token = token

    card._open_token_modal = mock_open_token_modal

    # Click it (we use the internal handler to avoid blocking on exec())
    modal._on_token_link_clicked(tokens[0])

    # The modal should have accepted (closed)
    assert modal.result() == AnnotationModal.DialogCode.Accepted
    # And the new modal should have been requested
    assert opened_token == tokens[0]

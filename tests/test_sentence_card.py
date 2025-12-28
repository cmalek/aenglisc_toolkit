"""Unit tests for SentenceCard."""

import pytest
from unittest.mock import MagicMock

from oeapp.ui.sentence_card import SentenceCard, ClickableTextEdit
from tests.conftest import create_test_project, create_test_sentence


class TestSentenceCard:
    """Test cases for SentenceCard."""

    def test_sentence_card_initializes(self, db_session, qapp):
        """Test SentenceCard initializes correctly."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        assert card.sentence == sentence
        assert card.session == db_session
        assert card.token_table is not None

    def test_sentence_card_displays_sentence_text(self, db_session, qapp):
        """Test SentenceCard displays sentence text."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        assert card.get_oe_text() == "Se cyning"

    def test_sentence_card_displays_translation(self, db_session, qapp):
        """Test SentenceCard displays translation."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        sentence.text_modern = "The king"
        db_session.commit()

        card = SentenceCard(sentence, parent=None)

        assert card.get_translation() == "The king"

    def test_sentence_card_updates_sentence(self, db_session, qapp):
        """Test SentenceCard updates when sentence changes."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        # Update sentence
        sentence.text_oe = "Se cyning fēoll"
        sentence.text_modern = "The king fell"
        db_session.commit()

        card.update_sentence(sentence)

        assert card.get_oe_text() == "Se cyning fēoll"
        assert card.get_translation() == "The king fell"

    def test_sentence_card_has_color_maps(self, db_session, qapp):
        """Test SentenceCard has POS and case color maps."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        assert "N" in card.POS_COLORS
        assert "n" in card.CASE_COLORS
        assert "s" in card.NUMBER_COLORS

    def test_sentence_card_emits_token_selected_signal(self, db_session, qapp):
        """Test SentenceCard emits token_selected_for_details signal."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]
        card = SentenceCard(sentence, parent=None)

        # Connect signal
        received_token = None
        received_sentence = None
        def on_token_selected(token, sentence, card):
            nonlocal received_token, received_sentence
            received_token = token
            received_sentence = sentence
        card.token_selected_for_details.connect(on_token_selected)

        # Simulate token selection
        card.token_selected_for_details.emit(token, sentence, card)

        assert received_token == token
        assert received_sentence == sentence

    def test_sentence_card_handles_paragraph_start(self, db_session, qapp):
        """Test SentenceCard handles paragraph start flag."""
        project = create_test_project(db_session, name="Test", text="")
        db_session.commit()

        sentence = create_test_sentence(
            db_session, project_id=project.id, text="First paragraph.",
            display_order=1, is_paragraph_start=True
        )
        db_session.commit()

        card = SentenceCard(sentence, parent=None)

        assert card.sentence.is_paragraph_start is True


class TestClickableTextEdit:
    """Test cases for ClickableTextEdit."""

    def test_clickable_text_edit_initializes(self, qapp):
        """Test ClickableTextEdit initializes correctly."""
        widget = ClickableTextEdit(parent=None)

        assert widget is not None

    def test_clickable_text_edit_emits_clicked_signal(self, qapp):
        """Test ClickableTextEdit emits clicked signal."""
        from PySide6.QtCore import QPoint

        widget = ClickableTextEdit(parent=None)

        # Connect signal
        clicked_pos = None
        clicked_modifiers = None
        def on_clicked(pos, modifiers):
            nonlocal clicked_pos, clicked_modifiers
            clicked_pos = pos
            clicked_modifiers = modifiers
        widget.clicked.connect(on_clicked)

        # Simulate click
        point = QPoint(10, 10)
        widget.clicked.emit(point, None)

        assert clicked_pos == point

    def test_clickable_text_edit_emits_double_clicked_signal(self, qapp):
        """Test ClickableTextEdit emits double_clicked signal."""
        from PySide6.QtCore import QPoint

        widget = ClickableTextEdit(parent=None)

        # Connect signal
        double_clicked_pos = None
        def on_double_clicked(pos):
            nonlocal double_clicked_pos
            double_clicked_pos = pos
        widget.double_clicked.connect(on_double_clicked)

        # Simulate double-click
        point = QPoint(10, 10)
        widget.double_clicked.emit(point)

        assert double_clicked_pos == point


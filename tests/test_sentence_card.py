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

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        assert card.sentence == sentence
        assert card.session == db_session
        assert card.token_table is not None

    def test_sentence_card_displays_sentence_text(self, db_session, qapp):
        """Test SentenceCard displays sentence text."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        assert card.get_oe_text() == "Se cyning"

    def test_sentence_card_displays_translation(self, db_session, qapp):
        """Test SentenceCard displays translation."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        sentence.text_modern = "The king"

        card = SentenceCard(sentence, parent=None)

        assert card.get_translation() == "The king"

    def test_sentence_card_updates_sentence(self, db_session, qapp):
        """Test SentenceCard updates when sentence changes."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        # Update sentence
        sentence.text_oe = "Se cyning fēoll"
        sentence.text_modern = "The king fell"

        card.update_sentence(sentence)

        assert card.get_oe_text() == "Se cyning fēoll"
        assert card.get_translation() == "The king fell"

    def test_sentence_card_has_color_maps(self, db_session, qapp):
        """Test SentenceCard has POS and case color maps."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)

        assert "N" in card.POS_COLORS
        assert "n" in card.CASE_COLORS
        assert "s" in card.NUMBER_COLORS

    def test_sentence_card_emits_token_selected_signal(self, db_session, qapp):
        """Test SentenceCard emits token_selected_for_details signal."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

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

        sentence = create_test_sentence(
            db_session, project_id=project.id, text="First paragraph.",
            display_order=1, is_paragraph_start=True
        )

        card = SentenceCard(sentence, parent=None)

        assert card.sentence.is_paragraph_start is True

    def test_token_navigation_next_prev(self, db_session, qapp, qtbot):
        """Test token navigation using arrow keys."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning fēoll")
        sentence = project.sentences[0]
        # Mock main_window since keyPressEvent checks for it
        mock_main_window = MagicMock()
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
        # Manually render to populate _token_positions
        card._render_oe_text_with_superscripts()
        card.show()
        qtbot.addWidget(card)

        # 1. Select first token (Se)
        card.selected_token_index = 0
        card.token_table.select_token(0)

        # 2. Press Right Arrow -> should move to "cyning" (index 1)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        card.keyPressEvent(event)

        assert card.selected_token_index == 1
        assert card.token_table.table.currentRow() == 1

        # 3. Press Right Arrow -> should move to "fēoll" (index 2)
        event2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        card.keyPressEvent(event2)
        assert card.selected_token_index == 2
        assert card.token_table.table.currentRow() == 2

        # 4. Press Right Arrow at end -> should stay at "fēoll" (index 2)
        event3 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        card.keyPressEvent(event3)
        assert card.selected_token_index == 2
        assert card.token_table.table.currentRow() == 2

        # 5. Press Left Arrow -> should move back to "cyning" (index 1)
        event_left = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        card.keyPressEvent(event_left)
        assert card.selected_token_index == 1
        assert card.token_table.table.currentRow() == 1

        # 6. Press Left Arrow -> should move back to "Se" (index 0)
        event_left2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        card.keyPressEvent(event_left2)
        assert card.selected_token_index == 0
        assert card.token_table.table.currentRow() == 0

        # 7. Press Left Arrow at start -> should stay at "Se" (index 0)
        event_left3 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        card.keyPressEvent(event_left3)
        assert card.selected_token_index == 0
        assert card.token_table.table.currentRow() == 0

    def test_token_table_selection_syncs_to_card(self, db_session, qapp):
        """Test that selecting a token in the table updates the card state."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)
        # Manually render to populate _token_positions
        card._render_oe_text_with_superscripts()

        # Select second token in table
        token = sentence.tokens[1]
        card.token_table.token_selected.emit(token)

        assert card.selected_token_index == token.order_index
        assert card._current_highlight_start is not None

    def test_clickable_text_edit_ignores_arrows(self, qapp):
        """Test that ClickableTextEdit ignores arrow keys so they bubble up."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        widget = ClickableTextEdit(parent=None)

        # Test Right Arrow - should be ignored (bubbled up)
        event_right = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        widget.keyPressEvent(event_right)
        assert event_right.isAccepted() is False

        # Test Left Arrow - should be ignored (bubbled up)
        event_left = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        widget.keyPressEvent(event_left)
        assert event_left.isAccepted() is False


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

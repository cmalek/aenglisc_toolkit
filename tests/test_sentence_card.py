"""Unit tests for SentenceCard."""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QComboBox, QWidget
from unittest.mock import MagicMock

from oeapp.models import Annotation
from oeapp.models.idiom import Idiom
from oeapp.ui.sentence_card import SentenceCard
from oeapp.ui.oe_text_edit import OldEnglishTextEdit
from tests.conftest import create_test_project, create_test_sentence


class TestSentenceCard:
    """Test cases for SentenceCard."""

    def test_sentence_card_initializes(self, db_session, qapp, mock_main_window):
        """Test SentenceCard initializes correctly."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        assert card.sentence == sentence
        assert card.session == db_session
        assert card.token_table is not None

    def test_sentence_card_has_color_maps(self, db_session, qapp, mock_main_window):
        """Test SentenceCard has POS and case color maps."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        assert "N" in card.POS_COLORS
        assert "n" in card.CASE_COLORS
        assert "s" in card.NUMBER_COLORS

    def test_sentence_card_emits_token_selected_signal(self, db_session, qapp, mock_main_window):
        """Test SentenceCard emits token_selected_for_details signal."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

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

    def test_sentence_card_handles_paragraph_start(self, db_session, qapp, mock_main_window):
        """Test SentenceCard handles paragraph start flag."""
        project = create_test_project(db_session, name="Test", text="")

        sentence = create_test_sentence(
            db_session, project_id=project.id, text="First paragraph.",
            display_order=1, is_paragraph_start=True
        )

        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        assert card.sentence.is_paragraph_start is True

    def test_token_navigation_next_prev(self, db_session, qapp, qtbot, mock_main_window):
        """Test token navigation using arrow keys."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning fēoll")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
        # Manually render to populate positions
        card.oe_text_edit.render_readonly_text()
        card.show()
        qtbot.addWidget(card)

        # 1. Select first token (Se)
        card.oe_text_edit.set_selected_token_index(0)
        card.token_table.select_token(0)

        # 2. Press Right Arrow -> should move to "cyning" (index 1)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event)

        assert card.oe_text_edit.current_token_index() == 1
        assert card.token_table.table.currentRow() == 1

        # 3. Press Right Arrow -> should move to "fēoll" (index 2)
        event2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event2)
        assert card.oe_text_edit.current_token_index() == 2
        assert card.token_table.table.currentRow() == 2

        # 4. Press Right Arrow at end -> should stay at "fēoll" (index 2)
        event3 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event3)
        assert card.oe_text_edit.current_token_index() == 2
        assert card.token_table.table.currentRow() == 2

        # 5. Press Left Arrow -> should move back to "cyning" (index 1)
        event_left = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event_left)
        assert card.oe_text_edit.current_token_index() == 1
        assert card.token_table.table.currentRow() == 1

        # 6. Press Left Arrow -> should move back to "Se" (index 0)
        event_left2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event_left2)
        assert card.oe_text_edit.current_token_index() == 0
        assert card.token_table.table.currentRow() == 0

        # 7. Press Left Arrow at start -> should stay at "Se" (index 0)
        event_left3 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event_left3)
        assert card.oe_text_edit.current_token_index() == 0
        assert card.token_table.table.currentRow() == 0

    def test_enter_key_opens_annotation_modal(self, db_session, qapp, qtbot, monkeypatch, mock_main_window):
        """Test that pressing Enter key opens the annotation modal when a token is selected."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        # Mock _open_annotation_modal to see if it's called
        mock_open_modal = MagicMock()
        monkeypatch.setattr(card, "_open_annotation_modal", mock_open_modal)

        # Select a token
        card.oe_text_edit.set_selected_token_index(0)

        # Press Enter
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event)

        assert mock_open_modal.called
        assert event.isAccepted()

        # Press Return (standard Enter)
        mock_open_modal.reset_mock()
        event2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event2)

        assert mock_open_modal.called
        assert event2.isAccepted()

    def test_enter_key_in_edit_mode_not_intercepted(
        self, db_session, qapp, qtbot, monkeypatch, mock_main_window
    ):
        """Test that Enter key is NOT intercepted by SentenceCard when in edit mode."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        # Enter edit mode
        card._on_edit_oe_clicked()
        assert card.oe_text_edit.in_edit_mode is True

        # Mock _open_annotation_modal
        mock_open_modal = MagicMock()
        monkeypatch.setattr(card, "_open_annotation_modal", mock_open_modal)

        # Select a token (even though in edit mode, it might have an index)
        card.oe_text_edit.set_selected_token_index(0)

        # Press Enter
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event)

        # Should NOT call open_modal.
        # Note: QTextEdit will accept the event to insert a newline.
        assert not mock_open_modal.called

    def test_enter_key_without_token_selected_does_nothing(
        self, db_session, qapp, qtbot, monkeypatch, mock_main_window
    ):
        """Test that Enter key does nothing if no token is selected."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        # Ensure no token selected
        card.oe_text_edit.reset_selection()

        # Mock _open_annotation_modal
        mock_open_modal = MagicMock()
        monkeypatch.setattr(card, "_open_annotation_modal", mock_open_modal)

        # Press Enter
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event)

        assert not mock_open_modal.called
        assert not event.isAccepted()

    def _create_card_with_idiom(self, db_session, qtbot, mock_main_window):
        project = create_test_project(
            db_session, name="Test", text="Se cyning fēoll on eorþan"
        )
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
        qtbot.addWidget(card)
        card.oe_text_edit.render_readonly_text()
        card.show()

        card.session.refresh(sentence)
        card.set_tokens()
        card.oe_text_edit.render_readonly_text()

        tokens = list(card.oe_text_edit.tokens)
        idiom = Idiom(
            sentence_id=sentence.id,
            start_token_id=tokens[0].id,
            end_token_id=tokens[1].id,
        )
        idiom.sentence = sentence
        idiom.start_token = tokens[0]
        idiom.end_token = tokens[1]
        sentence.idioms.append(idiom)
        idiom.save()
        db_session.commit()
        card.session.refresh(sentence)
        card.set_tokens()
        card.oe_text_edit.idioms = sentence.idioms
        card.oe_text_edit.render_readonly_text()
        tokens = list(card.oe_text_edit.tokens)
        idiom = card.oe_text_edit.idioms[0]
        return card, tokens, idiom

    def test_double_click_selected_idiom_opens_idiom_modal(
        self, db_session, qtbot, monkeypatch, mock_main_window
    ):
        card, tokens, idiom = self._create_card_with_idiom(db_session, qtbot, mock_main_window)
        card.oe_text_edit.selector.idiom_selection(tokens[0].order_index)
        card.oe_text_edit.selector.idiom_selection(tokens[1].order_index)
        selection = card.oe_text_edit.current_range()

        idiom_calls = []
        token_calls = []
        monkeypatch.setattr(card, "_open_idiom_modal", lambda i: idiom_calls.append(i))
        monkeypatch.setattr(card, "_open_token_modal", lambda t: token_calls.append(t))
        monkeypatch.setattr(card.oe_text_edit, "find_token_at_position", lambda _: tokens[0].order_index)

        from PySide6.QtGui import QMouseEvent
        event = QMouseEvent(
            QMouseEvent.Type.MouseButtonDblClick,
            QPoint(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier
        )
        card.oe_text_edit.mouseDoubleClickEvent(event)

        assert idiom_calls and idiom_calls[0].id == idiom.id
        assert token_calls == []
        assert card.oe_text_edit.current_range() == selection

    def test_token_table_selection_syncs_to_card(self, db_session, qapp, mock_main_window):
        """Test that selecting a token in the table updates the card state."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
        # Manually render to populate positions
        card.oe_text_edit.render_readonly_text()

        # Select second token in table
        token = sentence.tokens[1]
        card.token_table.token_selected.emit(token)

        assert card.oe_text_edit.current_token_index() == token.order_index
        assert card.oe_text_edit.span_highlighter.is_highlighted

    def test_arrow_keys_in_edit_mode_move_cursor(self, db_session, qapp, qtbot, mock_main_window):
        """Test that arrow keys move the cursor instead of tokens in edit mode."""
        project = create_test_project(db_session, name="TestEdit", text="Se cyning fēoll")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
        qtbot.addWidget(card)
        card.show()

        # Enter edit mode
        card._on_edit_oe_clicked()
        assert card.oe_text_edit.in_edit_mode is True
        assert card.oe_text_edit.isReadOnly() is False

        # Set cursor position to end (length of "Se cyning fēoll" is 15)
        text = "Se cyning fēoll"
        card.oe_text_edit.setPlainText(text)
        cursor = card.oe_text_edit.textCursor()
        cursor.setPosition(len(text))
        card.oe_text_edit.setTextCursor(cursor)
        assert card.oe_text_edit.textCursor().position() == 15

        # Press Left Arrow - should move cursor left (to 14)
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        card.oe_text_edit.keyPressEvent(event)
        assert card.oe_text_edit.textCursor().position() == 14
        # Token selection should not have changed from None
        assert card.oe_text_edit.current_token_index() is None

    def test_sentence_card_has_highlighter(self, db_session, qapp, mock_main_window):
        """Test that SentenceCard has a SentenceHighlighter."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)
        assert card.sentence_highlighter is not None
        assert card.sentence_highlighter.card == card

    def test_sentence_card_highlighter_combo_box_in_layout(self, db_session, qapp, mock_main_window):
        """Test that the highlighting combo box is present in the layout."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        # Check if highlighting_combo is set
        assert card.highlighting_combo is not None
        assert isinstance(card.highlighting_combo, QComboBox)

        # Verify it has the expected items
        expected_items = ["None", "Part of Speech", "Case", "Number", "Idiom"]
        items = [card.highlighting_combo.itemText(i) for i in range(card.highlighting_combo.count())]
        assert items == expected_items


class TestOldEnglishTextEditInternal:
    """Internal tests for OldEnglishTextEdit when used within SentenceCard."""

    def test_clickable_text_edit_ignores_arrows(self, qapp, mock_main_window):
        """Test that OldEnglishTextEdit ignores arrow keys so they bubble up when read-only."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent
        from unittest.mock import PropertyMock

        widget = OldEnglishTextEdit(parent=None)
        # We need a mock sentence and card for it to work properly
        mock_sentence = MagicMock()
        type(mock_sentence).sorted_tokens = PropertyMock(return_value=([], {}))
        mock_sentence.idioms = []
        mock_card = MagicMock(sentence=mock_sentence, main_window=mock_main_window)
        # mock_card.sentence_highlighter is also needed by OldEnglishTextEdit.sentence_card setter
        mock_card.sentence_highlighter = MagicMock()
        widget.sentence_card = mock_card

        widget.setReadOnly(True)

        # Test Right Arrow - should be ignored (bubbled up)
        event_right = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        widget.keyPressEvent(event_right)
        assert event_right.isAccepted() is False

        # Test Left Arrow - should be ignored (bubbled up)
        event_left = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        widget.keyPressEvent(event_left)
        assert event_left.isAccepted() is False

        # Test not read-only (edit mode)
        widget.setReadOnly(False)
        event_right_edit = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        widget.keyPressEvent(event_right_edit)
        # When not read-only, it should be accepted by QTextEdit
        assert event_right_edit.isAccepted() is True

"""Unit tests for OldEnglishTextEdit and TokenSelector."""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QWidget
from unittest.mock import MagicMock, patch

from oeapp.models.token import Token
from oeapp.models.sentence import Sentence
from oeapp.models.idiom import Idiom
from oeapp.ui.oe_text_edit import OldEnglishTextEdit, TokenSelector
from oeapp.ui.sentence_card import SentenceCard
from tests.conftest import create_test_project, create_test_sentence

class TestTokenSelector:
    @pytest.fixture
    def text_edit(self, db_session, qapp, mock_main_window):
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window)
        return card.oe_text_edit

    @pytest.fixture
    def selector(self, text_edit):
        return text_edit.selector

    def test_initialization(self, selector, text_edit):
        assert selector.text_edit == text_edit
        assert selector.sentence_card == text_edit.sentence_card
        assert selector.sentence == text_edit.sentence
        assert len(selector.tokens) == 2
        assert selector.selected_token_index is None
        assert selector.selected_token_range is None

    def test_set_selected_token_index(self, selector):
        selector.set_selected_token_index(1)
        assert selector.selected_token_index == 1
        assert selector.selected_token_range is None

    def test_reset_selection(self, selector):
        selector.set_selected_token_index(1)
        selector.reset_selection()
        assert selector.selected_token_index is None
        assert selector.selected_token_range is None

    def test_token_selection(self, selector, text_edit):
        # Select first token
        selector.token_selection(0)
        assert selector.selected_token_index == 0
        assert selector.selected_token_range is None
        
        # Verify signal emitted from text_edit
        # Note: we need to spy on the signal or check side effects
        assert text_edit.span_highlighter.is_highlighted

    def test_range_selection(self, selector, text_edit):
        # Populate positions
        text_edit.render_readonly_text()
        # Select first token then shift-click second
        selector.set_selected_token_index(0)
        selector.range_selection(1)
        assert selector.selected_token_range == (0, 1)
        assert selector.selected_token_index is None
        assert text_edit.span_highlighter.is_highlighted

    def test_idiom_selection(self, selector, text_edit):
        # Populate positions
        text_edit.render_readonly_text()
        # Cmd-click first token
        selector.idiom_selection(0)
        assert selector.selected_token_range == (0, 0)
        
        # Cmd-click second token
        selector.idiom_selection(1)
        assert selector.selected_token_range == (0, 1)
        assert text_edit.span_highlighter.is_highlighted

    def test_deselect_timer(self, selector, qtbot):
        selector.set_selected_token_index(0)
        # Simulate click on same token
        selector.token_selection(0)
        assert selector._deselect_timer.isActive()
        
        # Wait for timer
        qtbot.wait(150)
        assert selector.selected_token_index is None

class TestOldEnglishTextEdit:
    @pytest.fixture
    def card(self, db_session, qapp, mock_main_window):
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, main_window=mock_main_window)
        return card

    @pytest.fixture
    def text_edit(self, card):
        return card.oe_text_edit

    def test_initialization(self, text_edit, card):
        assert text_edit.sentence_card == card
        assert text_edit.isReadOnly()
        assert not text_edit.in_edit_mode

    def test_in_edit_mode_toggle(self, text_edit):
        text_edit.in_edit_mode = True
        assert not text_edit.isReadOnly()
        assert text_edit.in_edit_mode
        
        text_edit.in_edit_mode = False
        assert text_edit.isReadOnly()
        assert not text_edit.in_edit_mode

    def test_render_readonly_text(self, text_edit):
        # This is called during initialization, but let's call it again
        text_edit.render_readonly_text()
        # Verify text content (stripping superscripts logic if any)
        assert "Se" in text_edit.toPlainText()
        assert "cyning" in text_edit.toPlainText()

    def test_find_token_at_position(self, text_edit):
        # "Se" is at start
        token_index = text_edit.find_token_at_position(0)
        assert token_index == 0
        
        # "cyning" starts after "Se " (pos 3)
        token_index = text_edit.find_token_at_position(3)
        assert token_index == 1

    def test_navigation(self, text_edit):
        text_edit.set_selected_token_index(0)
        assert text_edit.current_token_index() == 0
        
        text_edit.next_token()
        assert text_edit.current_token_index() == 1
        
        text_edit.prev_token()
        assert text_edit.current_token_index() == 0

    def test_copy_paste_annotation(self, text_edit, mock_main_window):
        text_edit.set_selected_token_index(0)
        
        text_edit.copy_annotation()
        assert mock_main_window.action_service.copy_annotation.called
        
        text_edit.paste_annotation()
        assert mock_main_window.action_service.paste_annotation.called

    def test_key_press_navigation(self, text_edit, qtbot):
        text_edit.set_selected_token_index(0)
        
        # Right arrow
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.NoModifier)
        text_edit.keyPressEvent(event)
        assert text_edit.current_token_index() == 1
        
        # Left arrow
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Left, Qt.NoModifier)
        text_edit.keyPressEvent(event)
        assert text_edit.current_token_index() == 0

    def test_mouse_press_emits_clicked(self, text_edit, qtbot):
        clicked_args = []
        text_edit.clicked.connect(lambda pos, mod: clicked_args.append((pos, mod)))
        
        # Simulate mouse press
        event = QMouseEvent(QMouseEvent.Type.MouseButtonPress, QPoint(5, 5), Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.NoModifier)
        text_edit.mousePressEvent(event)
        
        assert len(clicked_args) == 1
        assert clicked_args[0][0] == QPoint(5, 5)

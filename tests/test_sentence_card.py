"""Unit tests for SentenceCard."""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent
from unittest.mock import MagicMock

from oeapp.models.idiom import Idiom
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

    def test_enter_key_opens_annotation_modal(self, db_session, qapp, qtbot, monkeypatch):
        """Test that pressing Enter key opens the annotation modal when a token is selected."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        mock_main_window = MagicMock()
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        # Mock _open_annotation_modal to see if it's called
        mock_open_modal = MagicMock()
        monkeypatch.setattr(card, "_open_annotation_modal", mock_open_modal)

        # Select a token
        card.selected_token_index = 0

        # Press Enter
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.NoModifier)
        card.keyPressEvent(event)

        assert mock_open_modal.called
        assert event.isAccepted()

        # Press Return (standard Enter)
        mock_open_modal.reset_mock()
        event2 = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Return, Qt.NoModifier)
        card.keyPressEvent(event2)

        assert mock_open_modal.called
        assert event2.isAccepted()

    def test_enter_key_in_edit_mode_not_intercepted(
        self, db_session, qapp, qtbot, monkeypatch
    ):
        """Test that Enter key is NOT intercepted by SentenceCard when in edit mode."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        mock_main_window = MagicMock()
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        # Enter edit mode
        card._on_edit_oe_clicked()
        assert card._oe_edit_mode is True

        # Mock _open_annotation_modal
        mock_open_modal = MagicMock()
        monkeypatch.setattr(card, "_open_annotation_modal", mock_open_modal)

        # Select a token (even though in edit mode, it might have an index)
        card.selected_token_index = 0

        # Press Enter
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.NoModifier)
        card.keyPressEvent(event)

        # Should NOT call open_modal and should NOT accept the event (bubbles to super)
        assert not mock_open_modal.called
        assert not event.isAccepted()

    def test_enter_key_without_token_selected_does_nothing(
        self, db_session, qapp, qtbot, monkeypatch
    ):
        """Test that Enter key does nothing if no token is selected."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeyEvent

        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        mock_main_window = MagicMock()
        card = SentenceCard(sentence, main_window=mock_main_window, parent=None)

        # Ensure no token selected
        card.selected_token_index = None

        # Mock _open_annotation_modal
        mock_open_modal = MagicMock()
        monkeypatch.setattr(card, "_open_annotation_modal", mock_open_modal)

        # Press Enter
        event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Enter, Qt.NoModifier)
        card.keyPressEvent(event)

        assert not mock_open_modal.called
        assert not event.isAccepted()

    def _create_card_with_idiom(self, db_session, qtbot):
        project = create_test_project(
            db_session, name="Test", text="Se cyning fēoll on eorþan"
        )
        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)
        qtbot.addWidget(card)
        card._render_oe_text_with_superscripts()
        card.show()

        card.session.refresh(sentence)
        card.set_tokens(sentence.tokens)
        card._render_oe_text_with_superscripts()

        tokens = list(card.tokens)
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
        card.set_tokens(sentence.tokens)
        card.idioms = sentence.idioms
        card._render_oe_text_with_superscripts()
        tokens = list(card.tokens)
        idiom = card.idioms[0]
        return card, tokens, idiom

    def test_double_click_selected_idiom_opens_idiom_modal(
        self, db_session, qtbot, monkeypatch
    ):
        card, tokens, idiom = self._create_card_with_idiom(db_session, qtbot)
        card._handle_idiom_selection_click(tokens[0].order_index)
        card._handle_idiom_selection_click(tokens[1].order_index)
        selection = card._selected_token_range

        idiom_calls = []
        token_calls = []
        monkeypatch.setattr(card, "_open_idiom_modal", lambda i: idiom_calls.append(i))
        monkeypatch.setattr(card, "_open_token_modal", lambda t: token_calls.append(t))
        monkeypatch.setattr(card, "_find_token_at_position", lambda _: tokens[0].order_index)

        card._on_oe_text_double_clicked(QPoint(0, 0))

        assert idiom_calls and idiom_calls[0].id == idiom.id
        assert token_calls == []
        assert card._selected_token_range == selection

    def test_double_click_token_in_idiom_opens_idiom_modal(
        self, db_session, qtbot, monkeypatch
    ):
        card, tokens, idiom = self._create_card_with_idiom(db_session, qtbot)
        card._selected_token_range = None
        card.selected_token_index = None

        idiom_calls = []
        token_calls = []
        monkeypatch.setattr(card, "_open_idiom_modal", lambda i: idiom_calls.append(i))
        monkeypatch.setattr(card, "_open_token_modal", lambda t: token_calls.append(t))
        monkeypatch.setattr(card, "_find_token_at_position", lambda _: tokens[0].order_index)

        card._on_oe_text_double_clicked(QPoint(0, 0))

        assert idiom_calls and idiom_calls[0].id == idiom.id
        assert token_calls == []
        assert card._selected_token_range == (
            idiom.start_token.order_index,
            idiom.end_token.order_index,
        )

    def test_double_click_token_outside_idiom_opens_token_modal(
        self, db_session, qtbot, monkeypatch
    ):
        card, tokens, idiom = self._create_card_with_idiom(db_session, qtbot)
        outside_order = tokens[-1].order_index

        idiom_calls = []
        token_calls = []
        monkeypatch.setattr(card, "_open_idiom_modal", lambda i: idiom_calls.append(i))
        monkeypatch.setattr(card, "_open_token_modal", lambda t: token_calls.append(t))
        monkeypatch.setattr(card, "_find_token_at_position", lambda _: outside_order)

        card._on_oe_text_double_clicked(QPoint(0, 0))

        assert idiom_calls == []
        assert token_calls and token_calls[0].id == tokens[-1].id
        assert card._selected_token_range is None

    def test_enter_key_triggers_idiom_modal_when_selected(self, db_session, qtbot, monkeypatch):
        card, tokens, idiom = self._create_card_with_idiom(db_session, qtbot)
        card._handle_idiom_selection_click(tokens[0].order_index)
        card._handle_idiom_selection_click(tokens[1].order_index)

        idiom_calls = []
        token_calls = []
        monkeypatch.setattr(card, "_open_idiom_modal", lambda i: idiom_calls.append(i))
        monkeypatch.setattr(card, "_open_token_modal", lambda t: token_calls.append(t))

        card._open_annotation_modal()

        assert idiom_calls and idiom_calls[0].id == idiom.id
        assert token_calls == []

    def test_double_click_unsaved_idiom_selection_opens_idiom_modal(
        self, db_session, qtbot, monkeypatch
    ):
        """
        Test that double-clicking a token within an active (unsaved) idiom selection
        correctly opens the idiom annotation modal instead of clearing the selection.
        """
        project = create_test_project(
            db_session, name="TestDouble", text="for ðan þǣr is wōp"
        )
        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)
        qtbot.addWidget(card)
        card._render_oe_text_with_superscripts()
        card.show()

        tokens = list(card.tokens)
        for_idx = tokens[0].order_index
        ðan_idx = tokens[1].order_index

        # 1. Cmd-Click "for"
        monkeypatch.setattr(card, "_find_token_at_position", lambda _: for_idx)
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.ControlModifier)

        # 2. Cmd-Click "ðan"
        monkeypatch.setattr(card, "_find_token_at_position", lambda _: ðan_idx)
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.ControlModifier)

        assert card._selected_token_range == (for_idx, ðan_idx)

        # 3. Double-click "for" (no modifiers)
        # First click of double-click
        monkeypatch.setattr(card, "_find_token_at_position", lambda _: for_idx)
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.NoModifier)

        # Second click / Double-click event
        idiom_calls = []
        token_calls = []
        monkeypatch.setattr(card, "_open_new_idiom_modal", lambda s, e: idiom_calls.append((s, e)))
        monkeypatch.setattr(card, "_open_token_modal", lambda t: token_calls.append(t))
        card._on_oe_text_double_clicked(QPoint(0, 0))

        assert len(idiom_calls) == 1
        assert idiom_calls[0] == (for_idx, ðan_idx)

    def test_enter_key_on_non_idiom_token_opens_token_modal(
        self, db_session, qtbot, monkeypatch
    ):
        project = create_test_project(db_session, name="TokenOnly", text="Se cyning fēoll")
        sentence = project.sentences[0]
        card = SentenceCard(sentence, parent=None)
        qtbot.addWidget(card)
        card._render_oe_text_with_superscripts()
        tokens = list(card.tokens)
        token = tokens[0]

        card._selected_token_range = None
        card.selected_token_index = token.order_index
        card.idioms = []

        idiom_calls = []
        token_calls = []
        monkeypatch.setattr(card, "_open_idiom_modal", lambda i: idiom_calls.append(i))
        monkeypatch.setattr(card, "_open_token_modal", lambda t: token_calls.append(t))

        card._open_annotation_modal()

        assert idiom_calls == []
        assert token_calls

    def test_add_note_button_enabled_only_for_shift_click(self, db_session, qtbot):
        """Test that Add Note button is only enabled for Shift-Click sequences."""
        card, tokens, idiom = self._create_card_with_idiom(db_session, qtbot)

        # Initially disabled
        assert not card.add_note_button.isEnabled()

        # Setup mock for _find_token_at_position
        current_order = 0
        card._find_token_at_position = lambda _: current_order

        # 1. Normal click on a token - should be disabled
        current_order = tokens[2].order_index
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.NoModifier)
        assert not card.add_note_button.isEnabled()

        # 2. Cmd-Click (idiom selection) - should be disabled
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.MetaModifier)
        assert not card.add_note_button.isEnabled()

        # 3. Normal click on a saved idiom - should be disabled
        current_order = tokens[0].order_index
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.NoModifier)
        assert card._selected_token_range is not None # Idiom selected
        assert not card.add_note_button.isEnabled()

        # 4. Shift-Click sequence - should be enabled
        # Click first token
        current_order = tokens[2].order_index
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.NoModifier)
        # Shift-click second token
        current_order = tokens[3].order_index
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.ShiftModifier)
        assert card._selected_token_range == (tokens[2].order_index, tokens[3].order_index)
        assert card.add_note_button.isEnabled()

        # 5. Clicking away - should be disabled again
        current_order = tokens[0].order_index
        card._on_oe_text_clicked(QPoint(0, 0), Qt.KeyboardModifier.NoModifier)
        assert not card.add_note_button.isEnabled()

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

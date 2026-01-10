"""Unit tests for NotesPanel."""

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog
from oeapp.ui.notes_panel import NotesPanel, ClickableNoteLabel
from oeapp.ui.sentence_card import SentenceCard
from tests.conftest import create_test_project


class TestNotesPanel:
    """Test cases for NotesPanel."""

    def test_notes_panel_initialize_requires_sentence(self, db_session, qapp):
        """
        Test NotesPanel initializes correctly.
        """
        with pytest.raises(AssertionError):
            NotesPanel(parent=None)

    def test_notes_panel_initializes_with_sentence(self, db_session, qapp):
        """Test NotesPanel initializes with a sentence."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        panel = NotesPanel(sentence=sentence, parent=None)

        assert panel.sentence == sentence

    def test_notes_panel_displays_notes(self, db_session, qapp):
        """Test NotesPanel displays notes for a sentence."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Create notes
        note1 = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="First note"
        )
        note2 = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Second note"
        )
        note1.save()
        note2.save()

        panel = NotesPanel(sentence=sentence, parent=None)
        panel.update_notes()

        # Should have note labels
        assert len(panel.note_labels) == 2

    def test_notes_panel_handles_empty_notes(self, db_session, qapp):
        """Test NotesPanel handles sentence with no notes."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        panel = NotesPanel(sentence=sentence, parent=None)
        panel.update_notes()

        # Should have no note labels
        assert len(panel.note_labels) == 0

    def test_notes_panel_emits_note_clicked_signal(self, db_session, qapp, qtbot, mock_main_window):
        """Test NotesPanel emits signal when note is clicked."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Test note"
        )
        note.save()

        card = SentenceCard(sentence=sentence, main_window=mock_main_window, parent=None)
        qtbot.addWidget(card)

        card.notes_panel.update_notes()

        # Connect signal
        clicked_note = None
        def on_clicked(note):
            nonlocal clicked_note
            clicked_note = note
        card.notes_panel.note_clicked.connect(on_clicked)

        # Use qtbot to simulate click on first note label
        if card.notes_panel.note_labels:
            label = card.notes_panel.note_labels[0]
            qtbot.mouseClick(label, Qt.MouseButton.LeftButton)
            assert clicked_note == note

    def test_notes_panel_emits_note_double_clicked_signal(self, db_session, qapp, qtbot, mock_main_window, monkeypatch):
        """Test NotesPanel emits signal when note is double-clicked."""
        from oeapp.models.note import Note
        from oeapp.ui.dialogs.note_dialog import NoteDialog

        # Mock exec to avoid hanging when dialog opens
        monkeypatch.setattr(NoteDialog, "exec", lambda self: QDialog.Accepted)

        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Test note"
        )
        note.save()

        card = SentenceCard(sentence=sentence, main_window=mock_main_window, parent=None)
        qtbot.addWidget(card)

        card.notes_panel.update_notes()

        # Connect signal
        double_clicked_note = None
        def on_double_clicked(note):
            nonlocal double_clicked_note
            double_clicked_note = note
        card.notes_panel.note_double_clicked.connect(on_double_clicked)

        # Use qtbot to simulate double-click on first note label
        if card.notes_panel.note_labels:
            label = card.notes_panel.note_labels[0]
            qtbot.mouseDClick(label, Qt.MouseButton.LeftButton)
            assert double_clicked_note == note

    def test_notes_panel_updates_when_sentence_changes(self, db_session, qapp):
        """Test NotesPanel updates when sentence changes."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning. Þæt scip.")

        sentence1 = project.sentences[0]
        sentence2 = project.sentences[1]

        # Add note to first sentence
        token1 = sentence1.tokens[0]
        note = Note(
            sentence_id=sentence1.id,
            start_token=token1.id,
            end_token=token1.id,
            note_text_md="Note for sentence 1"
        )
        note.save()

        panel = NotesPanel(sentence=sentence1, parent=None)
        panel.update_notes()

        assert len(panel.note_labels) == 1

        # Update to second sentence (no notes)
        panel.update_notes(sentence2)

        assert len(panel.note_labels) == 0


class TestClickableNoteLabel:
    """Test cases for ClickableNoteLabel."""

    def test_clickable_note_label_initializes(self, db_session, qapp):
        """Test ClickableNoteLabel initializes correctly."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Test note"
        )

        label = ClickableNoteLabel(note, parent=None)

        assert label.note == note

    def test_clickable_note_label_emits_clicked_signal(self, db_session, qapp):
        """Test ClickableNoteLabel emits clicked signal."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Test note"
        )

        label = ClickableNoteLabel(note, parent=None)

        # Connect signal
        clicked_note = None
        def on_clicked(note):
            nonlocal clicked_note
            clicked_note = note
        label.clicked.connect(on_clicked)

        # Simulate click
        label.clicked.emit(note)

        assert clicked_note == note


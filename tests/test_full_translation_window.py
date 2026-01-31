import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QLabel

from oeapp.ui.full_translation_window import FullTranslationWindow, NOTE_HIGHLIGHT_PROPERTY, FullProjectNotesArea
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.note import Note
from oeapp.models.token import Token

@pytest.fixture
def full_window(qapp, db_session, mock_main_window):
    """Fixture to create a FullTranslationWindow instance."""
    project = Project.create(name="Test Project", text="First sentence. Second sentence.")
    window = FullTranslationWindow(project, mock_main_window)
    return window

class TestFullTranslationWindow:
    def test_initialization(self, full_window):
        """Test that the window initializes with the correct title and components."""
        assert "Full Translation - Test Project" in full_window.windowTitle()
        assert full_window.oe_edit is not None
        assert full_window.mode_edit is not None
        assert full_window.splitter is not None

    def test_rendering_sentences(self, full_window):
        """Test that sentences are rendered in both OE and ModE edits."""
        oe_text = full_window.oe_edit.toPlainText()
        assert "First sentence" in oe_text
        assert "Second sentence" in oe_text

        # Initially modern text might be empty or placeholders if not set
        mode_text = full_window.mode_edit.toPlainText()
        assert "[...]" in mode_text

    def test_note_collection_and_numbering(self, db_session, mock_main_window):
        """Test that notes are collected and numbered correctly across sentences."""
        project = Project.create(name="Note Project", text="Sentence one. Sentence two.")
        s1 = project.sentences[0]
        s2 = project.sentences[1]

        # Add notes to sentence 1
        t1_1 = s1.tokens[0]
        n1 = Note(sentence_id=s1.id, start_token=t1_1.id, end_token=t1_1.id, note_text_md="Note 1")
        n1.save()

        t1_2 = s1.tokens[1]
        n2 = Note(sentence_id=s1.id, start_token=t1_2.id, end_token=t1_2.id, note_text_md="Note 2")
        n2.save()

        # Add note to sentence 2
        t2_1 = s2.tokens[0]
        n3 = Note(sentence_id=s2.id, start_token=t2_1.id, end_token=t2_1.id, note_text_md="Note 3")
        n3.save()

        db_session.refresh(s1)
        db_session.refresh(s2)

        window = FullTranslationWindow(project, mock_main_window)

        assert hasattr(window, "notes_area")
        assert len(window.project_notes) == 3
        assert window.project_notes[0][0] == 1
        assert window.project_notes[1][0] == 2
        assert window.project_notes[2][0] == 3

        # Check if note widgets are created
        assert len(window.notes_area.note_widgets) == 3
        assert 1 in window.notes_area.note_widgets
        assert 2 in window.notes_area.note_widgets
        assert 3 in window.notes_area.note_widgets

    def test_note_highlighting_interaction(self, full_window, db_session):
        """Test that clicking a note highlights its tokens."""
        # Add a note for testing
        s1 = full_window.project.sentences[0]
        t1 = s1.tokens[0]
        note = Note(sentence_id=s1.id, start_token=t1.id, end_token=t1.id, note_text_md="Test Note")
        note.save()
        db_session.refresh(s1)

        # Re-initialize to pick up the note
        full_window._collect_project_notes()
        full_window.oe_edit.render_readonly_text()
        full_window.notes_area = FullProjectNotesArea(full_window.project_notes, full_window)
        full_window.notes_area.note_clicked.connect(full_window._on_note_clicked)

        note_num = full_window.project_notes[0][0]

        # Initial state: not highlighted
        assert not full_window.notes_area.note_widgets[note_num].is_selected

        # Click the note
        full_window._on_note_clicked(note_num)
        assert full_window.notes_area.note_widgets[note_num].is_selected

        # Verify OE edit has note highlights
        selections = full_window.oe_edit.extraSelections()
        note_highlights = [s for s in selections if s.format.property(NOTE_HIGHLIGHT_PROPERTY) == note.id]
        assert len(note_highlights) > 0

        # Click again to unhighlight
        full_window._on_note_clicked(note_num)
        assert not full_window.notes_area.note_widgets[note_num].is_selected
        selections = full_window.oe_edit.extraSelections()
        note_highlights = [s for s in selections if s.format.property(14) == note.id]
        assert len(note_highlights) == 0

    def test_search_notes(self, full_window, db_session):
        """Test that searching highlights text in notes."""
        s1 = full_window.project.sentences[0]
        t1 = s1.tokens[0]
        note = Note(sentence_id=s1.id, start_token=t1.id, end_token=t1.id, note_text_md="FindMe")
        note.save()
        db_session.refresh(s1)

        full_window._collect_project_notes()
        full_window.notes_area = FullProjectNotesArea(full_window.project_notes, full_window)

        # Search for "FindMe"
        full_window._on_search_changed("FindMe")

        # Check if the label in the note widget contains the highlight span
        note_num = full_window.project_notes[0][0]
        label_text = full_window.notes_area.note_widgets[note_num].label.text()
        assert '<span style="background-color: #ffeb3b; color: black;">FindMe</span>' in label_text

    def test_note_deselection_on_token_click(self, full_window, db_session):
        """Test that selecting a token deselects any active note."""
        s1 = full_window.project.sentences[0]
        t1 = s1.tokens[0]
        note = Note(sentence_id=s1.id, start_token=t1.id, end_token=t1.id, note_text_md="Test Note")
        note.save()
        db_session.refresh(s1)

        full_window._collect_project_notes()
        full_window.notes_area = FullProjectNotesArea(full_window.project_notes, full_window)
        full_window.notes_area.note_clicked.connect(full_window._on_note_clicked)

        note_num = full_window.project_notes[0][0]

        # Select the note
        full_window._on_note_clicked(note_num)
        assert full_window.notes_area.note_widgets[note_num].is_selected

        # Simulate token selection in OE edit
        full_window._on_token_selected(t1)

        # Verify note is deselected
        assert not full_window.notes_area.note_widgets[note_num].is_selected
        selections = full_window.oe_edit.extraSelections()
        note_highlights = [s for s in selections if s.format.property(NOTE_HIGHLIGHT_PROPERTY) == note.id]
        assert len(note_highlights) == 0

    def test_note_deselection_on_mode_sentence_click(self, full_window, db_session):
        """Test that selecting a modern English sentence deselects any active note."""
        s1 = full_window.project.sentences[0]
        t1 = s1.tokens[0]
        note = Note(sentence_id=s1.id, start_token=t1.id, end_token=t1.id, note_text_md="Test Note")
        note.save()
        db_session.refresh(s1)

        full_window._collect_project_notes()
        full_window.notes_area = FullProjectNotesArea(full_window.project_notes, full_window)
        full_window.notes_area.note_clicked.connect(full_window._on_note_clicked)

        note_num = full_window.project_notes[0][0]

        # Select the note
        full_window._on_note_clicked(note_num)
        assert full_window.notes_area.note_widgets[note_num].is_selected

        # Simulate sentence selection in ModE edit
        full_window._on_mode_sentence_selected(s1.id)

        # Verify note is deselected
        assert not full_window.notes_area.note_widgets[note_num].is_selected
        selections = full_window.oe_edit.extraSelections()
        note_highlights = [s for s in selections if s.format.property(NOTE_HIGHLIGHT_PROPERTY) == note.id]
        assert len(note_highlights) == 0

    def test_no_notes(self, db_session, mock_main_window):
        """Test the window with a project that has no notes."""
        project = Project.create(name="No Note Project", text="Sentence one.")
        window = FullTranslationWindow(project, mock_main_window)

        assert len(window.project_notes) == 0
        # Should show the "No notes" label
        found_no_notes_label = False
        for i in range(window.notes_area.main_layout.count()):
            widget = window.notes_area.main_layout.itemAt(i).widget()
            if isinstance(widget, QLabel) and "No notes" in widget.text():
                found_no_notes_label = True
                break
        assert found_no_notes_label

    def test_project_metadata_banner(self, db_session, mock_main_window):
        """Test that project metadata (source, translator, notes) is displayed in the banner."""
        project = Project.create(
            name="Metadata Project",
            text="Sentence one.",
            source="Test Source",
            translator="Test Translator",
            notes="These are some project notes that should be long enough to wrap and be limited in width."
        )
        window = FullTranslationWindow(project, mock_main_window)

        assert hasattr(window, "source_banner")
        assert window.source_label.text() == "<b>Source:</b> Test Source"
        assert window.translator_label.text() == "<b>Translator:</b> <i>Test Translator</i>"
        assert window.notes_label.text() == f"<i>{project.notes}</i>"

        # Verify width constraint and wrapping
        assert window.notes_label.wordWrap() is True
        assert window.notes_label.maximumWidth() == 800

    def test_banner_visibility_with_only_notes(self, db_session, mock_main_window):
        """Test that the banner is visible even if only project notes are present."""
        project = Project.create(
            name="Notes Only Project",
            text="Sentence one.",
            notes="Only notes here."
        )
        window = FullTranslationWindow(project, mock_main_window)

        assert hasattr(window, "source_banner")
        assert not hasattr(window, "source_label")
        assert not hasattr(window, "translator_label")
        assert window.notes_label.text() == "<i>Only notes here.</i>"

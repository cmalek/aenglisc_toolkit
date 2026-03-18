import pytest
from unittest.mock import MagicMock
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QScrollArea, QVBoxLayout, QLabel

from oeapp.ui.full_translation_window import FullTranslationWindow, NOTE_HIGHLIGHT_PROPERTY, FullProjectNotesArea
from oeapp.models.chapter import Chapter
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
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
        assert window.show_notes_btn.isEnabled() is False
        # Should show the "No notes" label
        found_no_notes_label = False
        for i in range(window.notes_area.main_layout.count()):
            widget = window.notes_area.main_layout.itemAt(i).widget()
            if isinstance(widget, QLabel) and "No notes" in widget.text():
                found_no_notes_label = True
                break
        assert found_no_notes_label

    def test_project_metadata_banner(self, db_session, mock_main_window):
        """Test that source/translator metadata appears in the banner, but notes do not."""
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
        assert not hasattr(window, "notes_label")
        assert window.show_notes_btn.isEnabled() is True

    def test_banner_visibility_with_only_notes(self, db_session, mock_main_window):
        """Notes-only projects should not render a body banner."""
        project = Project.create(
            name="Notes Only Project",
            text="Sentence one.",
            notes="Only notes here."
        )
        window = FullTranslationWindow(project, mock_main_window)

        assert not hasattr(window, "source_banner")
        assert window.show_notes_btn.isEnabled() is True

    def test_show_notes_button_is_left_of_show_details(self, full_window):
        """Show notes button should appear before Show Details in the toolbar."""
        notes_index = full_window.toolbar_layout.indexOf(full_window.show_notes_btn)
        details_index = full_window.toolbar_layout.indexOf(full_window.toggle_sidebar_btn)
        assert notes_index < details_index

    def test_show_notes_dialog_non_modal(self, db_session, mock_main_window):
        """Show notes should open a non-modal dialog with project notes text."""
        project = Project.create(
            name="Dialog Notes Project",
            text="Sentence one.",
            notes="Line one.\nLine two."
        )
        window = FullTranslationWindow(project, mock_main_window)
        window._show_project_notes()

        assert window.project_notes_dialog is not None
        assert window.project_notes_dialog.isModal() is False
        assert window.project_notes_dialog.windowModality() == Qt.WindowModality.NonModal
        assert window.project_notes_dialog.isVisible() is True
        assert window.project_notes_dialog_text is not None
        assert window.project_notes_dialog_text.toPlainText() == project.notes

    def test_export_button_uses_pdf_label(self, full_window):
        """The Full Translation toolbar export button should target PDF."""
        assert full_window.export_btn.text() == "Export PDF"

    def test_export_pdf_invokes_pdf_exporter(self, full_window, monkeypatch):
        """Export action should call the PDF exporter with selected path."""
        selected_path = "/tmp/test-full-translation.pdf"
        calls: list[tuple[int, Path]] = []
        open_calls: list[str] = []

        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (selected_path, "PDF Files (*.pdf)"),
        )

        def fake_export(self, project_id: int, output_path: Path) -> bool:
            calls.append((project_id, output_path))
            return True

        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.FullTranslationPDFExporter.export_side_by_side_pdf",
            fake_export,
        )
        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.QDesktopServices.openUrl",
            lambda url: open_calls.append(url.toLocalFile()) or True,
        )

        full_window._export_pdf()

        assert calls == [(full_window.project.id, Path(selected_path))]
        assert open_calls == [str(Path(selected_path).resolve())]
        full_window.main_window.messages.show_message.assert_called_once()
        full_window.main_window.messages.show_warning.assert_not_called()

    def test_export_pdf_warns_when_auto_open_fails(self, full_window, monkeypatch):
        """Successful export should warn if the PDF cannot be opened automatically."""
        selected_path = "/tmp/test-full-translation.pdf"

        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (selected_path, "PDF Files (*.pdf)"),
        )
        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.FullTranslationPDFExporter.export_side_by_side_pdf",
            lambda *args, **kwargs: True,
        )
        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.QDesktopServices.openUrl",
            lambda url: False,
        )

        full_window._export_pdf()

        full_window.main_window.messages.show_message.assert_called_once()
        full_window.main_window.messages.show_warning.assert_called_once()
        args, kwargs = full_window.main_window.messages.show_warning.call_args
        assert "could not be opened automatically" in args[0]
        assert selected_path in args[0]
        assert kwargs["title"] == "Open Exported PDF Failed"

    def test_export_pdf_failure_shows_detailed_error(self, full_window, monkeypatch):
        """Failed export should display exporter-provided error details."""
        selected_path = "/tmp/test-full-translation.pdf"

        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (selected_path, "PDF Files (*.pdf)"),
        )

        def fake_export(self, project_id: int, output_path: Path) -> bool:  # noqa: ARG001
            self.last_error = "Bundled Tectonic binary is missing."
            return False

        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.FullTranslationPDFExporter.export_side_by_side_pdf",
            fake_export,
        )
        open_url = MagicMock()
        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.QDesktopServices.openUrl",
            open_url,
        )

        full_window._export_pdf()

        full_window.main_window.messages.show_error.assert_called_once()
        open_url.assert_not_called()
        args, kwargs = full_window.main_window.messages.show_error.call_args
        assert "Bundled Tectonic binary is missing." in args[0]
        assert kwargs["title"] == "PDF Export Failed"

    def test_full_translation_hides_auto_titles_and_renders_gapless_verse(
        self, db_session, mock_main_window
    ):
        """Official titles render while auto titles are suppressed; verse stays gapless."""
        project = Project(name="Verse Layout")
        project.save()
        chapter1 = Chapter.create(
            project_id=project.id,
            number=1,
            title="Official Chapter",
            title_auto=False,
            commit=False,
        )
        section1 = Section.create(
            chapter_id=chapter1.id,
            number=1,
            title="Official Section",
            title_auto=False,
            commit=False,
        )
        p1 = Paragraph(section_id=section1.id, order=1)
        p2 = Paragraph(section_id=section1.id, order=2)
        db_session.add_all([p1, p2])
        db_session.flush()
        Sentence.create(
            project_id=project.id,
            display_order=1,
            text_oe="a1\na2\na3\na4\na5",
            paragraph_id=p1.id,
            verse_line_start=1,
            verse_line_end=5,
            commit=False,
        )
        Sentence.create(
            project_id=project.id,
            display_order=2,
            text_oe="b1\nb2\nb3\nb4\nb5",
            paragraph_id=p2.id,
            verse_line_start=6,
            verse_line_end=10,
            commit=False,
        )

        chapter2 = Chapter.create(
            project_id=project.id,
            number=2,
            title="Auto Chapter ....",
            title_auto=True,
            commit=False,
        )
        section2 = Section.create(
            chapter_id=chapter2.id,
            number=1,
            title="Lines 11-15",
            title_auto=True,
            commit=False,
        )
        p3 = Paragraph(section_id=section2.id, order=1)
        db_session.add(p3)
        db_session.flush()
        Sentence.create(
            project_id=project.id,
            display_order=3,
            text_oe="prose sentence",
            paragraph_id=p3.id,
            commit=False,
        )
        db_session.commit()

        window = FullTranslationWindow(project, mock_main_window)
        oe_text = window.oe_edit.toPlainText()
        mode_text = window.mode_edit.toPlainText()

        assert "Official Chapter" in oe_text
        assert "Official Section" in oe_text
        assert "Auto Chapter ...." not in oe_text
        assert "Lines 11-15" not in oe_text
        assert "    a1" in oe_text
        assert "a5\n5\n    b1" in oe_text
        assert "a5\n5\n\n    b1" not in oe_text
        assert "Official Chapter" in mode_text
        assert "    [...]" in mode_text

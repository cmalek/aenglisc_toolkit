import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from oeapp.db import get_runtime_session
from oeapp.services.pdf_engine import PDFEngineError
from oeapp.models.chapter import Chapter
from oeapp.models.note import Note
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence
from oeapp.ui.pdf_export_job import PdfExportJob
from oeapp.ui.full_translation_window import (
    NOTE_HIGHLIGHT_PROPERTY,
    FullProjectNotesArea,
    FullTranslationWindow,
)
from oeapp.ui.highlighting import SearchHighlighter
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import QLabel


@pytest.fixture
def full_window(qapp, db_session, mock_main_window):
    """Fixture to create a FullTranslationWindow instance."""
    session = get_runtime_session()
    project = Project.create(
        name="Test Project", text="First sentence. Second sentence.", session=session
    )
    window = FullTranslationWindow(project, mock_main_window)
    return window


def _stub_async_pdf_export(
    monkeypatch: pytest.MonkeyPatch, *, opened: bool
) -> tuple[str, list[tuple[int, Path]], list[object], list[str]]:
    """Stub the file dialog, LaTeX prepare, and QProcess start."""
    selected_path = "/tmp/test-full-translation.pdf"
    calls: list[tuple[int, Path]] = []
    jobs: list[object] = []
    open_calls: list[str] = []

    monkeypatch.setattr(
        "oeapp.ui.full_translation_window.QFileDialog.getSaveFileName",
        lambda *args, **kwargs: (selected_path, "PDF Files (*.pdf)"),
    )

    def fake_prepare(
        self: object, project_id: int, output_path: Path
    ) -> tuple[Path, Path]:
        calls.append((project_id, output_path))
        return Path("/tmp/pdf-work"), Path("/tmp/pdf-work/full_translation.tex")

    monkeypatch.setattr(
        "oeapp.ui.full_translation_window.FullTranslationPDFExporter.prepare_side_by_side_tex",
        fake_prepare,
    )
    monkeypatch.setattr(
        "oeapp.ui.full_translation_window.tectonic_compile_command",
        lambda tex_path, work_dir: ["/usr/bin/true", str(tex_path)],
    )
    monkeypatch.setattr(
        "oeapp.ui.full_translation_window.FullTranslationPDFExporter.finalize_side_by_side_pdf",
        lambda self, *args, **kwargs: True,
    )

    def fake_start(self: object, program: str, arguments: list[str]) -> None:
        jobs.append(self)

    monkeypatch.setattr(
        "oeapp.ui.full_translation_window.PdfExportJob.start",
        fake_start,
    )
    monkeypatch.setattr(
        "oeapp.ui.full_translation_window.QDesktopServices.openUrl",
        lambda url: open_calls.append(url.toLocalFile()) or opened,
    )
    return selected_path, calls, jobs, open_calls


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
        session = get_runtime_session()
        project = Project.create(
            name="Note Project", text="Sentence one. Sentence two.", session=session
        )
        s1 = project.sentences[0]
        s2 = project.sentences[1]

        # Add notes to sentence 1
        t1_1 = s1.tokens[0]
        n1 = Note(
            sentence_id=s1.id,
            start_token=t1_1.id,
            end_token=t1_1.id,
            note_text_md="Note 1",
        )
        n1.save()

        t1_2 = s1.tokens[1]
        n2 = Note(
            sentence_id=s1.id,
            start_token=t1_2.id,
            end_token=t1_2.id,
            note_text_md="Note 2",
        )
        n2.save()

        # Add note to sentence 2
        t2_1 = s2.tokens[0]
        n3 = Note(
            sentence_id=s2.id,
            start_token=t2_1.id,
            end_token=t2_1.id,
            note_text_md="Note 3",
        )
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
        note = Note(
            sentence_id=s1.id,
            start_token=t1.id,
            end_token=t1.id,
            note_text_md="Test Note",
        )
        note.save()
        db_session.refresh(s1)

        # Re-initialize to pick up the note
        full_window._collect_project_notes()
        full_window.oe_edit.render_readonly_text()
        full_window.notes_area = FullProjectNotesArea(
            full_window.project_notes, full_window
        )
        full_window.notes_area.note_clicked.connect(full_window._on_note_clicked)

        note_num = full_window.project_notes[0][0]

        # Initial state: not highlighted
        assert not full_window.notes_area.note_widgets[note_num].is_selected

        # Click the note
        full_window._on_note_clicked(note_num)
        assert full_window.notes_area.note_widgets[note_num].is_selected

        # Verify OE edit has note highlights
        selections = full_window.oe_edit.extraSelections()
        note_highlights = [
            s
            for s in selections
            if s.format.property(NOTE_HIGHLIGHT_PROPERTY) == note.id
        ]
        assert len(note_highlights) > 0

        # Click again to unhighlight
        full_window._on_note_clicked(note_num)
        assert not full_window.notes_area.note_widgets[note_num].is_selected
        selections = full_window.oe_edit.extraSelections()
        note_highlights = [s for s in selections if s.format.property(14) == note.id]
        assert len(note_highlights) == 0

    def test_oe_edit_search_keeps_direct_path(self, full_window):
        """The full window's editor must not be captured by the layer path."""
        edit = full_window.oe_edit
        assert edit.uses_highlight_layers is False
        pattern = full_window.project.sentences[0].text_oe.split()[0][:2]

        assert SearchHighlighter.highlight_text(edit, pattern) > 0
        assert any(
            s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)
            for s in edit.extraSelections()
        )

        SearchHighlighter.clear_highlight(edit)
        assert not any(
            s.format.property(SearchHighlighter.SEARCH_HIGHLIGHT_PROPERTY)
            for s in edit.extraSelections()
        )

    def test_search_notes(self, full_window, db_session):
        """Test that searching highlights text in notes."""
        s1 = full_window.project.sentences[0]
        t1 = s1.tokens[0]
        note = Note(
            sentence_id=s1.id, start_token=t1.id, end_token=t1.id, note_text_md="FindMe"
        )
        note.save()
        db_session.refresh(s1)

        full_window._collect_project_notes()
        full_window.notes_area = FullProjectNotesArea(
            full_window.project_notes, full_window
        )

        # Search for "FindMe"
        full_window._on_search_changed("FindMe")

        # Check if the label in the note widget contains the highlight span
        note_num = full_window.project_notes[0][0]
        label_text = full_window.notes_area.note_widgets[note_num].label.text()
        assert (
            '<span style="background-color: #ffeb3b; color: black;">FindMe</span>'
            in label_text
        )

    def test_note_deselection_on_token_click(self, full_window, db_session):
        """Test that selecting a token deselects any active note."""
        s1 = full_window.project.sentences[0]
        t1 = s1.tokens[0]
        note = Note(
            sentence_id=s1.id,
            start_token=t1.id,
            end_token=t1.id,
            note_text_md="Test Note",
        )
        note.save()
        db_session.refresh(s1)

        full_window._collect_project_notes()
        full_window.notes_area = FullProjectNotesArea(
            full_window.project_notes, full_window
        )
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
        note_highlights = [
            s
            for s in selections
            if s.format.property(NOTE_HIGHLIGHT_PROPERTY) == note.id
        ]
        assert len(note_highlights) == 0

    def test_note_deselection_on_mode_sentence_click(self, full_window, db_session):
        """Test that selecting a modern English sentence deselects any active note."""
        s1 = full_window.project.sentences[0]
        t1 = s1.tokens[0]
        note = Note(
            sentence_id=s1.id,
            start_token=t1.id,
            end_token=t1.id,
            note_text_md="Test Note",
        )
        note.save()
        db_session.refresh(s1)

        full_window._collect_project_notes()
        full_window.notes_area = FullProjectNotesArea(
            full_window.project_notes, full_window
        )
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
        note_highlights = [
            s
            for s in selections
            if s.format.property(NOTE_HIGHLIGHT_PROPERTY) == note.id
        ]
        assert len(note_highlights) == 0

    def test_no_notes(self, db_session, mock_main_window):
        """Test the window with a project that has no notes."""
        session = get_runtime_session()
        project = Project.create(
            name="No Note Project", text="Sentence one.", session=session
        )
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
        session = get_runtime_session()
        project = Project.create(
            name="Metadata Project",
            text="Sentence one.",
            source="Test Source",
            translator="Test Translator",
            notes="These are some project notes that should be long enough to wrap and be limited in width.",
            session=session,
        )
        window = FullTranslationWindow(project, mock_main_window)

        assert hasattr(window, "source_banner")
        assert window.source_label.text() == "<b>Source:</b> Test Source"
        assert (
            window.translator_label.text()
            == "<b>Translator:</b> <i>Test Translator</i>"
        )
        assert not hasattr(window, "notes_label")
        assert window.show_notes_btn.isEnabled() is True

    def test_banner_visibility_with_only_notes(self, db_session, mock_main_window):
        """Notes-only projects should not render a body banner."""
        session = get_runtime_session()
        project = Project.create(
            name="Notes Only Project",
            text="Sentence one.",
            notes="Only notes here.",
            session=session,
        )
        window = FullTranslationWindow(project, mock_main_window)

        assert not hasattr(window, "source_banner")
        assert window.show_notes_btn.isEnabled() is True

    def test_show_notes_button_is_left_of_show_details(self, full_window):
        """Show notes button should appear before Show Details in the toolbar."""
        notes_index = full_window.toolbar_layout.indexOf(full_window.show_notes_btn)
        details_index = full_window.toolbar_layout.indexOf(
            full_window.toggle_sidebar_btn
        )
        assert notes_index < details_index

    def test_show_notes_dialog_non_modal(self, db_session, mock_main_window):
        """Show notes should open a non-modal dialog with project notes text."""
        session = get_runtime_session()
        project = Project.create(
            name="Dialog Notes Project",
            text="Sentence one.",
            notes="Line one.\nLine two.",
            session=session,
        )
        window = FullTranslationWindow(project, mock_main_window)
        window._show_project_notes()

        assert window.project_notes_dialog is not None
        assert window.project_notes_dialog.isModal() is False
        assert (
            window.project_notes_dialog.windowModality() == Qt.WindowModality.NonModal
        )
        assert window.project_notes_dialog.isVisible() is True
        assert window.project_notes_dialog_text is not None
        assert window.project_notes_dialog_text.toPlainText() == project.notes

    def test_export_button_uses_pdf_label(self, full_window):
        """The Full Translation toolbar export button should target PDF."""
        assert full_window.export_btn.text() == "Export PDF"

    def test_export_pdf_invokes_pdf_exporter(self, full_window, monkeypatch):
        """Export action should prepare LaTeX and open the PDF after compile."""
        selected_path, calls, jobs, open_calls = _stub_async_pdf_export(
            monkeypatch, opened=True
        )

        full_window._export_pdf()
        jobs[0].finished.emit(False, 0, "", "")

        assert calls == [(full_window.project.id, Path(selected_path))]
        assert open_calls == [str(Path(selected_path).resolve())]
        full_window.main_window.messages.show_message.assert_called_once()
        full_window.main_window.messages.show_warning.assert_not_called()

    def test_export_pdf_warns_when_auto_open_fails(self, full_window, monkeypatch):
        """Successful export should warn if the PDF cannot be opened automatically."""
        selected_path, _calls, jobs, _open_calls = _stub_async_pdf_export(
            monkeypatch, opened=False
        )

        full_window._export_pdf()
        jobs[0].finished.emit(False, 0, "", "")

        full_window.main_window.messages.show_message.assert_called_once()
        full_window.main_window.messages.show_warning.assert_called_once()
        args, kwargs = full_window.main_window.messages.show_warning.call_args
        assert "could not be opened automatically" in args[0]
        assert selected_path in args[0]
        assert kwargs["title"] == "Open Exported PDF Failed"

    def test_export_pdf_failure_shows_detailed_error(self, full_window, monkeypatch):
        """A missing Tectonic binary should display the engine error."""
        selected_path = "/tmp/test-full-translation.pdf"

        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.QFileDialog.getSaveFileName",
            lambda *args, **kwargs: (selected_path, "PDF Files (*.pdf)"),
        )
        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.FullTranslationPDFExporter.prepare_side_by_side_tex",
            lambda self, project_id, output_path: (
                Path("/tmp/pdf-work"),
                Path("/tmp/pdf-work/full_translation.tex"),
            ),
        )

        def missing_binary(tex_path: Path, work_dir: Path) -> list[str]:
            raise PDFEngineError("Bundled Tectonic binary is missing.")

        monkeypatch.setattr(
            "oeapp.ui.full_translation_window.tectonic_compile_command",
            missing_binary,
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

    def test_close_stops_the_pdf_process(self, full_window, tmp_path: Path):
        """Closing the window kills Tectonic before the process object is destroyed."""
        job = PdfExportJob(full_window)
        full_window._pdf_job = job
        work = tmp_path / "pdf-work"
        work.mkdir()
        full_window._pdf_work_dir = work
        job.finished.connect(full_window._on_pdf_finished)
        job._process.start(sys.executable, ["-c", "import time; time.sleep(30)"])
        assert job._process.waitForStarted(3000)
        pid = job._process.processId()
        assert pid > 0
        full_window.close()
        assert not work.exists()
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)

    def test_full_translation_hides_auto_titles_and_renders_gapless_verse(
        self, db_session, mock_main_window
    ):
        """Official titles render while auto titles are suppressed; verse stays gapless."""
        session = get_runtime_session()
        project = Project(name="Verse Layout")
        project.save()
        chapter1 = Chapter.create(
            project_id=project.id,
            number=1,
            title="Official Chapter",
            title_auto=False,
            commit=False,
            session=session,
        )
        section1 = Section.create(
            chapter_id=chapter1.id,
            number=1,
            title="Official Section",
            title_auto=False,
            commit=False,
            session=session,
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
            session=session,
        )
        Sentence.create(
            project_id=project.id,
            display_order=2,
            text_oe="b1\nb2\nb3\nb4\nb5",
            paragraph_id=p2.id,
            verse_line_start=6,
            verse_line_end=10,
            commit=False,
            session=session,
        )

        chapter2 = Chapter.create(
            project_id=project.id,
            number=2,
            title="Auto Chapter ....",
            title_auto=True,
            commit=False,
            session=session,
        )
        section2 = Section.create(
            chapter_id=chapter2.id,
            number=1,
            title="Lines 11-15",
            title_auto=True,
            commit=False,
            session=session,
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
            session=session,
        )
        db_session.commit()

        window = FullTranslationWindow(project, mock_main_window)
        oe_text = window.oe_edit.toPlainText()
        mode_text = window.mode_edit.toPlainText()

        assert "Official Chapter" not in oe_text
        assert "Official Section" not in oe_text
        assert "Auto Chapter ...." not in oe_text
        assert "Lines 11-15" not in oe_text
        assert "    a1" in oe_text
        assert "a5\n5\n    b1" in oe_text
        assert "a5\n5\n\n    b1" not in oe_text
        assert "Official Chapter" not in mode_text
        assert "    [...]" in mode_text


def _heading_project(session, roles, *, second_chapter_at=None):
    """
    Build a project whose sentence ``i`` has ``roles[i]`` as its heading role.

    Args:
        session: Runtime session.
        roles: One heading role (or ``None``) per sentence, in display order.

    Keyword Args:
        second_chapter_at: Sentence index that opens a second chapter.

    Returns:
        The saved project.

    """
    project = Project(name="Heading Layout")
    project.save()
    chapter = Chapter.create(
        project_id=project.id, number=1, commit=False, session=session
    )
    section = Section.create(
        chapter_id=chapter.id, number=1, commit=False, session=session
    )
    paragraph = Paragraph(section_id=section.id, order=1)
    session.add(paragraph)
    session.flush()
    for index, role in enumerate(roles):
        if index == second_chapter_at:
            chapter = Chapter.create(
                project_id=project.id, number=2, commit=False, session=session
            )
            section = Section.create(
                chapter_id=chapter.id, number=1, commit=False, session=session
            )
            paragraph = Paragraph(section_id=section.id, order=1)
            session.add(paragraph)
            session.flush()
        sentence = Sentence.create(
            project_id=project.id,
            display_order=index + 1,
            text_oe=f"Word{index}" if role is None else f"Head{index}",
            paragraph_id=paragraph.id,
            commit=False,
            session=session,
        )
        sentence.heading_role = role
    session.commit()
    return project


def _range_format(edit, sentence_id):
    """
    Return the block and character format at the start of a sentence's range.

    Args:
        edit: A full-translation text edit.
        sentence_id: Sentence to look up.

    Returns:
        ``(block_format, char_format)`` for the first character of the range.

    """
    start, end = edit.sentence_positions[sentence_id]
    doc = edit.document()
    cursor = QTextCursor(doc)
    cursor.setPosition(start + 1)
    return doc.findBlock(start).blockFormat(), cursor.charFormat()


class TestHeadingRendering:
    def test_first_chapter_heading_is_styled_in_both_columns(
        self, db_session, mock_main_window
    ):
        """A first-sentence chapter heading is bold capitals with a 4pt top margin."""
        project = _heading_project(
            db_session, ["chapter", None, "chapter"], second_chapter_at=2
        )
        window = FullTranslationWindow(project, mock_main_window)
        heading, body, second = project.sentences

        assert window.oe_edit.toPlainText().count("Head0") == 1
        assert window.mode_edit.toPlainText().startswith("Head0")
        assert "[...]" in window.mode_edit.toPlainText()
        for edit in (window.oe_edit, window.mode_edit):
            block, char = _range_format(edit, heading.id)
            assert char.fontCapitalization() == QFont.Capitalization.AllUppercase
            assert char.fontWeight() == QFont.Weight.Bold
            assert block.topMargin() == 4
            assert block.bottomMargin() == 16
            body_block, body_char = _range_format(edit, body.id)
            assert body_block.topMargin() == 0
            assert body_block.bottomMargin() == 0
            assert body_char.fontCapitalization() == QFont.Capitalization.MixedCase
            second_block, second_char = _range_format(edit, second.id)
            assert second_block.topMargin() == 22
            assert second_block.bottomMargin() == 16
            assert second_char.fontCapitalization() == QFont.Capitalization.AllUppercase
        assert "HEAD0" not in window.oe_edit.toPlainText()

    def test_later_chapter_heading_in_first_chapter_uses_22pt(
        self, db_session, mock_main_window
    ):
        """A chapter heading that is not the first sentence uses 22pt above."""
        project = _heading_project(db_session, [None, "chapter", None])
        window = FullTranslationWindow(project, mock_main_window)
        heading = project.sentences[1]

        for edit in (window.oe_edit, window.mode_edit):
            block, _char = _range_format(edit, heading.id)
            assert block.topMargin() == 22
            assert block.bottomMargin() == 16

    def test_section_and_subsection_styling(self, db_session, mock_main_window):
        """Section is bold in own case; subsection is italic, not bold."""
        project = _heading_project(
            db_session, ["chapter", "section", "subsection", None]
        )
        window = FullTranslationWindow(project, mock_main_window)
        _head, section, subsection, body = project.sentences

        for edit in (window.oe_edit, window.mode_edit):
            block, char = _range_format(edit, section.id)
            assert char.fontWeight() == QFont.Weight.Bold
            assert char.fontCapitalization() == QFont.Capitalization.MixedCase
            assert (block.topMargin(), block.bottomMargin()) == (12, 12)
            block, char = _range_format(edit, subsection.id)
            assert char.fontItalic()
            assert char.fontWeight() != QFont.Weight.Bold
            assert char.fontCapitalization() == QFont.Capitalization.MixedCase
            assert (block.topMargin(), block.bottomMargin()) == (6, 6)
            block, char = _range_format(edit, body.id)
            assert (block.topMargin(), block.bottomMargin()) == (0, 0)
            assert not char.fontItalic()

    def test_translated_heading_and_plain_sentence_bodies(
        self, db_session, mock_main_window
    ):
        """Modern text wins for a heading; body sentences keep ``[...]``."""
        project = _heading_project(db_session, ["chapter", None])
        project.sentences[0].text_modern = "The Beginning"
        project.sentences[1].text_modern = "   "
        db_session.commit()
        window = FullTranslationWindow(project, mock_main_window)

        mode_text = window.mode_edit.toPlainText()
        assert "The Beginning" in mode_text
        assert "Head0" not in mode_text
        assert "[...]" in mode_text
        assert "Word1" not in mode_text
        assert window.oe_edit.toPlainText().startswith("Head0")

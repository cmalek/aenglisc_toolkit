# ruff: noqa: ARG002, PLR2004, S101

from __future__ import annotations

from oeapp.models.note import Note
from oeapp.models.project import Project
from oeapp.models.token import Token
from oeapp.services.export_reading_text import ReadingTextExporter


def _mark_verse(sentence, start: int, end: int) -> None:
    sentence.verse_line_start = start
    sentence.verse_line_end = end


def _require_n_sentences(project: Project, n: int) -> None:
    assert len(project.sentences) == n, (
        f"splitter yielded {len(project.sentences)} sentences, need {n}; "
        "build with Sentence.create like tests/test_export_docx.py"
    )


class TestReadingTextExporter:
    def test_prose_uses_text_oe_without_notes(self, db_session) -> None:
        project = Project.create(name="Prose", text="Hwæt. We Gardena.")
        first = project.sentences[0]
        token = Token.list(first.id)[0]
        Note.create(
            sentence_id=first.id,
            start_token_id=token.id,
            end_token_id=token.id,
            note_text_md="should not appear",
        )
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert "Hwæt" in text
        assert "should not appear" not in text

    def test_omits_auto_titles_includes_manual(self, db_session) -> None:
        project = Project.create(name="Titles", text="Line one.")
        sentence = project.sentences[0]
        section = sentence.paragraph.section
        chapter = section.chapter
        chapter.title = "Auto Chapter"
        chapter.title_auto = True
        section.title = "Lines 1-25"
        section.title_auto = True
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert "Auto Chapter" not in text
        assert "Lines 1-25" not in text

        chapter.title = "Beowulf"
        chapter.title_auto = False
        section.title = "The opening"
        section.title_auto = False
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert text.startswith("Beowulf\nThe opening\n")

    def test_verse_indent_and_every_five_numbers(self, db_session) -> None:
        lines = " ".join(f"Line{i}." for i in range(1, 8))
        project = Project.create(name="Verse", text=lines)
        _require_n_sentences(project, 7)
        for i, sentence in enumerate(project.sentences, start=1):
            _mark_verse(sentence, i, i)
            sentence.text_oe = f"OE{i}"
        db_session.commit()
        text = ReadingTextExporter().render_old_english(project)
        assert "    OE1" in text
        assert "\n5\n" in text or text.endswith("\n5")
        assert "\n5\n    OE6" in text or "5\n    OE6" in text
        assert "\n7" not in text  # short remainder, no number

    def test_translation_empty_no_placeholder_no_number(self, db_session) -> None:
        lines = " ".join(f"Line{i}." for i in range(1, 6))
        project = Project.create(name="EmptyME", text=lines)
        _require_n_sentences(project, 5)
        for i, sentence in enumerate(project.sentences, start=1):
            _mark_verse(sentence, i, i)
            sentence.text_oe = f"OE{i}"
            sentence.text_modern = "ok" if i < 5 else None
        db_session.commit()
        text = ReadingTextExporter().render_translation(project)
        assert "[...]" not in text
        assert "ok" in text
        assert not text.rstrip().endswith("5")

    def test_translation_uses_modern_english_body(self, db_session) -> None:
        project = Project.create(name="MEBody", text="Hwæt.")
        project.sentences[0].text_modern = "Listen."
        db_session.commit()
        text = ReadingTextExporter().render_translation(project)
        assert "Listen." in text
        assert "Hwæt" not in text

    def test_write_utf8_forces_txt(self, db_session, tmp_path) -> None:
        project = Project.create(name="Write", text="A.")
        path = tmp_path / "out"
        exporter = ReadingTextExporter()
        exporter.write_utf8(path, exporter.render_old_english(project))
        written = tmp_path / "out.txt"
        assert written.exists()
        assert "A" in written.read_text(encoding="utf-8")

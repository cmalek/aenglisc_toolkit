"""Unit tests for shared text-flow rendering rules."""

# ruff: noqa: ARG002, S101

from __future__ import annotations

from oeapp.models.project import Project
from oeapp.models.text_flow import (
    SentenceSeparatorKind,
    is_paragraph_start,
    plain_text_separator,
    sentence_separator_kind,
    visible_titles,
)


class TestTextFlow:
    """Focused tests for oeapp.models.text_flow helpers."""

    def test_is_paragraph_start_true_for_first_sentence(self, db_session) -> None:
        """First sentence in paragraph order should be a paragraph start."""
        project = Project.create(name="Flow", text="Alpha. Beta.")
        sentence = project.sentences[0]
        assert is_paragraph_start(sentence) is True

    def test_is_paragraph_start_false_for_second_sentence(self, db_session) -> None:
        """Later sentences in the same paragraph should not be paragraph starts."""
        project = Project.create(name="Flow", text="Alpha. Beta.")
        assert is_paragraph_start(project.sentences[1]) is False

    def test_visible_titles_emits_manual_chapter_and_section(self, db_session) -> None:
        """Manual chapter/section titles should appear at boundaries."""
        project = Project.create(name="Titles", text="Line one.")
        sentence = project.sentences[0]
        section = sentence.paragraph.section
        chapter = section.chapter
        chapter.title = "Chapter Two"
        chapter.title_auto = False
        section.title = "Section One"
        section.title_auto = False
        db_session.commit()

        titles = visible_titles(None, sentence)
        assert titles == ["Chapter Two", "Section One"]

    def test_sentence_separator_kind_after_titles_is_none(self, db_session) -> None:
        """Title insertion should suppress inter-sentence separators."""
        project = Project.create(name="Titles gap", text="Only one.")
        sentence = project.sentences[0]
        assert (
            sentence_separator_kind(None, sentence, has_titles=True)
            is SentenceSeparatorKind.NONE
        )

    def test_plain_text_separator_maps_verse_line(self) -> None:
        """Verse-line separators should render as a single newline."""
        assert plain_text_separator(SentenceSeparatorKind.VERSE_LINE) == "\n"

    def test_sentence_separator_kind_verse_to_prose(self, db_session) -> None:
        """Prose after verse should use the prose-after-verse separator."""
        project = Project.create(name="Verse", text="Verse line. Prose line.")
        previous = project.sentences[0]
        current = project.sentences[1]
        previous.verse_line_start = 1
        previous.verse_line_end = 1
        current.verse_line_start = None
        current.verse_line_end = None
        db_session.commit()
        assert (
            sentence_separator_kind(previous, current, has_titles=False)
            is SentenceSeparatorKind.PROSE_AFTER_VERSE
        )

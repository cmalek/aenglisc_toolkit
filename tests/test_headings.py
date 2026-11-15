"""Tests for heading sentences."""

from __future__ import annotations

import pytest
from oeapp.models.chapter import Chapter
from oeapp.models.headings import (
    HeadingRole,
    allowed_role,
    apply_generated_title,
    apply_heading_title,
    heading_is_legal,
    is_opening_section,
    is_verse_section,
    section_index,
)
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence

from tests.conftest import create_test_sentence


def test_sentence_json_round_trips_heading_role(db_session) -> None:
    """A heading role is written to the sentence JSON."""
    sentence = create_test_sentence(db_session, text="Beowulf")
    sentence.heading_role = "chapter"
    sentence.save()
    assert sentence.to_json()["heading_role"] == "chapter"


def test_old_sentence_json_without_heading_role_imports(db_session) -> None:
    """Sentence JSON from files predating heading roles still imports."""
    sentence = create_test_sentence(db_session, text="Hwæt")
    payload = sentence.to_json()
    payload.pop("heading_role", None)
    lookup = {
        (
            sentence.paragraph.section.chapter.number,
            sentence.paragraph.section.number,
            sentence.paragraph.order,
        ): sentence.paragraph_id
    }
    project_id = sentence.project_id
    sentence.delete()
    imported = Sentence.from_json(project_id, payload, lookup, session=db_session)
    assert imported.heading_role is None


def _build(session, layout, chapter_number=1):
    """
    Build a chapter whose sections hold the sentences described by ``layout``.

    Args:
        session: SQLAlchemy session
        layout: One list per section; each item is ``True`` for a verse
            sentence and ``False`` for a prose sentence

    Keyword Args:
        chapter_number: The chapter number

    Returns:
        The chapter and a list of sentence lists, one per section

    """
    project = Project.create(text="", name=f"Headings {id(layout)}", session=session)
    chapter = Chapter(project_id=project.id, number=chapter_number)
    session.add(chapter)
    session.flush()
    order = 0
    result = []
    for number, flags in enumerate(layout, 1):
        section = Section(chapter_id=chapter.id, number=number)
        session.add(section)
        session.flush()
        paragraph = Paragraph(section_id=section.id, order=1)
        session.add(paragraph)
        session.flush()
        sentences = []
        for is_verse in flags:
            order += 1
            sentence = Sentence(
                project_id=project.id,
                paragraph_id=paragraph.id,
                display_order=order,
                text_oe=f"Sentence {order}",
                verse_line_start=order if is_verse else None,
                verse_line_end=order if is_verse else None,
            )
            session.add(sentence)
            sentences.append(sentence)
        session.flush()
        result.append(sentences)
    session.refresh(chapter)
    return chapter, result


class TestSlotRules:
    """Which heading a sentence slot allows."""

    def test_section_index_is_one_based_display_order(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        assert [section_index(s) for s in sections[0]] == [1, 2, 3]

    def test_opening_section_is_lowest_number(self, db_session):
        _, sections = _build(db_session, [[False], [False]])
        assert is_opening_section(sections[0][0]) is True
        assert is_opening_section(sections[1][0]) is False

    def test_is_verse_section(self, db_session):
        _, sections = _build(db_session, [[True, True], [True, False], []])
        assert is_verse_section(sections[0][0].paragraph.section) is True
        assert is_verse_section(sections[1][0].paragraph.section) is False
        empty = sections[0][0].paragraph.section.chapter.sections[2]
        assert is_verse_section(empty) is False

    def test_opening_allowed_index_one_is_chapter(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        assert allowed_role(sections[0][0]) == HeadingRole.CHAPTER

    def test_opening_allowed_index_two_needs_chapter_heading(self, db_session):
        _, sections = _build(db_session, [[False, False, False]])
        first, second, _third = sections[0]
        assert allowed_role(second) is None
        first.heading_role = "chapter"
        assert allowed_role(second) == HeadingRole.SECTION

    def test_opening_index_two_ignores_own_role(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        first.heading_role = "chapter"
        second.heading_role = "section"
        assert allowed_role(second) == HeadingRole.SECTION
        first.heading_role = None
        assert allowed_role(second) is None

    def test_opening_index_two_blocked_by_section_heading_on_first(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        sections[0][0].heading_role = "section"
        assert allowed_role(sections[0][1]) is None

    def test_opening_allowed_index_three_is_subsection(self, db_session):
        _, sections = _build(db_session, [[False, False, False, False]])
        assert allowed_role(sections[0][2]) == HeadingRole.SUBSECTION
        assert allowed_role(sections[0][3]) == HeadingRole.SUBSECTION

    def test_verse_opening_section(self, db_session):
        _, sections = _build(db_session, [[True, True, True]])
        first, second, third = sections[0]
        assert allowed_role(first) == HeadingRole.CHAPTER
        assert allowed_role(second) is None
        first.heading_role = "chapter"
        assert allowed_role(second) is None
        assert allowed_role(third) == HeadingRole.SUBSECTION

    def test_verse_non_opening_section(self, db_session):
        _, sections = _build(db_session, [[False], [True, True, True]])
        first, second, third = sections[1]
        assert allowed_role(first) is None
        assert allowed_role(second) == HeadingRole.SUBSECTION
        assert allowed_role(third) == HeadingRole.SUBSECTION

    def test_later_prose_section(self, db_session):
        _, sections = _build(db_session, [[False], [False, False]])
        first, second = sections[1]
        assert allowed_role(first) == HeadingRole.SECTION
        assert allowed_role(second) == HeadingRole.SUBSECTION

    def test_heading_is_legal(self, db_session):
        _, sections = _build(db_session, [[False, False]])
        first, second = sections[0]
        assert heading_is_legal(first) is True
        first.heading_role = "chapter"
        assert heading_is_legal(first) is True
        first.heading_role = "section"
        assert heading_is_legal(first) is False
        second.heading_role = "subsection"
        assert heading_is_legal(second) is False


class TestTitleWrites:
    """Writing divisions' titles from headings."""

    def test_generated_chapter_title(self, db_session):
        chapter, sections = _build(db_session, [[False, False]], chapter_number=2)
        sections[0][0].heading_role = "chapter"
        apply_generated_title(sections[0][0])
        assert chapter.title == "Chapter 2"
        assert chapter.title_auto is True

    def test_generated_section_title(self, db_session):
        _, sections = _build(db_session, [[False], [False, False]])
        sections[1][0].heading_role = "section"
        apply_generated_title(sections[1][0])
        section = sections[1][0].paragraph.section
        assert section.title == "Section 2"
        assert section.title_auto is True

    @pytest.mark.parametrize("role", ["subsection", None])
    def test_generated_title_ignores_other_roles(self, db_session, role):
        chapter, sections = _build(db_session, [[False, False]])
        sentence = sections[0][1]
        sentence.heading_role = role
        apply_generated_title(sentence)
        assert chapter.title is None
        assert sentence.paragraph.section.title is None

    def test_heading_title_for_chapter(self, db_session):
        chapter, sections = _build(db_session, [[False]])
        sections[0][0].heading_role = "chapter"
        chapter.title_auto = True
        apply_heading_title(sections[0][0])
        assert chapter.title == sections[0][0].text_oe
        assert chapter.title_auto is False

    def test_heading_title_for_section(self, db_session):
        _, sections = _build(db_session, [[False], [False]])
        sentence = sections[1][0]
        sentence.heading_role = "section"
        sentence.paragraph.section.title_auto = True
        apply_heading_title(sentence)
        section = sentence.paragraph.section
        assert section.title == sentence.text_oe
        assert section.title_auto is False

    def test_chapter_heading_leaves_verse_section_title(self, db_session):
        _, sections = _build(db_session, [[True, True]])
        section = sections[0][0].paragraph.section
        section.title = "Lines 1-2"
        section.title_auto = True
        sections[0][0].heading_role = "chapter"
        apply_heading_title(sections[0][0])
        assert section.title == "Lines 1-2"
        assert section.title_auto is True

    @pytest.mark.parametrize("role", ["subsection", None])
    def test_heading_title_ignores_other_roles(self, db_session, role):
        chapter, sections = _build(db_session, [[False, False]])
        sentence = sections[0][1]
        sentence.heading_role = role
        apply_heading_title(sentence)
        assert chapter.title is None
        assert sentence.paragraph.section.title is None

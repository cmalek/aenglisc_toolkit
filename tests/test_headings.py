"""Tests for heading sentences."""

from __future__ import annotations

import pytest
from oeapp.commands import (
    ClearHeadingCommand,
    EditSentenceCommand,
    SetHeadingCommand,
)
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


def _hit(command, session):
    """Execute a command and expire the session so reads see its writes."""
    assert command.execute() is True
    session.expire_all()


def test_set_heading_copies_oe_and_clears_auto(db_session) -> None:
    """Marking a chapter heading names the chapter after its Old English text."""
    chapter, sections = _build(db_session, [[False, False]])
    chapter.title = "Chapter 1"
    chapter.title_auto = True
    first = sections[0][0]
    first.text_oe = "Be ðēodwitan"
    db_session.commit()
    command = SetHeadingCommand(sentence_id=first.id, role="chapter")
    _hit(command, db_session)
    assert first.heading_role == "chapter"
    assert chapter.title == "Be ðēodwitan"
    assert chapter.title_auto is False


def test_set_heading_writes_the_allowed_role(db_session) -> None:
    """The stored role is the slot's allowed role, not the declared one."""
    _, sections = _build(db_session, [[False], [False, False]])
    sentence = sections[1][0]
    _hit(SetHeadingCommand(sentence_id=sentence.id, role="chapter"), db_session)
    assert sentence.heading_role == "section"


def test_set_heading_refuses_when_slot_allows_nothing(db_session) -> None:
    """A slot that allows no heading is refused and nothing changes."""
    _, sections = _build(db_session, [[False, False]])
    second = sections[0][1]
    command = SetHeadingCommand(sentence_id=second.id, role="section")
    assert command.execute() is False
    assert second.heading_role is None


def test_set_heading_undo_restores_role_and_title(db_session) -> None:
    """Undo puts back the previous role, title, and title_auto."""
    chapter, sections = _build(db_session, [[False]])
    chapter.title = "Chapter 1"
    chapter.title_auto = True
    db_session.commit()
    command = SetHeadingCommand(sentence_id=sections[0][0].id, role="chapter")
    _hit(command, db_session)
    assert command.undo() is True
    db_session.expire_all()
    assert sections[0][0].heading_role is None
    assert chapter.title == "Chapter 1"
    assert chapter.title_auto is True


def test_clear_chapter_heading_also_clears_section_heading(db_session) -> None:
    """Clearing a chapter heading drops the section heading on index 2."""
    chapter, sections = _build(db_session, [[False, False, False]])
    first, second, _third = sections[0]
    section = first.paragraph.section
    first.heading_role = "chapter"
    second.heading_role = "section"
    chapter.title = first.text_oe
    chapter.title_auto = False
    section.title = second.text_oe
    section.title_auto = False
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=first.id)
    _hit(command, db_session)
    assert first.heading_role is None
    assert second.heading_role is None
    assert chapter.title == "Chapter 1"
    assert chapter.title_auto is True
    assert section.title == "Section 1"
    assert section.title_auto is True
    assert command.cleared_section_heading_id == second.id
    assert command.cleared_section_text_oe == "Sentence 2"
    assert command.cleared_section_number == 1


def test_clear_chapter_heading_undo_restores_both_roles(db_session) -> None:
    """Undo restores both roles and both titles."""
    chapter, sections = _build(db_session, [[False, False]])
    first, second = sections[0]
    section = first.paragraph.section
    first.heading_role = "chapter"
    second.heading_role = "section"
    chapter.title = "Sentence 1"
    section.title = "Sentence 2"
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=first.id)
    _hit(command, db_session)
    assert command.undo() is True
    db_session.expire_all()
    assert first.heading_role == "chapter"
    assert second.heading_role == "section"
    assert chapter.title == "Sentence 1"
    assert chapter.title_auto is False
    assert section.title == "Sentence 2"


def test_clear_chapter_heading_in_verse_section_keeps_lines_title(db_session) -> None:
    """A verse opening section keeps its Lines title and no cascade runs."""
    chapter, sections = _build(db_session, [[True, True, True]])
    first, second, _third = sections[0]
    section = first.paragraph.section
    first.heading_role = "chapter"
    second.heading_role = "section"
    chapter.title = "Sentence 1"
    section.title = "Lines 1-3"
    section.title_auto = True
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=first.id)
    _hit(command, db_session)
    assert command.cleared_section_heading_id is None
    assert second.heading_role == "section"
    assert chapter.title == "Chapter 1"
    assert section.title == "Lines 1-3"
    assert section.title_auto is True


def test_clear_section_heading_restores_section_n(db_session) -> None:
    """A section heading cleared alone restores ``Section {number}``."""
    chapter, sections = _build(db_session, [[False], [False, False]])
    sentence = sections[1][0]
    section = sentence.paragraph.section
    sentence.heading_role = "section"
    section.title = sentence.text_oe
    section.title_auto = False
    chapter.title = "Kept"
    db_session.commit()
    command = ClearHeadingCommand(sentence_id=sentence.id)
    _hit(command, db_session)
    assert sentence.heading_role is None
    assert section.title == "Section 2"
    assert section.title_auto is True
    assert chapter.title == "Kept"
    assert command.cleared_section_heading_id is None


def test_clear_subsection_heading_writes_no_title(db_session) -> None:
    """A subsection clear only clears the role."""
    chapter, sections = _build(db_session, [[False, False, False]])
    sentence = sections[0][2]
    sentence.heading_role = "subsection"
    chapter.title = "Kept"
    db_session.commit()
    _hit(ClearHeadingCommand(sentence_id=sentence.id), db_session)
    assert sentence.heading_role is None
    assert chapter.title == "Kept"
    assert sentence.paragraph.section.title is None


def test_clear_heading_refuses_a_plain_sentence(db_session) -> None:
    """A sentence with no heading role cannot be cleared."""
    _, sections = _build(db_session, [[False]])
    assert ClearHeadingCommand(sentence_id=sections[0][0].id).execute() is False


def test_edit_oe_updates_chapter_title(db_session) -> None:
    """Editing a chapter heading's Old English text renames the chapter."""
    chapter, sections = _build(db_session, [[False]])
    first = sections[0][0]
    first.heading_role = "chapter"
    chapter.title = first.text_oe
    chapter.title_auto = False
    db_session.commit()
    command = EditSentenceCommand(
        sentence_id=first.id,
        field="text_oe",
        before=first.text_oe,
        after="Beowulf",
    )
    _hit(command, db_session)
    assert chapter.title == "Beowulf"
    assert chapter.title_auto is False
    assert command.undo() is True
    db_session.expire_all()
    assert chapter.title == "Sentence 1"


def test_edit_oe_leaves_titles_of_a_plain_sentence(db_session) -> None:
    """Editing a non-heading sentence does not touch titles."""
    chapter, sections = _build(db_session, [[False, False]])
    chapter.title = "Kept"
    db_session.commit()
    second = sections[0][1]
    command = EditSentenceCommand(
        sentence_id=second.id, field="text_oe", before="Sentence 2", after="Other"
    )
    _hit(command, db_session)
    assert chapter.title == "Kept"

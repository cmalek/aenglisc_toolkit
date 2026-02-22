"""Tests for chapter/section hierarchy command behavior."""

from oeapp.commands.hierarchy import (
    MergeChapterCommand,
    MergeSectionCommand,
    SplitChapterCommand,
    SplitSectionCommand,
)
from oeapp.models.chapter import Chapter
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section


def _build_section_with_paragraphs(db_session, *, chapter_id: int, section_number: int, count: int):
    section = Section(chapter_id=chapter_id, number=section_number)
    db_session.add(section)
    db_session.flush()
    paragraphs = []
    for order in range(1, count + 1):
        paragraph = Paragraph(section_id=section.id, order=order)
        db_session.add(paragraph)
        paragraphs.append(paragraph)
    db_session.flush()
    return section, paragraphs


def test_split_section_command_execute_and_undo(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    section, paragraphs = _build_section_with_paragraphs(
        db_session, chapter_id=chapter.id, section_number=1, count=3
    )
    split_paragraph = paragraphs[1]

    cmd = SplitSectionCommand(paragraph_id=split_paragraph.id)
    assert cmd.execute() is True

    db_session.expire_all()
    original_section = Section.get(section.id)
    new_section = Section.get(cmd.new_section_id)
    assert original_section is not None
    assert new_section is not None
    assert [p.id for p in original_section.paragraphs] == [paragraphs[0].id]
    assert [p.id for p in new_section.paragraphs] == [paragraphs[1].id, paragraphs[2].id]
    assert [p.order for p in new_section.paragraphs] == [1, 2]

    assert cmd.undo() is True
    db_session.expire_all()
    restored_section = Section.get(section.id)
    assert restored_section is not None
    assert [p.id for p in restored_section.paragraphs] == [p.id for p in paragraphs]
    assert [p.order for p in restored_section.paragraphs] == [1, 2, 3]
    assert Section.get(cmd.new_section_id) is None


def test_split_section_command_fails_for_first_paragraph(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    _section, paragraphs = _build_section_with_paragraphs(
        db_session, chapter_id=chapter.id, section_number=1, count=2
    )

    cmd = SplitSectionCommand(paragraph_id=paragraphs[0].id)
    assert cmd.execute() is False


def test_merge_section_command_execute_and_undo(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    section1, section1_paragraphs = _build_section_with_paragraphs(
        db_session, chapter_id=chapter.id, section_number=1, count=1
    )
    section2, section2_paragraphs = _build_section_with_paragraphs(
        db_session, chapter_id=chapter.id, section_number=2, count=2
    )

    merge_start = section2_paragraphs[0]
    cmd = MergeSectionCommand(paragraph_id=merge_start.id)
    assert cmd.execute() is True

    db_session.expire_all()
    merged_section = Section.get(section1.id)
    assert merged_section is not None
    assert [p.id for p in merged_section.paragraphs] == [
        section1_paragraphs[0].id,
        section2_paragraphs[0].id,
        section2_paragraphs[1].id,
    ]
    assert Section.get(section2.id) is None

    assert cmd.undo() is True
    db_session.expire_all()
    restored_section1 = Section.get(section1.id)
    restored_section2 = Section.get(cmd.removed_section_id)
    assert restored_section1 is not None
    assert restored_section2 is not None
    assert [p.id for p in restored_section1.paragraphs] == [section1_paragraphs[0].id]
    assert [p.id for p in restored_section2.paragraphs] == [
        section2_paragraphs[0].id,
        section2_paragraphs[1].id,
    ]


def test_merge_section_command_fails_when_paragraph_not_section_start(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    _section1, _ = _build_section_with_paragraphs(
        db_session, chapter_id=chapter.id, section_number=1, count=1
    )
    _section2, section2_paragraphs = _build_section_with_paragraphs(
        db_session, chapter_id=chapter.id, section_number=2, count=2
    )

    cmd = MergeSectionCommand(paragraph_id=section2_paragraphs[1].id)
    assert cmd.execute() is False


def test_split_and_merge_chapter_commands_execute_and_undo(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    sections = []
    for number in (1, 2, 3):
        section = Section(chapter_id=chapter.id, number=number)
        db_session.add(section)
        sections.append(section)
    db_session.flush()

    split_cmd = SplitChapterCommand(section_id=sections[1].id)
    assert split_cmd.execute() is True

    db_session.expire_all()
    original_chapter = Chapter.get(chapter.id)
    new_chapter = Chapter.get(split_cmd.new_chapter_id)
    assert original_chapter is not None
    assert new_chapter is not None
    assert [section.number for section in original_chapter.sections] == [1]
    assert [section.number for section in new_chapter.sections] == [1, 2]
    assert [section.id for section in new_chapter.sections] == [sections[1].id, sections[2].id]

    assert split_cmd.undo() is True
    db_session.expire_all()
    restored_chapter = Chapter.get(chapter.id)
    assert restored_chapter is not None
    assert [section.id for section in restored_chapter.sections] == [s.id for s in sections]

    assert split_cmd.execute() is True
    db_session.expire_all()
    moved_section = Section.get(sections[1].id)
    assert moved_section is not None

    merge_cmd = MergeChapterCommand(section_id=moved_section.id)
    assert merge_cmd.execute() is True
    db_session.expire_all()
    merged_chapter = Chapter.get(chapter.id)
    assert merged_chapter is not None
    assert len(merged_chapter.sections) == 3

    assert merge_cmd.undo() is True
    db_session.expire_all()
    chapter_after_undo = Chapter.get(chapter.id)
    recreated_chapter = Chapter.get(merge_cmd.removed_chapter_id)
    assert chapter_after_undo is not None
    assert recreated_chapter is not None
    assert len(chapter_after_undo.sections) == 1
    assert len(recreated_chapter.sections) == 2


def test_split_chapter_command_fails_for_first_section(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    first_section = Section(chapter_id=chapter.id, number=1)
    db_session.add(first_section)
    db_session.flush()

    cmd = SplitChapterCommand(section_id=first_section.id)
    assert cmd.execute() is False

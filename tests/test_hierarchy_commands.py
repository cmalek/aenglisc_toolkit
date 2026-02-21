import pytest
from sqlalchemy import select
from oeapp.models.project import Project
from oeapp.models.chapter import Chapter
from oeapp.models.section import Section
from oeapp.models.paragraph import Paragraph
from oeapp.commands.hierarchy import (
    SplitSectionCommand, MergeSectionCommand,
    SplitChapterCommand, MergeChapterCommand
)

def test_split_section_command(db_session):
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.commit()

    section = Section(chapter_id=chapter.id, number=1)
    db_session.add(section)
    db_session.commit()

    p1 = Paragraph(section_id=section.id, order=1)
    p2 = Paragraph(section_id=section.id, order=2)
    p3 = Paragraph(section_id=section.id, order=3)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # Split at p2
    cmd = SplitSectionCommand(paragraph_id=p2.id)
    assert cmd.execute()
    db_session.commit()

    db_session.expire_all()
    section = db_session.get(Section, section.id)
    assert len(section.paragraphs) == 1
    assert section.paragraphs[0].id == p1.id

    new_section = db_session.get(Section, cmd.new_section_id)
    assert new_section.number == 2
    assert len(new_section.paragraphs) == 2
    assert new_section.paragraphs[0].id == p2.id
    assert new_section.paragraphs[1].id == p3.id
    assert p2.order == 1
    assert p3.order == 2

    # Undo split
    assert cmd.undo()
    db_session.commit()
    db_session.expire_all()

    section = db_session.get(Section, section.id)
    assert len(section.paragraphs) == 3

def test_merge_section_command(db_session):
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.commit()

    section1 = Section(chapter_id=chapter.id, number=1)
    db_session.add(section)
    db_session.commit()

    section2 = Section(chapter_id=chapter.id, number=2)
    db_session.add(section2)
    db_session.commit()

    p1 = Paragraph(section_id=section1.id, order=1)
    p2 = Paragraph(section_id=section2.id, order=2)
    p3 = Paragraph(section_id=section2.id, order=3)
    db_session.add_all([p1, p2, p3])
    db_session.commit()

    # Merge at p2
    cmd = MergeSectionCommand(paragraph_id=p2.id)
    assert cmd.execute()
    db_session.commit()

    db_session.expire_all()
    section = db_session.get(Section, section.id)
    assert len(section.paragraphs) == 2
def test_split_merge_chapter(db_session):
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.commit()

    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.commit()

    s1 = Section(chapter_id=chapter.id, number=1)
    s2 = Section(chapter_id=chapter.id, number=2)
    s3 = Section(chapter_id=chapter.id, number=3)
    db_session.add_all([s1, s2, s3])
    db_session.commit()

    # Split at s2
    cmd = SplitChapterCommand(section_id=s2.id)
    assert cmd.execute()
    db_session.commit()

    db_session.expire_all()
    chapter = db_session.get(Chapter, chapter.id)
    assert len(chapter.sections) == 1

    new_chapter = db_session.get(Chapter, cmd.new_chapter_id)
    assert new_chapter.number == 2
    assert len(new_chapter.sections) == 2
    assert s2.chapter_id == new_chapter.id
    assert s2.number == 1

    # Undo split
    assert cmd.undo()
    db_session.commit()
    db_session.expire_all()

    all_s = db_session.query(Section).all()
    assert len(all_s) == 3
    for s in all_s:
        assert s.chapter_id == chapter.id

    # Merge chapter (redo split first)
    cmd.execute()
    db_session.commit()
    merge_cmd = MergeChapterCommand(section_id=s2.id)
    assert merge_cmd.execute()
    db_session.commit()
    db_session.expire_all()
    chapter = db_session.get(Chapter, chapter.id)
    assert len(chapter.sections) == 3

    # Undo merge
    assert merge_cmd.undo()
    db_session.commit()
    db_session.expire_all()
    chapter = db_session.get(Chapter, chapter.id)
    assert len(chapter.sections) == 1
    new_chapter = db_session.get(Chapter, merge_cmd.removed_chapter_id)
    assert new_chapter is not None
    assert len(new_chapter.sections) == 2

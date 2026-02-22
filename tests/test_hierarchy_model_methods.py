"""Focused tests for chapter/section/paragraph helper methods."""

from oeapp.models.chapter import Chapter
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence


def test_chapter_methods_cover_ordering_and_navigation(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()

    chapter1 = Chapter.create(project_id=project.id, number=1, title="One")
    chapter2 = Chapter.create(project_id=project.id, number=2)
    chapter3 = Chapter.create(project_id=project.id, number=3)

    assert [chapter.number for chapter in Chapter.list(project_id=project.id)] == [1, 2, 3]
    assert Chapter.previous_chapter(project.id, 1) is None
    assert Chapter.previous_chapter(project.id, 3).id == chapter2.id
    assert [chapter.id for chapter in Chapter.get_chapters_after(project.id, 1)] == [
        chapter2.id,
        chapter3.id,
    ]
    assert [chapter.id for chapter in Chapter.get_chapters_after(project.id, 1, exclude_chapter_id=chapter2.id)] == [
        chapter3.id
    ]
    assert chapter1.display_title == "One"
    assert chapter2.display_title == "Chapter 2"
    assert chapter1.last_section_number() == 0


def test_section_methods_cover_ordering_and_navigation(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter.create(project_id=project.id, number=1)

    section1 = Section.create(chapter_id=chapter.id, number=1, title="Intro")
    section2 = Section.create(chapter_id=chapter.id, number=2)
    section3 = Section.create(chapter_id=chapter.id, number=3)

    assert [section.number for section in Section.list(chapter_id=chapter.id)] == [1, 2, 3]
    assert Section.previous_section(chapter.id, 1) is None
    assert Section.previous_section(chapter.id, 3).id == section2.id
    assert [section.id for section in Section.get_sections_after(chapter.id, 1)] == [
        section2.id,
        section3.id,
    ]
    assert [section.id for section in Section.get_sections_after(chapter.id, 1, exclude_section_id=section2.id)] == [
        section3.id
    ]
    assert section1.display_title == "Intro"
    assert section2.display_title == "Section 2"
    assert section1.last_paragraph_number() == 0


def test_paragraph_methods_cover_ordering_navigation_and_json(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    chapter = Chapter.create(project_id=project.id, number=1)
    section = Section.create(chapter_id=chapter.id, number=1)

    paragraph1 = Paragraph.create(section_id=section.id, order=1)
    paragraph2 = Paragraph.create(section_id=section.id, order=2)
    paragraph3 = Paragraph.create(section_id=section.id, order=3)
    sentence = Sentence.create(
        project_id=project.id,
        display_order=1,
        text_oe="S1.",
        paragraph_id=paragraph2.id,
    )

    assert [paragraph.order for paragraph in Paragraph.list(section_id=section.id)] == [1, 2, 3]
    assert Paragraph.previous_paragraph(section.id, 1) is None
    assert Paragraph.previous_paragraph(section.id, 3).id == paragraph2.id
    assert [paragraph.id for paragraph in Paragraph.get_paragraphs_after(section.id, 1)] == [
        paragraph2.id,
        paragraph3.id,
    ]
    assert [paragraph.id for paragraph in Paragraph.get_paragraphs_after(section.id, 1, exclude_paragraph_id=paragraph2.id)] == [
        paragraph3.id
    ]
    assert paragraph2.last_sentence_number() == sentence.display_order
    assert paragraph2.to_json() == {
        "id": paragraph2.id,
        "section_id": section.id,
        "order": 2,
    }

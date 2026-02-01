import pytest
from oeapp.models.project import Project
from oeapp.models.chapter import Chapter
from oeapp.models.section import Section
from oeapp.models.paragraph import Paragraph
from oeapp.models.sentence import Sentence

def test_chapter_model(db_session):
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.flush()
    
    chapter = Chapter(project_id=project.id, number=1, title="Introduction")
    db_session.add(chapter)
    db_session.flush()
    
    assert chapter.display_title == "Introduction"
    assert chapter.project == project
    
    chapter2 = Chapter(project_id=project.id, number=2)
    db_session.add(chapter2)
    db_session.flush()
    assert chapter2.display_title == "Chapter 2"

def test_section_model(db_session):
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.flush()
    
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    
    section = Section(chapter_id=chapter.id, number=1, title="Section 1")
    db_session.add(section)
    db_session.flush()
    
    assert section.display_title == "Section 1"
    assert section.chapter == chapter
    
    section2 = Section(chapter_id=chapter.id, number=2)
    db_session.add(section2)
    db_session.flush()
    assert section2.display_title == "Section 2"

def test_paragraph_model(db_session):
    project = Project(name="Test Project")
    db_session.add(project)
    db_session.flush()
    
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    
    section = Section(chapter_id=chapter.id, number=1)
    db_session.add(section)
    db_session.flush()
    
    paragraph = Paragraph(section_id=section.id, order=1)
    db_session.add(paragraph)
    db_session.flush()
    
    assert paragraph.section == section
    assert paragraph.order == 1

def test_hierarchy_relationships(db_session):
    project = Project(name="Hierarchy Project")
    db_session.add(project)
    db_session.flush()
    
    chapter = Chapter(project_id=project.id, number=1)
    db_session.add(chapter)
    db_session.flush()
    
    section = Section(chapter_id=chapter.id, number=1)
    db_session.add(section)
    db_session.flush()
    
    paragraph = Paragraph(section_id=section.id, order=1)
    db_session.add(paragraph)
    db_session.flush()
    
    sentence = Sentence(project_id=project.id, paragraph_id=paragraph.id, display_order=1, text_oe="Hwaet!")
    db_session.add(sentence)
    db_session.flush()
    
    assert sentence.paragraph == paragraph
    assert paragraph.sentences == [sentence]
    assert section.paragraphs == [paragraph]
    assert chapter.sections == [section]
    assert project.chapters == [chapter]

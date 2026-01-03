import time
from datetime import UTC, datetime

from oeapp.models import Annotation, Note, Project, Sentence, Token


def test_project_updated_at_on_sentence_create(db_session):
    """Test that creating a sentence updates the project's updated_at."""
    project = Project.create(text="Initial text.", name="Test Project Create Sentence")
    db_session.commit()
    initial_updated_at = project.updated_at

    # Wait a bit to ensure timestamp will be different
    time.sleep(0.1)

    Sentence.create(project_id=project.id, display_order=2, text_oe="New sentence.")
    db_session.commit()

    db_session.refresh(project)
    assert project.updated_at > initial_updated_at


def test_project_updated_at_on_sentence_update(db_session):
    """Test that updating a sentence updates the project's updated_at."""
    project = Project.create(text="Initial text.", name="Test Project Update Sentence")
    db_session.commit()
    sentence = project.sentences[0]
    initial_updated_at = project.updated_at

    time.sleep(0.1)

    sentence.text_oe = "Updated text."
    sentence.save()

    db_session.refresh(project)
    assert project.updated_at > initial_updated_at


def test_project_updated_at_on_sentence_delete(db_session):
    """Test that deleting a sentence updates the project's updated_at."""
    project = Project.create(
        text="Sentence 1. Sentence 2.", name="Test Project Delete Sentence"
    )
    db_session.commit()
    sentence_to_delete = project.sentences[1]
    initial_updated_at = project.updated_at

    time.sleep(0.1)

    sentence_to_delete.delete()

    db_session.refresh(project)
    assert project.updated_at > initial_updated_at


def test_project_updated_at_on_token_update(db_session):
    """Test that updating a token updates the project's updated_at."""
    project = Project.create(text="Se cyning.", name="Test Project Update Token")
    db_session.commit()
    sentence = project.sentences[0]
    token = sentence.tokens[0]
    initial_updated_at = project.updated_at

    time.sleep(0.1)

    token.surface = "Changed"
    token.save()

    db_session.refresh(project)
    assert project.updated_at > initial_updated_at


def test_project_updated_at_on_annotation_update(db_session):
    """Test that updating an annotation updates the project's updated_at."""
    project = Project.create(text="Se cyning.", name="Test Project Update Annotation")
    db_session.commit()
    sentence = project.sentences[0]
    token = sentence.tokens[0]
    annotation = token.annotation
    initial_updated_at = project.updated_at

    time.sleep(0.1)

    annotation.pos = "V"
    annotation.save()

    db_session.refresh(project)
    assert project.updated_at > initial_updated_at


def test_project_updated_at_on_note_create(db_session):
    """Test that creating a note updates the project's updated_at."""
    project = Project.create(text="Se cyning.", name="Test Project Create Note")
    db_session.commit()
    sentence = project.sentences[0]
    initial_updated_at = project.updated_at

    time.sleep(0.1)

    note = Note(sentence_id=sentence.id, note_text_md="Test note")
    note.save()

    db_session.refresh(project)
    assert project.updated_at > initial_updated_at


def test_project_updated_at_on_note_delete(db_session):
    """Test that deleting a note updates the project's updated_at."""
    project = Project.create(text="Se cyning.", name="Test Project Delete Note")
    db_session.commit()
    sentence = project.sentences[0]
    note = Note(sentence_id=sentence.id, note_text_md="Test note")
    note.save()
    db_session.commit()

    db_session.refresh(project)
    initial_updated_at = project.updated_at

    time.sleep(0.1)

    note.delete()

    db_session.refresh(project)
    assert project.updated_at > initial_updated_at


def test_timestamps_are_utc(db_session):
    """Test that timestamps are close to UTC now."""
    project = Project.create(text="Test", name="Test Timestamps UTC")
    db_session.commit()
    now_utc = datetime.now(UTC).replace(tzinfo=None)

    # Should be within a small delta of now_utc
    assert abs((project.updated_at - now_utc).total_seconds()) < 5
    assert abs((project.created_at - now_utc).total_seconds()) < 5


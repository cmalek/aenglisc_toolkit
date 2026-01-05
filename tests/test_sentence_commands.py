import pytest
from oeapp.commands.sentence import AddSentenceCommand, DeleteSentenceCommand, MergeSentenceCommand
from oeapp.models.sentence import Sentence
from tests.conftest import create_test_project

def test_add_sentence_before_first_sentence_succeeds(db_session):
    """
    Verify that adding a sentence before the first sentence of a project
    now succeeds.
    """
    # 1. Create a project with one sentence
    project = create_test_project(db_session, text="First sentence.")
    db_session.commit()
    first_sentence = project.sentences[0]
    assert first_sentence.display_order == 1
    assert first_sentence.paragraph_number == 1
    assert first_sentence.sentence_number_in_paragraph == 1

    # 2. Add a sentence BEFORE the first sentence
    command = AddSentenceCommand(
        project_id=project.id,
        reference_sentence_id=first_sentence.id,
        position="before"
    )

    assert command.execute()

    # 3. Verify structure
    sentences = Sentence.list(project.id)
    assert len(sentences) == 2

    # New sentence should be first and inherit paragraph start
    new_s = sentences[0]
    old_s = sentences[1]

    assert new_s.display_order == 1
    assert new_s.paragraph_number == 1
    assert new_s.sentence_number_in_paragraph == 1
    assert new_s.is_paragraph_start is True

    assert old_s.display_order == 2
    assert old_s.paragraph_number == 1
    assert old_s.sentence_number_in_paragraph == 2
    assert old_s.is_paragraph_start is False

    # 4. Undo and verify
    assert command.undo()
    sentences = Sentence.list(project.id)
    assert len(sentences) == 1
    assert sentences[0].id == first_sentence.id
    assert sentences[0].display_order == 1
    assert sentences[0].paragraph_number == 1
    assert sentences[0].sentence_number_in_paragraph == 1
    assert sentences[0].is_paragraph_start is True

def test_add_sentence_after_first_sentence_succeeds(db_session):
    """
    Verify that adding a sentence after the first sentence of a project
    now succeeds.
    """
    # 1. Create a project with one sentence
    project = create_test_project(db_session, text="First sentence.")
    db_session.commit()
    first_sentence = project.sentences[0]

    # 2. Add a sentence AFTER the first sentence
    command = AddSentenceCommand(
        project_id=project.id,
        reference_sentence_id=first_sentence.id,
        position="after"
    )

    assert command.execute()

    # 3. Verify structure
    sentences = Sentence.list(project.id)
    assert len(sentences) == 2

    old_s = sentences[0]
    new_s = sentences[1]

    assert old_s.display_order == 1
    assert old_s.paragraph_number == 1
    assert old_s.sentence_number_in_paragraph == 1

    assert new_s.display_order == 2
    assert new_s.paragraph_number == 1
    assert new_s.sentence_number_in_paragraph == 2
    assert new_s.is_paragraph_start is False

def test_delete_sentence_recalculates(db_session):
    """Test that deleting a sentence recalculates paragraph/sentence numbers."""
    project = create_test_project(db_session, text="S1. S2. S3.")
    db_session.commit()
    sentences = Sentence.list(project.id)
    s2 = sentences[1]

    command = DeleteSentenceCommand(sentence_id=s2.id)
    assert command.execute()

    remaining = Sentence.list(project.id)
    assert len(remaining) == 2
    assert remaining[0].display_order == 1
    assert remaining[1].display_order == 2
    assert remaining[1].sentence_number_in_paragraph == 2

    assert command.undo()
    restored = Sentence.list(project.id)
    assert len(restored) == 3
    assert restored[1].display_order == 2
    assert restored[1].sentence_number_in_paragraph == 2

def test_merge_sentences_recalculates(db_session):
    """Test that merging sentences recalculates paragraph/sentence numbers."""
    project = create_test_project(db_session, text="S1. S2. S3.")
    db_session.commit()
    sentences = Sentence.list(project.id)
    s1 = sentences[0]
    s2 = sentences[1]

    command = MergeSentenceCommand(
        current_sentence_id=s1.id,
        next_sentence_id=s2.id,
        before_text_oe=s1.text_oe,
        before_text_modern=s1.text_modern
    )
    assert command.execute()

    remaining = Sentence.list(project.id)
    assert len(remaining) == 2
    assert remaining[0].display_order == 1
    assert remaining[1].display_order == 2
    assert remaining[1].sentence_number_in_paragraph == 2

    assert command.undo()
    restored = Sentence.list(project.id)
    assert len(restored) == 3
    assert restored[1].display_order == 2
    assert restored[1].sentence_number_in_paragraph == 2
    assert restored[2].display_order == 3
    assert restored[2].sentence_number_in_paragraph == 3


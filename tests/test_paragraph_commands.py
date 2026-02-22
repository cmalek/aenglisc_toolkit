"""Tests for paragraph split/merge command behavior."""

from oeapp.commands.paragraph import MergeParagraphCommand, SplitParagraphCommand
from oeapp.models.paragraph import Paragraph
from oeapp.models.sentence import Sentence
from tests.conftest import create_test_project


def _create_three_sentences_single_paragraph(db_session):
    project = create_test_project(db_session, text="")
    paragraph_id = project.chapters[0].sections[0].paragraphs[0].id
    s1 = Sentence.create(project_id=project.id, display_order=1, text_oe="S1.", paragraph_id=paragraph_id)
    s2 = Sentence.create(project_id=project.id, display_order=2, text_oe="S2.", paragraph_id=paragraph_id)
    s3 = Sentence.create(project_id=project.id, display_order=3, text_oe="S3.", paragraph_id=paragraph_id)
    return project, s1, s2, s3


def test_split_paragraph_command_execute_and_undo(db_session):
    _project, s1, s2, s3 = _create_three_sentences_single_paragraph(db_session)
    original_paragraph_id = s1.paragraph_id

    cmd = SplitParagraphCommand(sentence_id=s2.id)
    assert cmd.execute() is True

    db_session.expire_all()
    s1_ref = Sentence.get(s1.id)
    s2_ref = Sentence.get(s2.id)
    s3_ref = Sentence.get(s3.id)
    assert s1_ref is not None
    assert s2_ref is not None
    assert s3_ref is not None
    assert s1_ref.paragraph_id == original_paragraph_id
    assert s2_ref.paragraph_id == s3_ref.paragraph_id
    assert s2_ref.paragraph_id != original_paragraph_id
    assert Paragraph.get(cmd.new_paragraph_id) is not None

    assert cmd.undo() is True
    db_session.expire_all()
    assert Sentence.get(s1.id).paragraph_id == original_paragraph_id
    assert Sentence.get(s2.id).paragraph_id == original_paragraph_id
    assert Sentence.get(s3.id).paragraph_id == original_paragraph_id
    assert Paragraph.get(cmd.new_paragraph_id) is None


def test_split_paragraph_command_fails_for_first_sentence(db_session):
    _project, s1, _s2, _s3 = _create_three_sentences_single_paragraph(db_session)

    cmd = SplitParagraphCommand(sentence_id=s1.id)
    assert cmd.execute() is False


def test_split_paragraph_command_fails_when_sentence_missing(db_session):
    cmd = SplitParagraphCommand(sentence_id=999_999)
    assert cmd.execute() is False


def test_merge_paragraph_command_execute_and_undo(db_session):
    _project, s1, s2, s3 = _create_three_sentences_single_paragraph(db_session)
    split_cmd = SplitParagraphCommand(sentence_id=s2.id)
    assert split_cmd.execute() is True
    db_session.expire_all()

    s2_ref = Sentence.get(s2.id)
    assert s2_ref is not None
    merge_cmd = MergeParagraphCommand(sentence_id=s2_ref.id)
    assert merge_cmd.execute() is True

    db_session.expire_all()
    assert Sentence.get(s1.id).paragraph_id == Sentence.get(s2.id).paragraph_id
    assert Sentence.get(s2.id).paragraph_id == Sentence.get(s3.id).paragraph_id
    assert merge_cmd.undo() is True

    db_session.expire_all()
    s2_after_undo = Sentence.get(s2.id)
    s3_after_undo = Sentence.get(s3.id)
    assert s2_after_undo is not None
    assert s3_after_undo is not None
    assert s2_after_undo.paragraph_id == s3_after_undo.paragraph_id
    assert s2_after_undo.paragraph.order == 2


def test_merge_paragraph_command_fails_when_sentence_not_paragraph_start(db_session):
    _project, _s1, s2, s3 = _create_three_sentences_single_paragraph(db_session)
    split_cmd = SplitParagraphCommand(sentence_id=s2.id)
    assert split_cmd.execute() is True
    db_session.expire_all()

    s3_ref = Sentence.get(s3.id)
    assert s3_ref is not None
    cmd = MergeParagraphCommand(sentence_id=s3_ref.id)
    assert cmd.execute() is False


def test_merge_paragraph_command_fails_when_first_paragraph(db_session):
    _project, s1, _s2, _s3 = _create_three_sentences_single_paragraph(db_session)

    cmd = MergeParagraphCommand(sentence_id=s1.id)
    assert cmd.execute() is False

"""Annotation modal apply: before-snapshot, command, and Undo."""

from oeapp.commands import AnnotateTokenCommand, push_command
from oeapp.models import Annotation, AnnotationEdit, Idiom
from oeapp.services.annotation_apply import AnnotationApplyService
from PySide6.QtGui import QUndoStack

from tests.conftest import create_test_project


def _existing_token_annotation(db_session, pos: str):
    project = create_test_project(db_session, name="Apply", text="Se cyning")
    sentence = project.sentences[0]
    token = sentence.tokens[0]
    annotation = Annotation.get_by_token(token.id)
    if annotation is None:
        annotation = Annotation(token_id=token.id)
    annotation.pos = pos
    annotation.save()
    db_session.refresh(token)
    return sentence, token


def test_begin_without_existing_annotation_is_empty() -> None:
    assert AnnotationApplyService().begin(None) == AnnotationEdit(before={})


def test_before_snapshot_is_taken_before_the_edit(db_session, qapp) -> None:
    _, token = _existing_token_annotation(db_session, "V")
    service = AnnotationApplyService()
    edit = service.begin(token.annotation)
    token.annotation.pos = "N"
    assert edit.before["pos"] == "V"


def test_undo_restores_an_edited_token_annotation(db_session, qapp) -> None:
    sentence, token = _existing_token_annotation(db_session, "V")
    service = AnnotationApplyService()
    edit = service.begin(token.annotation)
    applied = token.annotation
    applied.pos = "N"
    stack = QUndoStack()
    command = service.command_for(edit, applied, sentence.id)
    assert push_command(stack, command)
    assert Annotation.get_by_token(token.id).pos == "N"

    stack.undo()
    db_session.expire_all()
    assert Annotation.get_by_token(token.id).pos == "V"

    stack.redo()
    db_session.expire_all()
    assert Annotation.get_by_token(token.id).pos == "N"


def test_undo_restores_an_edited_idiom_annotation(db_session, qapp) -> None:
    project = create_test_project(db_session, name="Idiom", text="Se cyning")
    sentence = project.sentences[0]
    tokens = list(sentence.tokens)
    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[1].id,
    )
    idiom.save()
    Annotation(idiom_id=idiom.id, pos="V").save()
    db_session.refresh(idiom)

    service = AnnotationApplyService()
    edit = service.begin(idiom.annotation)
    applied = idiom.annotation
    applied.pos = "N"
    stack = QUndoStack()
    assert push_command(stack, service.command_for(edit, applied, sentence.id))

    stack.undo()
    db_session.expire_all()
    assert Annotation.get_by_idiom(idiom.id).pos == "V"


def test_new_idiom_apply_creates_the_idiom_and_its_annotation(
    db_session, qapp
) -> None:
    project = create_test_project(db_session, name="New", text="Se cyning")
    sentence = project.sentences[0]
    tokens = list(sentence.tokens)
    new_idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[1].id,
    )
    applied = Annotation(pos="N")
    applied.idiom = new_idiom

    service = AnnotationApplyService()
    edit = service.begin(None)
    command = service.command_for(edit, applied, sentence.id)
    assert command.new_idiom is new_idiom
    assert push_command(QUndoStack(), command)

    assert command.idiom_id is not None
    assert Annotation.get_by_idiom(command.idiom_id).pos == "N"


def test_finish_copies_a_created_idiom_id() -> None:
    applied = Annotation(pos="N")
    command = AnnotateTokenCommand(
        token_id=None,
        idiom_id=7,
        before={},
        after={},
        new_idiom=Idiom(sentence_id=1, start_token_id=1, end_token_id=2),
        sentence_id=1,
    )
    AnnotationApplyService().finish(applied, command)
    assert applied.idiom_id == 7


def test_finish_leaves_an_existing_annotation_alone() -> None:
    applied = Annotation(pos="N", idiom_id=3)
    command = AnnotateTokenCommand(
        token_id=None, idiom_id=3, before={}, after={}, sentence_id=1
    )
    AnnotationApplyService().finish(applied, command)
    assert applied.idiom_id == 3

"""Tests for the QUndoCommand wrapper around ``Command``."""

import gc

import pytest
from oeapp.commands.abstract import Command
from oeapp.commands.annotation import (
    AnnotateTokenCommand,
    ApplyAnnotationPropagationCommand,
    ApplyRememberedAnnotationsCommand,
)
from oeapp.commands.hierarchy import (
    MergeChapterCommand,
    MergeSectionCommand,
    SplitChapterCommand,
    SplitSectionCommand,
)
from oeapp.commands.note import AddNoteCommand, DeleteNoteCommand, UpdateNoteCommand
from oeapp.commands.paragraph import MergeParagraphCommand, SplitParagraphCommand
from oeapp.commands.sentence import (
    AddSentenceCommand,
    DeleteSentenceCommand,
    EditSentenceCommand,
    MergeSentenceCommand,
)
from oeapp.commands.undo_command import UndoCommand, push_command
from PySide6.QtGui import QUndoStack


class FailCommand(Command):
    """Command whose ``execute`` always fails."""

    def execute(self) -> bool:
        """Fail."""
        return False

    def undo(self) -> bool:
        """Undo nothing."""
        return True

    def menu_text(self) -> str:
        """Describe the command."""
        return "Fail"


class LogCommand(Command):
    """
    Command that records ``execute`` and ``undo`` calls.

    Args:
        log: List that receives ``"redo"`` and ``"undo"`` entries.

    """

    def __init__(self, log: list[str]) -> None:
        """Store the log list."""
        self.log = log

    def execute(self) -> bool:
        """Record a redo."""
        self.log.append("redo")
        return True

    def undo(self) -> bool:
        """Record an undo."""
        self.log.append("undo")
        return True

    def menu_text(self) -> str:
        """Describe the command."""
        return "Log"


def test_failed_execute_is_not_kept(qapp):
    stack = QUndoStack()
    assert push_command(stack, FailCommand()) is False
    assert stack.count() == 0
    assert stack.canUndo() is False


def test_stack_owns_the_command_after_the_name_is_dropped(qapp):
    stack = QUndoStack()
    log: list[str] = []
    push_command(stack, LogCommand(log))
    gc.collect()
    stack.undo()
    stack.redo()
    assert log == ["redo", "undo", "redo"]


def test_successful_push_returns_true_and_is_on_stack(qapp):
    stack = QUndoStack()
    assert push_command(stack, LogCommand([])) is True
    assert stack.count() == 1
    assert stack.undoText() == "Log"


def test_id_and_merge_defaults(qapp):
    wrapper = UndoCommand(LogCommand([]), {})
    assert wrapper.id() == -1
    wrapper._run_open = True
    assert wrapper.id() == 1
    assert wrapper.mergeWith(UndoCommand(LogCommand([]), {})) is False


def _edit(field):
    return EditSentenceCommand(sentence_id=7, field=field, before="a", after="b")


UNDO_NAMES = [
    (lambda: _edit("text_modern"), "Edit translation"),
    (lambda: _edit("text_oe"), "Edit Old English"),
    (
        lambda: MergeSentenceCommand(
            current_sentence_id=7,
            next_sentence_id=8,
            before_text_oe="a",
            before_text_modern=None,
        ),
        "Merge sentences",
    ),
    (
        lambda: AddSentenceCommand(
            project_id=3, reference_sentence_id=7, position="before"
        ),
        "Add sentence",
    ),
    (
        lambda: AddSentenceCommand(
            project_id=3, reference_sentence_id=7, position="after"
        ),
        "Add sentence",
    ),
    (lambda: DeleteSentenceCommand(sentence_id=7), "Delete sentence"),
    (lambda: SplitParagraphCommand(sentence_id=7), "Split paragraph"),
    (lambda: MergeParagraphCommand(sentence_id=7), "Merge paragraphs"),
    (lambda: SplitSectionCommand(paragraph_id=7), "Split section"),
    (lambda: MergeSectionCommand(paragraph_id=7), "Merge sections"),
    (lambda: SplitChapterCommand(section_id=7), "Split chapter"),
    (lambda: MergeChapterCommand(section_id=7), "Merge chapters"),
    (lambda: AnnotateTokenCommand(token_id=7), "Annotate"),
    (lambda: AnnotateTokenCommand(idiom_id=7), "Annotate"),
    (
        lambda: ApplyRememberedAnnotationsCommand(token_ids=[7, 8]),
        "Apply remembered annotations",
    ),
    (
        lambda: ApplyAnnotationPropagationCommand(token_ids=[7, 8]),
        "Propagate annotation",
    ),
    (
        lambda: AddNoteCommand(
            sentence_id=7, start_token_id=1, end_token_id=2, note_text="n"
        ),
        "Add note",
    ),
    (
        lambda: UpdateNoteCommand(
            note_id=7,
            before_text="a",
            after_text="b",
            before_start_token=None,
            before_end_token=None,
            after_start_token=None,
            after_end_token=None,
        ),
        "Update note",
    ),
    (lambda: DeleteNoteCommand(note_id=7), "Delete note"),
]


@pytest.mark.parametrize(("make", "name"), UNDO_NAMES)
def test_undo_text_has_no_database_id(qapp, monkeypatch, make, name):
    command = make()
    monkeypatch.setattr(type(command), "execute", lambda self: True)
    stack = QUndoStack()
    assert push_command(stack, command) is True
    assert stack.undoText() == name
    assert command.get_description() == name

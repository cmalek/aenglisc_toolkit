"""Stack entries follow the sentence and the token they act on."""

from dataclasses import dataclass

import pytest
from oeapp.commands import (
    AddNoteCommand,
    AddSentenceCommand,
    AnnotateTokenCommand,
    ApplyRememberedAnnotationsCommand,
    DeleteSentenceCommand,
    EditSentenceCommand,
    MergeSentenceCommand,
    UpdateNoteCommand,
    push_command,
)
from oeapp.commands.abstract import Command, CommandLocators, StackAdjustment
from oeapp.commands.stack_maintenance import maintain_stack
from oeapp.commands.undo_command import UndoCommand, redo_step, undo_step
from oeapp.models.annotation import Annotation
from oeapp.models.note import Note
from oeapp.models.project import Project
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token
from PySide6.QtGui import QUndoStack


@dataclass
class Setup:
    """Two-sentence project and a fresh undo stack."""

    project_id: int
    sentence_id: int
    next_sentence_id: int
    undo_stack: QUndoStack


@pytest.fixture
def setup(db_session) -> Setup:
    """Create a project with two sentences and an empty stack."""
    project = Project.create(
        text="Se cyning cōm. Hē wæs gōd.", name=f"Stack {id(db_session)}"
    )
    sentences = Sentence.list(project.id)
    assert len(sentences) == 2  # noqa: PLR2004
    return Setup(project.id, sentences[0].id, sentences[1].id, QUndoStack())


def edit_translation(sentence_id: int, before: str, after: str) -> EditSentenceCommand:
    return EditSentenceCommand(
        sentence_id=sentence_id, field="text_modern", before=before, after=after
    )


def edit_old_english(sentence_id: int, before: str, after: str) -> EditSentenceCommand:
    return EditSentenceCommand(
        sentence_id=sentence_id, field="text_oe", before=before, after=after
    )


def delete_sentence(sentence_id: int) -> DeleteSentenceCommand:
    return DeleteSentenceCommand(sentence_id=sentence_id)


def add_sentence_before(project_id: int, sentence_id: int) -> AddSentenceCommand:
    return AddSentenceCommand(
        project_id=project_id, reference_sentence_id=sentence_id, position="before"
    )


def merge_sentences(current_id: int, next_id: int) -> MergeSentenceCommand:
    current = Sentence.get(current_id)
    assert current is not None
    return MergeSentenceCommand(
        current_sentence_id=current_id,
        next_sentence_id=next_id,
        before_text_oe=current.text_oe,
        before_text_modern=current.text_modern,
    )


def annotate(token_id: int) -> AnnotateTokenCommand:
    return AnnotateTokenCommand(
        token_id=token_id, before={"pos": None}, after={"pos": "N"}
    )


def token_named(sentence_id: int, surface: str) -> Token:
    return next(t for t in Token.list(sentence_id) if t.surface == surface)


def entries(stack: QUndoStack) -> list:
    return [stack.command(i) for i in range(stack.count())]


# --- the two tests from the brief --------------------------------------------


def test_delete_drops_the_translation_step_and_undo_restores_the_capture(setup):
    push_command(setup.undo_stack, edit_translation(setup.sentence_id, "", "hello"))
    push_command(setup.undo_stack, delete_sentence(setup.sentence_id))
    assert undo_step(setup.undo_stack) is True
    sentences = Sentence.list(setup.project_id)
    assert len(sentences) == 2  # noqa: PLR2004
    assert sentences[0].text_modern == "hello"
    assert setup.undo_stack.canUndo() is False


def test_insert_keeps_the_translation_on_the_same_sentence_id(setup):
    sentence_id = setup.sentence_id
    push_command(setup.undo_stack, edit_translation(sentence_id, "", "hello"))
    push_command(setup.undo_stack, add_sentence_before(setup.project_id, sentence_id))
    assert undo_step(setup.undo_stack) is True  # undo the insert
    assert undo_step(setup.undo_stack) is True
    assert Sentence.get(sentence_id).text_modern == ""


# --- locators and adjustments ------------------------------------------------


def test_default_command_has_no_locators_and_removes_nothing(setup):
    command = edit_translation(setup.sentence_id, "", "x")
    assert command.locators() == CommandLocators(sentence_ids={setup.sentence_id})
    assert command.last_adjustment == StackAdjustment()
    assert command.is_removal_of(setup.sentence_id) is False


def test_delete_and_merge_are_removals(setup):
    assert delete_sentence(setup.sentence_id).is_removal_of(setup.sentence_id)
    merge = merge_sentences(setup.sentence_id, setup.next_sentence_id)
    assert merge.is_removal_of(setup.next_sentence_id) is True
    assert merge.is_removal_of(setup.sentence_id) is False


def test_delete_records_the_sentence_its_tokens_and_the_new_id_on_undo(setup):
    token_ids = {t.id for t in Token.list(setup.sentence_id)}
    delete = delete_sentence(setup.sentence_id)
    push_command(setup.undo_stack, delete)
    assert delete.last_adjustment.obsolete_sentence_ids == {setup.sentence_id}
    assert delete.last_adjustment.obsolete_token_ids == token_ids
    assert setup.undo_stack.count() == 1  # the removal itself stays
    undo_step(setup.undo_stack)
    # SQLite may hand the restored row the same id or a new one; the locator
    # follows whichever it is.
    restored = Sentence.list(setup.project_id)[0]
    assert delete.sentence_id == restored.id
    assert delete.last_adjustment.obsolete_sentence_ids == set()


# --- merge: the token moves and the annotation follows -----------------------


def test_merge_moves_the_annotation_locator_with_its_token(setup):
    token = token_named(setup.next_sentence_id, "wæs")
    annotation = annotate(token.id)
    push_command(setup.undo_stack, annotation)
    assert annotation.sentence_id == setup.next_sentence_id

    merge = merge_sentences(setup.sentence_id, setup.next_sentence_id)
    push_command(setup.undo_stack, merge)

    assert merge.last_adjustment.obsolete_sentence_ids == {setup.next_sentence_id}
    assert merge.last_adjustment.token_sentence[token.id] == setup.sentence_id
    assert annotation.token_id == token.id
    assert annotation.sentence_id == setup.sentence_id
    assert setup.undo_stack.command(0).isObsolete() is False

    assert undo_step(setup.undo_stack) is True
    new_next = Sentence.list(setup.project_id)[1]
    assert merge.next_sentence_id == new_next.id
    assert merge.last_adjustment.token_sentence[token.id] == new_next.id
    assert annotation.sentence_id == new_next.id
    assert Token.get(token.id).sentence_id == new_next.id

    assert undo_step(setup.undo_stack) is True
    assert Annotation.get_by_token(token.id).pos is None


def test_translation_of_the_merged_away_sentence_is_dropped(setup):
    push_command(
        setup.undo_stack, edit_translation(setup.next_sentence_id, "", "second")
    )
    push_command(setup.undo_stack, edit_translation(setup.sentence_id, "", "first"))
    push_command(
        setup.undo_stack, merge_sentences(setup.sentence_id, setup.next_sentence_id)
    )
    assert setup.undo_stack.command(0).isObsolete() is True
    assert setup.undo_stack.command(1).isObsolete() is False
    assert setup.undo_stack.command(2).isObsolete() is False


# --- Old English edits: a dropped surface drops the annotation ---------------


def test_oe_edit_that_drops_the_surface_makes_the_annotation_obsolete(setup):
    token = token_named(setup.sentence_id, "cyning")
    push_command(setup.undo_stack, annotate(token.id))
    edit = edit_old_english(setup.sentence_id, "Se cyning cōm.", "Se cōm.")
    push_command(setup.undo_stack, edit)
    assert edit.last_adjustment.obsolete_token_ids == {token.id}
    assert setup.undo_stack.command(0).isObsolete() is True

    assert undo_step(setup.undo_stack) is True
    assert setup.undo_stack.canUndo() is False
    assert setup.undo_stack.count() == 1


def test_oe_edit_that_keeps_the_surface_leaves_the_annotation(setup):
    token = token_named(setup.sentence_id, "cyning")
    push_command(setup.undo_stack, annotate(token.id))
    edit = edit_old_english(setup.sentence_id, "Se cyning cōm.", "Se cyning cōm nū.")
    push_command(setup.undo_stack, edit)
    assert edit.last_adjustment.obsolete_token_ids == set()
    assert setup.undo_stack.command(0).isObsolete() is False
    assert undo_step(setup.undo_stack) is True
    assert undo_step(setup.undo_stack) is True
    assert Annotation.get_by_token(token.id).pos is None


# --- snapshots are not locators ----------------------------------------------


def test_display_order_changes_on_the_add_command_are_unchanged_by_the_walk(setup):
    add = add_sentence_before(setup.project_id, setup.sentence_id)
    push_command(setup.undo_stack, add)
    snapshot = list(add.display_order_changes)
    assert snapshot  # both sentences moved down one
    push_command(setup.undo_stack, delete_sentence(setup.next_sentence_id))
    assert add.display_order_changes == snapshot
    assert add.locators().sentence_ids == {setup.sentence_id, add.new_sentence_id}
    assert setup.undo_stack.command(0).isObsolete() is False


# --- batch annotation commands keep the surviving tokens ---------------------


def test_batch_apply_drops_dead_tokens_and_keeps_the_rest(setup):
    first = token_named(setup.sentence_id, "cyning")
    second = token_named(setup.next_sentence_id, "wæs")
    before = {first.id: {"pos": None}, second.id: {"pos": None}}
    after = {first.id: {"pos": "N"}, second.id: {"pos": "V"}}
    apply = ApplyRememberedAnnotationsCommand(
        token_ids=[first.id, second.id], before=before, after=after
    )
    push_command(setup.undo_stack, apply)
    assert apply.locators() == CommandLocators(
        sentence_ids={setup.sentence_id, setup.next_sentence_id},
        token_ids={first.id, second.id},
    )

    push_command(setup.undo_stack, delete_sentence(setup.next_sentence_id))
    assert setup.undo_stack.command(0).isObsolete() is False
    assert apply.token_ids == [first.id]
    assert apply.locators().sentence_ids == {setup.sentence_id}
    assert apply.before == before  # the snapshot is not rewritten

    push_command(setup.undo_stack, delete_sentence(setup.sentence_id))
    assert setup.undo_stack.command(0).isObsolete() is True


# --- the stack settles -------------------------------------------------------


def test_redo_region_entries_on_a_removed_insert_are_dropped(setup):
    add = add_sentence_before(setup.project_id, setup.sentence_id)
    push_command(setup.undo_stack, add)
    new_id = add.new_sentence_id
    push_command(setup.undo_stack, edit_translation(new_id, "", "new words"))
    assert undo_step(setup.undo_stack) is True
    assert undo_step(setup.undo_stack) is True
    assert add.last_adjustment.obsolete_sentence_ids == {new_id}
    assert setup.undo_stack.command(1).isObsolete() is True

    assert redo_step(setup.undo_stack) is True
    assert add.new_sentence_id == Sentence.list(setup.project_id)[0].id
    assert Sentence.get(add.new_sentence_id).text_modern is None
    assert setup.undo_stack.count() == 1
    assert setup.undo_stack.canRedo() is False


def test_maintain_stack_marks_only_orphaned_entries(setup):
    stack = setup.undo_stack
    push_command(stack, edit_translation(setup.sentence_id, "", "a"))
    push_command(stack, edit_translation(setup.next_sentence_id, "", "b"))
    delete = delete_sentence(setup.next_sentence_id)
    push_command(stack, delete)
    assert [entry.isObsolete() for entry in entries(stack)] == [False, True, False]
    # Walking again with the same adjustment changes nothing.
    maintain_stack(stack, delete)
    assert [entry.isObsolete() for entry in entries(stack)] == [False, True, False]


# --- note steps follow their sentence ----------------------------------------


def add_note(sentence_id: int, text: str = "a note") -> AddNoteCommand:
    tokens = Token.list(sentence_id)
    return AddNoteCommand(
        sentence_id=sentence_id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[-1].id,
        note_text=text,
    )


def test_note_step_under_a_deleted_sentence_does_not_jam_undo(setup):
    stack = setup.undo_stack
    push_command(stack, edit_translation(setup.next_sentence_id, "", "kept"))
    push_command(stack, add_note(setup.sentence_id))
    push_command(stack, delete_sentence(setup.sentence_id))
    assert stack.command(1).isObsolete() is True
    assert undo_step(stack) is True  # undo the delete; the note step is dropped
    assert stack.count() == 2  # noqa: PLR2004
    assert stack.command(stack.index() - 1).text() == "Edit translation"
    assert undo_step(stack) is True
    assert Sentence.get(setup.next_sentence_id).text_modern == ""


def test_update_note_records_its_sentence_and_tokens(setup):
    add = add_note(setup.sentence_id)
    push_command(setup.undo_stack, add)
    note = Note.get(add.note_id)
    update = UpdateNoteCommand(
        note_id=note.id,
        before_text="a note",
        after_text="b note",
        before_start_token=note.start_token,
        before_end_token=note.end_token,
        after_start_token=note.start_token,
        after_end_token=note.end_token,
    )
    push_command(setup.undo_stack, update)
    assert update.locators() == CommandLocators(
        sentence_ids={setup.sentence_id},
        token_ids={note.start_token, note.end_token},
    )


# --- failed and dropped steps settle the stack -------------------------------


@dataclass
class FlakyCommand(Command):
    """A command whose ``execute`` succeeds once, then fails."""

    runs: int = 0

    def execute(self) -> bool:
        self.runs += 1
        return self.runs == 1

    def undo(self) -> bool:
        return True

    def menu_text(self) -> str:
        return "Flaky"


def test_redo_of_a_failing_entry_drops_the_obsolete_one_behind_it(setup):
    stack = setup.undo_stack
    push_command(stack, FlakyCommand())
    push_command(stack, FlakyCommand())
    assert undo_step(stack) is True
    assert undo_step(stack) is True
    stack.command(1).setObsolete(True)
    assert redo_step(stack) is False
    assert stack.canRedo() is False
    assert stack.count() == 0


def test_a_dropped_obsolete_entry_is_not_reported_as_undone(setup):
    stack = setup.undo_stack
    push_command(stack, FlakyCommand())
    push_command(stack, FlakyCommand())
    stack.command(1).setObsolete(True)
    assert isinstance(stack.command(1), UndoCommand)
    assert undo_step(stack) is False
    assert stack.count() == 1
    assert stack.canUndo() is True

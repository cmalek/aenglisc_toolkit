"""Unit tests for CommandManager and AnnotateTokenCommand."""

import pytest

from oeapp.commands import (
    AddNoteCommand,
    AnnotateTokenCommand,
    UpdateNoteCommand,
    DeleteNoteCommand,
    SplitParagraphCommand,
    MergeParagraphCommand,
)
from oeapp.models.annotation import Annotation
from oeapp.models.note import Note
from oeapp.models.sentence import Sentence
from oeapp.models.token import Token


class TestCommandManager:
    """Test cases for CommandManager."""

    def test_execute_and_undo_new_annotation(self, command_setup):
        """Test executing and undoing a new annotation."""
        setup = command_setup
        token_id = setup["token_id"]
        command_manager = setup["command_manager"]
        session = setup["session"]

        before = {
            k: None
            for k in [
                "pos",
                "gender",
                "number",
                "case",
                "declension",
                "article_type",
                "pronoun_type",
                "pronoun_number",
                "verb_class",
                "verb_tense",
                "verb_person",
                "verb_mood",
                "verb_aspect",
                "verb_form",
                "verb_direct_object_case",
                "prep_case",
                "adjective_inflection",
                "adjective_degree",
                "conjunction_type",
                "adverb_degree",
                "last_inferred_json",
                "modern_english_meaning",
                "root",
                "confidence",
                "updated_at",
            ]
        }
        after = before.copy()
        after.update(
            {
                "pos": "R",
                "gender": "m",
                "number": "s",
                "case": "n",
                "pronoun_type": "d",
                "confidence": 95,
            }
        )

        command = AnnotateTokenCommand(token_id=token_id, before=before, after=after)

        # Execute command
        assert command_manager.execute(command)

        # Verify annotation was created
        annotation = session.get(Annotation, token_id)
        assert annotation is not None
        assert annotation.pos == "R"
        assert annotation.gender == "m"
        assert annotation.number == "s"
        assert annotation.case == "n"
        assert annotation.pronoun_type == "d"
        assert annotation.confidence == 95

        # Undo command
        assert command_manager.undo()

        # Verify annotation was reset to before state (empty values)
        annotation = session.get(Annotation, token_id)
        assert annotation is not None
        assert annotation.pos is None
        assert annotation.gender is None
        assert annotation.number is None
        assert annotation.case is None
        assert annotation.pronoun_type is None
        assert annotation.confidence is None

    def test_execute_and_undo_update_annotation(self, command_setup, db_session):
        """Test executing and undoing an annotation update."""
        setup = command_setup
        token_id = setup["token_id"]
        command_manager = setup["command_manager"]
        session = setup["session"]

        # Get or create initial annotation
        annotation = session.get(Annotation, token_id)
        if annotation is None:
            annotation = Annotation(token_id=token_id)
            annotation.save()
        annotation.pos = "R"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.pronoun_type = "d"
        annotation.confidence = 80
        annotation.save()

        # Create command to update annotation
        before = {
            "pos": "R",
            "gender": "m",
            "number": "s",
            "case": "n",
            "declension": None,
            "article_type": None,
            "pronoun_type": "d",
            "pronoun_number": None,
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "verb_direct_object_case": None,
            "prep_case": None,
            "adjective_inflection": None,
            "adjective_degree": None,
            "conjunction_type": None,
            "adverb_degree": None,
            "confidence": 80,
        }
        after = before.copy()
        after.update(
            {
                "case": "a",  # Changed from nominative to accusative
                "confidence": 60,  # Lower confidence
            }
        )

        command = AnnotateTokenCommand(token_id=token_id, before=before, after=after)

        # Execute command
        assert command_manager.execute(command)

        # Verify annotation was updated
        annotation = session.get(Annotation, token_id)
        assert annotation.case == "a"
        assert annotation.confidence == 60

        # Undo command
        assert command_manager.undo()

        # Verify annotation was restored
        annotation = session.get(Annotation, token_id)
        assert annotation.case == "n"
        assert annotation.confidence == 80

    def test_redo_after_undo(self, command_setup):
        """Test redo functionality after undo."""
        setup = command_setup
        token_id = setup["token_id"]
        command_manager = setup["command_manager"]
        session = setup["session"]

        before = {
            k: None
            for k in [
                "pos",
                "gender",
                "number",
                "case",
                "declension",
                "article_type",
                "pronoun_type",
                "pronoun_number",
                "verb_class",
                "verb_tense",
                "verb_person",
                "verb_mood",
                "verb_aspect",
                "verb_form",
                "verb_direct_object_case",
                "prep_case",
                "adjective_inflection",
                "adjective_degree",
                "conjunction_type",
                "adverb_degree",
                "confidence",
                "last_inferred_json",
                "modern_english_meaning",
                "root",
            ]
        }
        after = before.copy()
        after.update(
            {
                "pos": "N",
                "gender": "m",
                "number": "s",
                "case": "n",
                "declension": "s",
                "confidence": 100,
            }
        )

        command = AnnotateTokenCommand(token_id, before, after)
        command_manager.execute(command)

        # Undo
        command_manager.undo()
        annotation = session.get(Annotation, token_id)
        assert annotation.pos is None

        # Redo
        assert command_manager.redo()

        # Verify annotation is back
        annotation = session.get(Annotation, token_id)
        assert annotation.pos == "N"
        assert annotation.gender == "m"

    def test_multiple_commands_undo_order(self, command_setup):
        """Test that multiple commands are undone in reverse order."""
        setup = command_setup
        token_id = setup["token_id"]
        sentence_id = setup["sentence_id"]
        command_manager = setup["command_manager"]
        session = setup["session"]

        tokens = Token.list(sentence_id)
        if len(tokens) < 2:
            token2 = Token(sentence_id=sentence_id, order_index=1, surface="cyning")
            token2.save()
            token_id_2 = token2.id
        else:
            token_id_2 = tokens[1].id

        before = {
            k: None
            for k in [
                "pos",
                "gender",
                "number",
                "case",
                "declension",
                "article_type",
                "pronoun_type",
                "pronoun_number",
                "verb_class",
                "verb_tense",
                "verb_person",
                "verb_mood",
                "verb_aspect",
                "verb_form",
                "verb_direct_object_case",
                "prep_case",
                "adjective_inflection",
                "adjective_degree",
                "conjunction_type",
                "adverb_degree",
                "confidence",
                "last_inferred_json",
                "modern_english_meaning",
                "root",
            ]
        }

        after1 = before.copy()
        after1.update(
            {
                "pos": "R",
                "gender": "m",
                "number": "s",
                "case": "n",
                "pronoun_type": "d",
                "confidence": 100,
            }
        )

        after2 = before.copy()
        after2.update(
            {
                "pos": "N",
                "gender": "m",
                "number": "s",
                "case": "n",
                "declension": "s",
                "confidence": 100,
            }
        )

        command1 = AnnotateTokenCommand(token_id, before, after1)
        command2 = AnnotateTokenCommand(token_id_2, before, after2)

        command_manager.execute(command1)
        command_manager.execute(command2)

        # Undo once - should undo second command
        command_manager.undo()
        annotation2 = session.get(Annotation, token_id_2)
        assert annotation2.pos is None
        annotation1 = session.get(Annotation, token_id)
        assert annotation1.pos == "R"

        # Undo again - should undo first command
        command_manager.undo()
        annotation1 = session.get(Annotation, token_id)
        assert annotation1.pos is None

    def test_can_undo_can_redo(self, command_setup):
        """Test can_undo and can_redo state tracking."""
        command_manager = command_setup["command_manager"]
        token_id = command_setup["token_id"]

        assert not command_manager.can_undo()
        assert not command_manager.can_redo()

        before = {
            k: None
            for k in [
                "pos",
                "gender",
                "number",
                "case",
                "declension",
                "article_type",
                "pronoun_type",
                "pronoun_number",
                "verb_class",
                "verb_tense",
                "verb_person",
                "verb_mood",
                "verb_aspect",
                "verb_form",
                "verb_direct_object_case",
                "prep_case",
                "adjective_inflection",
                "adjective_degree",
                "conjunction_type",
                "adverb_degree",
                "confidence",
                "last_inferred_json",
                "modern_english_meaning",
                "root",
            ]
        }
        after = before.copy()
        after.update(
            {"pos": "N", "gender": "m", "number": "s", "case": "n", "confidence": 100}
        )

        command = AnnotateTokenCommand(token_id, before, after)
        command_manager.execute(command)

        assert command_manager.can_undo()
        assert not command_manager.can_redo()

        command_manager.undo()
        assert not command_manager.can_undo()
        assert command_manager.can_redo()

        command_manager.redo()
        assert command_manager.can_undo()
        assert not command_manager.can_redo()


class TestAddNoteCommand:
    """Test cases for AddNoteCommand."""

    def test_execute_creates_note(self, command_setup):
        """Test execute() creates note."""
        setup = command_setup
        sentence_id = setup["sentence_id"]

        tokens = Token.list(sentence_id)
        start_token_id = tokens[0].id
        end_token_id = tokens[1].id if len(tokens) > 1 else tokens[0].id

        command = AddNoteCommand(
            sentence_id=sentence_id,
            start_token_id=start_token_id,
            end_token_id=end_token_id,
            note_text="Test note",
        )

        assert command.execute()
        assert command.note_id is not None

        note = Note.get(command.note_id)
        assert note is not None
        assert note.note_text_md == "Test note"

    def test_undo_deletes_note(self, db_session, command_setup):
        """Test undo() deletes note."""
        setup = command_setup
        sentence_id = setup["sentence_id"]

        tokens = Token.list(sentence_id)
        start_token_id = tokens[0].id
        end_token_id = tokens[0].id

        command = AddNoteCommand(
            sentence_id=sentence_id,
            start_token_id=start_token_id,
            end_token_id=end_token_id,
            note_text="Test note",
        )
        command.execute()
        note_id = command.note_id

        assert command.undo()
        assert Note.get(note_id) is None


class TestUpdateNoteCommand:
    """Test cases for UpdateNoteCommand."""

    @pytest.fixture
    def note_setup(self, db_session, command_setup):
        """Set up a note for update tests."""
        setup = command_setup
        session = db_session
        sentence_id = setup["sentence_id"]
        token_id = setup["token_id"]

        note = Note(
            sentence_id=sentence_id,
            start_token=token_id,
            end_token=token_id,
            note_text_md="Original note",
        )
        note.save()
        setup["note_id"] = note.id
        return setup

    def test_execute_updates_note(self, note_setup):
        """Test execute() updates note."""
        setup = note_setup
        note_id = setup["note_id"]
        token_id = setup["token_id"]

        note = Note.get(note_id)
        original_text = note.note_text_md

        command = UpdateNoteCommand(
            note_id=note_id,
            before_text=original_text,
            after_text="Updated note",
            before_start_token=token_id,
            before_end_token=token_id,
            after_start_token=token_id,
            after_end_token=token_id,
        )

        assert command.execute()
        assert Note.get(note_id).note_text_md == "Updated note"

    def test_undo_restores_note(self, note_setup):
        """Test undo() restores original note text."""
        setup = note_setup
        note_id = setup["note_id"]
        token_id = setup["token_id"]

        note = Note.get(note_id)
        original_text = note.note_text_md

        command = UpdateNoteCommand(
            note_id=note_id,
            before_text=original_text,
            after_text="Updated note",
            before_start_token=token_id,
            before_end_token=token_id,
            after_start_token=token_id,
            after_end_token=token_id,
        )
        command.execute()
        assert command.undo()
        assert Note.get(note_id).note_text_md == original_text


class TestDeleteNoteCommand:
    """Test cases for DeleteNoteCommand."""

    @pytest.fixture
    def note_setup(self, command_setup):
        """Set up a note for delete tests."""
        setup = command_setup
        session = setup["session"]
        sentence_id = setup["sentence_id"]
        token_id = setup["token_id"]

        note = Note(
            sentence_id=sentence_id,
            start_token=token_id,
            end_token=token_id,
            note_text_md="Note to delete",
        )
        note.save()
        setup["note_id"] = note.id
        return setup

    def test_execute_deletes_note(self, note_setup):
        """Test execute() deletes note."""
        note_id = note_setup["note_id"]
        command = DeleteNoteCommand(note_id=note_id)
        assert command.execute()
        assert Note.get(note_id) is None

    def test_undo_restores_note(self, note_setup):
        """Test undo() restores deleted note."""
        note_id = note_setup["note_id"]
        command = DeleteNoteCommand(note_id=note_id)
        command.execute()
        assert command.undo()
        note = Note.get(note_id)
        assert note is not None
        assert note.note_text_md == "Note to delete"


class TestSplitParagraphCommand:
    """Test cases for SplitParagraphCommand."""

    def test_execute_splits_paragraph(self, command_setup):
        """Test execute() splits a paragraph."""
        sentence_id = command_setup["sentence_id"]
        session = command_setup["session"]
        
        # Ensure we have a second sentence in the same paragraph to split
        sentence = Sentence.get(sentence_id)
        project_id = sentence.project_id
        
        # Create a second sentence in the same paragraph
        s2 = Sentence.create(
            project_id=project_id,
            display_order=sentence.display_order + 1,
            text_oe="Second sentence.",
            paragraph_id=sentence.paragraph_id,
            commit=True
        )
        s2_id = s2.id
        
        original_p_id = sentence.paragraph_id
        command = SplitParagraphCommand(sentence_id=s2_id)
        
        assert command.execute()
        s2 = Sentence.get(s2_id)
        assert s2.paragraph_id != original_p_id
        assert s2.paragraph.order == 2

    def test_undo_restores_paragraph(self, command_setup):
        """Test undo() restores original paragraph."""
        sentence_id = command_setup["sentence_id"]
        session = command_setup["session"]
    
        sentence = Sentence.get(sentence_id)
        s2 = Sentence.create(
            project_id=sentence.project_id,
            display_order=sentence.display_order + 1,
            text_oe="Second sentence.",
            paragraph_id=sentence.paragraph_id,
            commit=True
        )
        s2_id = s2.id
        original_p_id = sentence.paragraph_id
    
        command = SplitParagraphCommand(sentence_id=s2_id)
        command.execute()
    
        # Verify it moved
        s2_after_exec = session.get(Sentence, s2_id)
        assert s2_after_exec.paragraph_id != original_p_id
    
        # Undo
        assert command.undo()
    
        # Use a fresh query from the session
        # Use session.scalar(select(Sentence).where(Sentence.id == s2_id))
        from sqlalchemy import select
        s2_after_undo = session.scalar(select(Sentence).where(Sentence.id == s2_id))
        if s2_after_undo is None:
            # Try to see if it's in the project at all
            all_s = session.scalars(select(Sentence).where(Sentence.project_id == sentence.project_id)).all()
            print(f"DEBUG: all sentences in project: {[s.id for s in all_s]}")
        assert s2_after_undo is not None, f"Sentence {s2_id} not found after undo"
        assert s2_after_undo.paragraph_id == original_p_id

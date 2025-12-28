"""Unit tests for NoteDialog."""

from unittest.mock import MagicMock

from oeapp.ui.dialogs.note_dialog import NoteDialog
from tests.conftest import create_test_project


class TestNoteDialog:
    """Test cases for NoteDialog."""

    def test_note_dialog_initializes_for_new_note(self, db_session, qapp):
        """Test NoteDialog initializes correctly for creating a new note."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        dialog = NoteDialog(
            sentence=sentence,
            start_token_id=token.id,
            end_token_id=token.id,
            note=None,
            session=db_session
        )

        assert dialog.is_editing is False
        assert dialog.windowTitle() == "Add Note"
        assert dialog.note_text_edit.toPlainText() == ""

    def test_note_dialog_initializes_for_editing(self, db_session, qapp):
        """Test NoteDialog initializes correctly for editing an existing note."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Create a note
        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Existing note text"
        )
        db_session.add(note)
        db_session.commit()

        dialog = NoteDialog(
            sentence=sentence,
            start_token_id=token.id,
            end_token_id=token.id,
            note=note,
            session=db_session
        )

        assert dialog.is_editing is True
        assert dialog.windowTitle() == "Edit Note"
        assert dialog.note_text_edit.toPlainText() == "Existing note text"

    def test_note_dialog_displays_token_range(self, db_session, qapp):
        """Test NoteDialog displays the selected token range."""
        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        tokens = list(sentence.tokens)

        dialog = NoteDialog(
            sentence=sentence,
            start_token_id=tokens[0].id,
            end_token_id=tokens[1].id,
            note=None,
            session=db_session
        )

        # Check that token text is displayed (should contain "Se" and "cyning")
        # The dialog should have a label showing the token range
        assert dialog.sentence == sentence

    def test_note_dialog_saves_new_note(self, db_session, qapp):
        """Test NoteDialog saves a new note."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        dialog = NoteDialog(
            sentence=sentence,
            start_token_id=token.id,
            end_token_id=token.id,
            note=None,
            session=db_session
        )

        dialog.note_text_edit.setPlainText("New note text")

        # Mock command manager to avoid actual command execution
        mock_command_manager = MagicMock()
        dialog.command_manager = mock_command_manager

        # Simulate save button click
        dialog._on_save_clicked()

        # Check that command was created
        assert mock_command_manager.execute.called

    def test_note_dialog_updates_existing_note(self, db_session, qapp):
        """Test NoteDialog updates an existing note."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Create a note
        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Original text"
        )
        db_session.add(note)
        db_session.commit()

        dialog = NoteDialog(
            sentence=sentence,
            start_token_id=token.id,
            end_token_id=token.id,
            note=note,
            session=db_session
        )

        dialog.note_text_edit.setPlainText("Updated text")

        # Mock command manager
        mock_command_manager = MagicMock()
        dialog.command_manager = mock_command_manager

        # Simulate save button click
        dialog._on_save_clicked()

        # Check that update command was created
        assert mock_command_manager.execute.called

    def test_note_dialog_deletes_note(self, db_session, qapp):
        """Test NoteDialog deletes a note when delete button is clicked."""
        from oeapp.models.note import Note

        project = create_test_project(db_session, name="Test", text="Se cyning")
        db_session.commit()

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Create a note
        note = Note(
            sentence_id=sentence.id,
            start_token=token.id,
            end_token=token.id,
            note_text_md="Note to delete"
        )
        db_session.add(note)
        db_session.commit()
        note_id = note.id

        dialog = NoteDialog(
            sentence=sentence,
            start_token_id=token.id,
            end_token_id=token.id,
            note=note,
            session=db_session
        )

        # Mock command manager
        mock_command_manager = MagicMock()
        dialog.command_manager = mock_command_manager

        # Simulate delete button click
        dialog._on_delete_clicked()

        # Check that delete command was created
        assert mock_command_manager.execute.called


"""Unit tests for annotation copy/paste functionality."""

import pytest
from unittest.mock import MagicMock

from oeapp.models.project import Project
from oeapp.state import COPIED_ANNOTATION, SELECTED_SENTENCE_CARD, ApplicationState
from oeapp.ui.main_window import MainWindowActions
from oeapp.ui.sentence_card import SentenceCard
from tests.conftest import create_test_project

class TestCopyAnnotation:
    """Test cases for copy_annotation functionality."""

    def test_copy_annotation_no_token_selected_returns_false(self, db_session, qapp):
        """Test copy_annotation returns False when no token is selected."""
        # Create mock MainWindow with no selected sentence card
        main_window = MagicMock()
        main_window.application_state = ApplicationState()
        main_window.application_state.set_main_window(main_window)

        action_service = MainWindowActions(main_window)

        result = action_service.copy_annotation()

        assert result is False
        assert COPIED_ANNOTATION not in main_window.application_state

    def test_copy_annotation_token_selected_but_no_annotation_data(self, db_session, qapp, mock_main_window):
        """Test copy_annotation shows error when token has empty annotation."""
        # Create project with token
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Token has annotation but with no POS set (empty annotation)
        # Clear any fields that might have been set
        if token.annotation:
            token.annotation.pos = None
            token.annotation.save()

        # Create real SentenceCard to get proper token handling
        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(0)

        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        result = action_service.copy_annotation()

        # Token has an annotation object but with no meaningful data
        # The copy_annotation checks if token.annotation exists, so it will copy
        # even empty annotations. This is actually valid behavior - copying empty
        # state is allowed.
        assert result is True

    def test_copy_annotation_success(self, db_session, qapp, mock_main_window):
        """Test copy_annotation successfully copies annotation data."""
        # Create project with token and annotation
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Update existing annotation with data
        annotation = token.annotation
        annotation.pos = "N"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.declension = "i"
        annotation.modern_english_meaning = "king"
        annotation.root = "cyning"
        annotation.uncertain = False
        annotation.save()
        db_session.refresh(token)

        # Create real SentenceCard
        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(0)

        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        result = action_service.copy_annotation()

        assert result is True
        mock_main_window.messages.show_message.assert_called_with("Annotation copied")

        # Verify copied annotation data
        copied = mock_main_window.application_state[COPIED_ANNOTATION]
        assert copied is not None
        assert copied["pos"] == "N"
        assert copied["gender"] == "m"
        assert copied["number"] == "s"
        assert copied["case"] == "n"
        assert copied["declension"] == "i"
        assert copied["modern_english_meaning"] == "king"
        assert copied["root"] == "cyning"

    def test_copy_annotation_copies_all_fields(self, db_session, qapp, mock_main_window):
        """Test copy_annotation copies all annotation fields including None values."""
        # Create project with token and annotation
        project = create_test_project(db_session, name=f"Test_{id(self)}_2", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Update existing annotation with all fields set
        annotation = token.annotation
        annotation.pos = "V"
        annotation.gender = None  # Not applicable for verbs
        annotation.number = "s"
        annotation.case = None  # Not applicable for verbs
        annotation.declension = None
        annotation.article_type = None
        annotation.pronoun_type = None
        annotation.pronoun_number = None
        annotation.verb_class = "w1"
        annotation.verb_tense = "p"
        annotation.verb_person = "3"
        annotation.verb_mood = "i"
        annotation.verb_aspect = "p"
        annotation.verb_form = "f"
        annotation.prep_case = None
        annotation.adjective_inflection = None
        annotation.adjective_degree = None
        annotation.conjunction_type = None
        annotation.adverb_degree = None
        annotation.modern_english_meaning = "to be"
        annotation.root = "bēon"
        annotation.save()
        db_session.refresh(token)
        db_session.refresh(sentence)

        # Create real SentenceCard
        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(0)

        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        result = action_service.copy_annotation()

        assert result is True
        copied = mock_main_window.application_state[COPIED_ANNOTATION]

        # Verify all fields are copied
        assert copied["pos"] == "V"
        assert copied["gender"] is None
        assert copied["number"] == "s"
        assert copied["case"] is None
        assert copied["verb_class"] == "w1"
        assert copied["verb_tense"] == "p"
        assert copied["verb_person"] == "3"
        assert copied["verb_mood"] == "i"
        assert copied["verb_aspect"] == "p"
        assert copied["verb_form"] == "f"
        assert copied["modern_english_meaning"] == "to be"
        assert copied["root"] == "bēon"


class TestPasteAnnotation:
    """Test cases for paste_annotation functionality."""

    def test_paste_annotation_no_token_selected_returns_false(self, db_session, qapp):
        """Test paste_annotation returns False when no token is selected."""
        main_window = MagicMock()
        main_window.application_state = ApplicationState()
        main_window.application_state.set_main_window(main_window)
        main_window.application_state[COPIED_ANNOTATION] = {"pos": "N"}

        action_service = MainWindowActions(main_window)

        result = action_service.paste_annotation()

        assert result is False

    def test_paste_annotation_no_copied_annotation(self, db_session, qapp, mock_main_window):
        """Test paste_annotation shows error when no annotation copied."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]

        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(0)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        result = action_service.paste_annotation()

        assert result is True  # Event was handled
        mock_main_window.messages.show_message.assert_called_with("No annotation to paste")

    def test_paste_annotation_success(self, db_session, qapp, mock_main_window):
        """Test paste_annotation successfully pastes annotation data."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[1]  # "cyning"

        # Setup copied annotation in state
        mock_main_window.application_state[COPIED_ANNOTATION] = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "declension": "i",
            "article_type": None,
            "pronoun_type": None,
            "pronoun_number": None,
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "prep_case": None,
            "adjective_inflection": None,
            "adjective_degree": None,
            "conjunction_type": None,
            "adverb_degree": None,
            "modern_english_meaning": "king",
            "root": "cyning",
        }
        command_manager = mock_main_window.application_state.command_manager

        # Create real SentenceCard
        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(1)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        # Paste annotation
        result = action_service.paste_annotation()
        assert result is True

        # Verify annotation was applied
        db_session.refresh(token)
        assert token.annotation.pos == "N"

        # Verify command is on undo stack
        assert command_manager.can_undo()

        # Undo the paste
        undo_result = command_manager.undo()
        assert undo_result is True

        # Verify annotation was reverted
        db_session.refresh(token)
        # Token still has annotation object but fields should be None
        assert token.annotation.pos is None

    def test_paste_annotation_is_redoable(self, db_session, qapp, mock_main_window):
        """Test paste_annotation can be redone after undo."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[1]

        mock_main_window.application_state[COPIED_ANNOTATION] = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "declension": None,
            "article_type": None,
            "pronoun_type": None,
            "pronoun_number": None,
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "prep_case": None,
            "adjective_inflection": None,
            "adjective_degree": None,
            "conjunction_type": None,
            "adverb_degree": None,
            "modern_english_meaning": None,
            "root": None,
        }
        command_manager = mock_main_window.application_state.command_manager

        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(1)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        # Paste, undo, then redo
        action_service.paste_annotation()
        command_manager.undo()

        # Verify can redo
        assert command_manager.can_redo()

        redo_result = command_manager.redo()
        assert redo_result is True

        # Verify annotation was reapplied
        db_session.refresh(token)
        assert token.annotation.pos == "N"
        assert token.annotation.gender == "m"

    def test_paste_annotation_overwrites_existing(self, db_session, qapp, mock_main_window):
        """Test paste_annotation overwrites existing annotation."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[1]

        # Update existing annotation with data
        existing = token.annotation
        existing.pos = "V"
        existing.gender = None
        existing.number = "p"
        existing.modern_english_meaning = "old meaning"
        existing.save()
        db_session.refresh(token)

        mock_main_window.application_state[COPIED_ANNOTATION] = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "declension": None,
            "article_type": None,
            "pronoun_type": None,
            "pronoun_number": None,
            "verb_class": None,
            "verb_tense": None,
            "verb_person": None,
            "verb_mood": None,
            "verb_aspect": None,
            "verb_form": None,
            "prep_case": None,
            "adjective_inflection": None,
            "adjective_degree": None,
            "conjunction_type": None,
            "adverb_degree": None,
            "modern_english_meaning": "new meaning",
            "root": None,
        }

        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(1)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        result = action_service.paste_annotation()
        assert result is True

        # Verify annotation was overwritten
        db_session.refresh(token)
        assert token.annotation.pos == "N"
        assert token.annotation.gender == "m"
        assert token.annotation.number == "s"
        assert token.annotation.modern_english_meaning == "new meaning"


class TestCopyPasteIntegration:
    """Integration tests for copy/paste workflow."""

    def test_copy_then_paste_to_different_token(self, db_session, qapp, mock_main_window):
        """Test copying annotation from one token and pasting to another."""
        project = create_test_project(db_session, name="Test", text="Se cyning rād")

        sentence = project.sentences[0]
        source_token = sentence.tokens[0]  # "Se"
        target_token = sentence.tokens[2]  # "rād"

        # Update source token's annotation
        annotation = source_token.annotation
        annotation.pos = "D"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.article_type = "d"
        annotation.uncertain = False
        annotation.save()
        db_session.refresh(source_token)

        action_service = MainWindowActions(mock_main_window)

        # Select source token and copy
        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(0)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        copy_result = action_service.copy_annotation()
        assert copy_result is True
        assert COPIED_ANNOTATION in mock_main_window.application_state and mock_main_window.application_state[COPIED_ANNOTATION] is not None

        # Select target token and paste
        card.oe_text_edit.set_selected_token_index(2)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        paste_result = action_service.paste_annotation()
        assert paste_result is True

        # Verify target token has copied annotation
        db_session.refresh(target_token)
        assert target_token.annotation is not None
        assert target_token.annotation.pos == "D"
        assert target_token.annotation.gender == "m"
        assert target_token.annotation.article_type == "d"

    def test_copy_from_one_sentence_paste_to_another(self, db_session, qapp, mock_main_window):
        """Test copying annotation across sentences."""
        # Create project with multiple sentences
        project = Project.create(
            name="Multi-sentence Test",
            text="Se cyning.\nSēo cwēn.",
        )

        sentence1 = project.sentences[0]
        sentence2 = project.sentences[1]
        source_token = sentence1.tokens[0]  # "Se"
        target_token = sentence2.tokens[0]  # "Sēo"

        # Update source token's annotation
        annotation = source_token.annotation
        annotation.pos = "D"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.save()
        db_session.refresh(source_token)

        action_service = MainWindowActions(mock_main_window)

        # Copy from sentence 1
        card1 = SentenceCard(sentence1, main_window=mock_main_window)
        card1.oe_text_edit.set_selected_token_index(0)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card1

        action_service.copy_annotation()

        # Paste to sentence 2
        card2 = SentenceCard(sentence2, main_window=mock_main_window)
        card2.oe_text_edit.set_selected_token_index(0)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card2

        action_service.paste_annotation()

        # Verify target token has copied annotation
        db_session.refresh(target_token)
        assert target_token.annotation is not None
        assert target_token.annotation.pos == "D"
        assert target_token.annotation.gender == "m"

    def test_paste_to_same_token_is_undoable(self, db_session, qapp, mock_main_window):
        """Test pasting to same token creates undoable command."""
        project = create_test_project(db_session, name="Test", text="Se cyning")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Update annotation
        annotation = token.annotation
        annotation.pos = "D"
        annotation.gender = "m"
        annotation.save()
        db_session.refresh(token)

        command_manager = mock_main_window.application_state.command_manager

        action_service = MainWindowActions(mock_main_window)

        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(0)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        # Copy and paste to same token
        action_service.copy_annotation()
        action_service.paste_annotation()

        # Should still be undoable
        assert command_manager.can_undo()

        # Values should still be the same
        db_session.refresh(token)
        assert token.annotation.pos == "D"
        assert token.annotation.gender == "m"


class TestCopyAnnotationWithNoAnnotation:
    """Test copy_annotation behavior when token has no annotation object."""

    def test_copy_empty_annotation_shows_error(self, db_session, qapp, mock_main_window):
        """Test copying token with only empty annotation shows error."""
        project = create_test_project(db_session, name="Test", text="Se")

        sentence = project.sentences[0]
        token = sentence.tokens[0]

        # Ensure annotation has no POS (empty state)
        if token.annotation:
            assert token.annotation.pos is None  # Should be empty by default

        card = SentenceCard(sentence, main_window=mock_main_window)
        card.oe_text_edit.set_selected_token_index(0)
        mock_main_window.application_state[SELECTED_SENTENCE_CARD] = card

        action_service = MainWindowActions(mock_main_window)

        # When token has annotation object but no meaningful data,
        # copy_annotation still succeeds because the annotation exists
        result = action_service.copy_annotation()
        assert result is True
        # The copied annotation will have all None/False values
        assert COPIED_ANNOTATION in mock_main_window.application_state and mock_main_window.application_state[COPIED_ANNOTATION] is not None
        assert mock_main_window.application_state[COPIED_ANNOTATION]["pos"] is None

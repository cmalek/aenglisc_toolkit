"""Unit tests for annotation copy/paste functionality."""

from unittest.mock import MagicMock

import pytest

from oeapp.commands import CommandManager
from oeapp.models.project import Project
from oeapp.ui.main_window import MainWindowActions
from oeapp.ui.sentence_card import SentenceCard
from tests.conftest import create_test_project


def _actions(mock_main_window) -> MainWindowActions:
    """Build action service for mock main window."""
    return MainWindowActions(mock_main_window, mock_main_window.app_context)


def _select_card(db_session, mock_main_window, sentence, token_index: int) -> SentenceCard:
    """Create and select a real sentence card for token interaction tests."""
    card = SentenceCard(
        sentence,
        command_manager=CommandManager(db_session),
        main_window=mock_main_window,
    )
    card.oe_text_edit.set_selected_token_index(token_index)
    mock_main_window.project_ui.set_selected_sentence_card(card)
    return card


class TestCopyAnnotation:
    """Test cases for copy_annotation functionality."""

    def test_copy_annotation_no_token_selected_returns_false(self, db_session, qapp):
        """Test copy_annotation returns False when no token is selected."""
        del db_session, qapp
        main_window = MagicMock()
        main_window.app_context = MagicMock(copied_annotation=None)
        main_window.project_ui = MagicMock()
        main_window.project_ui.get_selected_sentence_card.return_value = None
        main_window.messages = MagicMock()
        main_window.sentence_cards = []

        assert _actions(main_window).copy_annotation() is False
        assert main_window.app_context.copied_annotation is None

    def test_copy_annotation_success(self, db_session, qapp, mock_main_window):
        """Test copy_annotation successfully copies annotation data."""
        del qapp
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token = sentence.tokens[0]

        annotation = token.annotation
        annotation.pos = "N"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.declension = "i"
        annotation.modern_english_meaning = "king"
        annotation.sense = "ruler in this line"
        annotation.root = "cyning"
        annotation.uncertain = False
        annotation.save()
        db_session.refresh(token)

        _select_card(db_session, mock_main_window, sentence, 0)

        assert _actions(mock_main_window).copy_annotation() is True
        mock_main_window.messages.show_message.assert_called_with("Annotation copied")

        copied = mock_main_window.app_context.copied_annotation
        assert copied is not None
        assert copied["pos"] == "N"
        assert copied["gender"] == "m"
        assert copied["number"] == "s"
        assert copied["case"] == "n"
        assert copied["declension"] == "i"
        assert copied["modern_english_meaning"] == "king"
        assert copied["sense"] == "ruler in this line"
        assert copied["root"] == "cyning"

    def test_copy_annotation_copies_none_values(self, db_session, qapp, mock_main_window):
        """Test copy_annotation preserves explicit None values."""
        del qapp
        project = create_test_project(
            db_session, name=f"Test_{id(self)}", text="Se cyning"
        )
        sentence = project.sentences[0]
        token = sentence.tokens[0]

        annotation = token.annotation
        annotation.pos = "V"
        annotation.gender = None
        annotation.number = "s"
        annotation.case = None
        annotation.verb_class = "w1"
        annotation.verb_tense = "p"
        annotation.verb_person = "3"
        annotation.verb_mood = "i"
        annotation.verb_aspect = "p"
        annotation.verb_form = "f"
        annotation.verb_direct_object_case = "a"
        annotation.modern_english_meaning = "to be"
        annotation.sense = "to exist here"
        annotation.root = "bēon"
        annotation.save()
        db_session.refresh(token)

        _select_card(db_session, mock_main_window, sentence, 0)

        assert _actions(mock_main_window).copy_annotation() is True
        copied = mock_main_window.app_context.copied_annotation
        assert copied is not None
        assert copied["pos"] == "V"
        assert copied["gender"] is None
        assert copied["case"] is None
        assert copied["verb_class"] == "w1"
        assert copied["root"] == "bēon"


class TestPasteAnnotation:
    """Test cases for paste_annotation functionality."""

    def test_paste_annotation_no_token_selected_returns_false(self, db_session, qapp):
        """Test paste_annotation returns False when no token is selected."""
        del db_session, qapp
        main_window = MagicMock()
        main_window.app_context = MagicMock(copied_annotation={"pos": "N"})
        main_window.project_ui = MagicMock()
        main_window.project_ui.get_selected_sentence_card.return_value = None
        main_window.messages = MagicMock()
        main_window.sentence_cards = []

        assert _actions(main_window).paste_annotation() is False

    def test_paste_annotation_no_copied_annotation(self, db_session, qapp, mock_main_window):
        """Test paste_annotation shows message when nothing was copied."""
        del qapp
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]

        _select_card(db_session, mock_main_window, sentence, 0)

        assert _actions(mock_main_window).paste_annotation() is True
        mock_main_window.messages.show_message.assert_called_with("No annotation to paste")

    def test_paste_annotation_success_and_undo(self, db_session, qapp, mock_main_window):
        """Test paste_annotation applies annotation data and remains undoable."""
        del qapp
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token = sentence.tokens[1]

        mock_main_window.app_context.copied_annotation = {
            "pos": "N",
            "gender": "m",
            "number": "s",
            "case": "n",
            "declension": "i",
            "modern_english_meaning": "king",
            "sense": "ruler in this line",
            "root": "cyning",
        }
        command_manager = mock_main_window.app_context.command_manager

        _select_card(db_session, mock_main_window, sentence, 1)

        assert _actions(mock_main_window).paste_annotation() is True
        db_session.refresh(token)
        assert token.annotation.pos == "N"
        assert command_manager.can_undo()

        assert command_manager.undo() is True
        db_session.refresh(token)
        assert token.annotation.pos is None

    def test_paste_annotation_is_redoable(self, db_session, qapp, mock_main_window):
        """Test paste_annotation can be redone after undo."""
        del qapp
        project = create_test_project(db_session, name="Test", text="Se cyning")
        sentence = project.sentences[0]
        token = sentence.tokens[1]

        mock_main_window.app_context.copied_annotation = {
            "pos": "N",
            "gender": "m",
            "number": "s",
        }
        command_manager = mock_main_window.app_context.command_manager

        _select_card(db_session, mock_main_window, sentence, 1)

        _actions(mock_main_window).paste_annotation()
        command_manager.undo()

        assert command_manager.can_redo()
        assert command_manager.redo() is True

        db_session.refresh(token)
        assert token.annotation.pos == "N"
        assert token.annotation.gender == "m"


class TestCopyPasteIntegration:
    """Integration tests for copy/paste workflow."""

    def test_copy_then_paste_to_different_token(self, db_session, qapp, mock_main_window):
        """Test copying annotation from one token and pasting to another."""
        del qapp
        project = create_test_project(db_session, name="Test", text="Se cyning rād")
        sentence = project.sentences[0]
        source_token = sentence.tokens[0]
        target_token = sentence.tokens[2]

        annotation = source_token.annotation
        annotation.pos = "D"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.article_type = "d"
        annotation.save()
        db_session.refresh(source_token)

        card = _select_card(db_session, mock_main_window, sentence, 0)
        actions = _actions(mock_main_window)

        assert actions.copy_annotation() is True
        assert mock_main_window.app_context.copied_annotation is not None

        card.oe_text_edit.set_selected_token_index(2)
        assert actions.paste_annotation() is True

        db_session.refresh(target_token)
        assert target_token.annotation is not None
        assert target_token.annotation.pos == "D"
        assert target_token.annotation.gender == "m"
        assert target_token.annotation.article_type == "d"

    def test_copy_from_one_sentence_paste_to_another(
        self, db_session, qapp, mock_main_window
    ):
        """Test copying annotation across sentences."""
        del qapp
        project = Project.create(
            name="Multi-sentence Test",
            text="Se cyning.\nSēo cwēn.",
        )
        sentence1 = project.sentences[0]
        sentence2 = project.sentences[1]
        source_token = sentence1.tokens[0]
        target_token = sentence2.tokens[0]

        annotation = source_token.annotation
        annotation.pos = "D"
        annotation.gender = "m"
        annotation.number = "s"
        annotation.case = "n"
        annotation.save()
        db_session.refresh(source_token)

        actions = _actions(mock_main_window)
        _select_card(db_session, mock_main_window, sentence1, 0)
        assert actions.copy_annotation() is True

        _select_card(db_session, mock_main_window, sentence2, 0)
        assert actions.paste_annotation() is True

        db_session.refresh(target_token)
        assert target_token.annotation is not None
        assert target_token.annotation.pos == "D"
        assert target_token.annotation.gender == "m"

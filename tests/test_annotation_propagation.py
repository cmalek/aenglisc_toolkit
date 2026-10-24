# ruff: noqa: ARG002, I001, N802, S101
"""Tests for annotation propagation workflows."""

from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QUndoStack

from oeapp.commands import push_command
from oeapp.models import Project
from oeapp.services.annotation_propagation import AnnotationPropagationService
from oeapp.ui.main_window import MainWindowActions
from oeapp.ui.sentence_card import SentenceCard

from tests.conftest import create_test_project, create_test_sentence


def _actions(mock_main_window) -> MainWindowActions:
    """Build action service for mock main window."""
    return MainWindowActions(mock_main_window, mock_main_window.app_context)


def _select_card(
    db_session, mock_main_window, sentence, token_index: int
) -> SentenceCard:
    """Create and select real sentence card for token interaction tests."""
    card = SentenceCard(
        sentence,
        undo_stack=QUndoStack(),
        main_window=mock_main_window,
    )
    card.oe_text_edit.set_selected_token_index(token_index)
    mock_main_window.project_ui.set_selected_sentence_card(card)
    return card


class TestAnnotationPropagationService:
    """Service-level propagation planning tests."""

    def test_plan_surface_propagation_matches_normalized_surface_across_project(
        self, db_session
    ):
        project = Project.create(
            name="Surface Match", text="Sē cyning. Se cyning. sē eorl."
        )
        tokens = [token for sentence in project.sentences for token in sentence.tokens]
        source_token = next(token for token in tokens if token.surface == "Sē")
        untouched_token = next(token for token in tokens if token.surface == "Se")
        target_token = next(token for token in tokens if token.surface == "sē")

        source_annotation = source_token.annotation
        source_annotation.pos = "D"
        source_annotation.gender = "m"
        source_annotation.number = "s"
        source_annotation.case = "n"
        source_annotation.article_type = "d"
        source_annotation.modern_english_meaning = "the"
        source_annotation.sense = "specific article in first sentence"
        source_annotation.root = "se"
        source_annotation.save()

        plan = AnnotationPropagationService().plan_surface_propagation(
            project.id, source_token
        )

        assert plan.updated_count == 1
        assert plan.affected_token_ids == [target_token.id]
        assert untouched_token.id not in plan.affected_token_ids
        assert plan.command.after[target_token.id]["pos"] == "D"
        assert plan.command.after[target_token.id]["modern_english_meaning"] == "the"
        assert "sense" not in plan.command.after[target_token.id]

    def test_plan_surface_propagation_only_updates_safe_empty_targets(self, db_session):
        project = create_test_project(
            db_session,
            name="Surface Safe Filter",
            text="Se cyning. Se cwēn. Se eorl.",
        )
        source_token = project.sentences[0].tokens[0]
        blocked_token = project.sentences[1].tokens[0]
        updated_token = project.sentences[2].tokens[0]

        source_annotation = source_token.annotation
        source_annotation.pos = "D"
        source_annotation.gender = "m"
        source_annotation.number = "s"
        source_annotation.case = "n"
        source_annotation.article_type = "d"
        source_annotation.modern_english_meaning = "the"
        source_annotation.save()

        blocked_annotation = blocked_token.annotation
        blocked_annotation.pos = "D"
        blocked_annotation.modern_english_meaning = "that"
        blocked_annotation.save()

        plan = AnnotationPropagationService().plan_surface_propagation(
            project.id, source_token
        )

        assert plan.updated_count == 1
        assert plan.affected_token_ids == [updated_token.id]
        assert blocked_token.id not in plan.affected_token_ids

    def test_plan_meaning_propagation_only_overwrites_meaning_for_same_root(
        self, db_session
    ):
        project = create_test_project(
            db_session,
            name="Meaning Match",
            text="cyning eorl.",
        )
        source_token = project.sentences[0].tokens[0]
        sentence2 = create_test_sentence(
            db_session, project_id=project.id, text="cyninge cyninges.", display_order=2
        )
        target_token = sentence2.tokens[0]

        source_annotation = source_token.annotation
        source_annotation.pos = "N"
        source_annotation.gender = "m"
        source_annotation.number = "s"
        source_annotation.case = "n"
        source_annotation.declension = "i"
        source_annotation.root = "cyning"
        source_annotation.modern_english_meaning = "king"
        source_annotation.save()

        target_annotation = target_token.annotation
        target_annotation.pos = "N"
        target_annotation.gender = "m"
        target_annotation.number = "s"
        target_annotation.case = "d"
        target_annotation.declension = "i"
        target_annotation.root = "cyning"
        target_annotation.modern_english_meaning = "ruler"
        target_annotation.sense = "dative use"
        target_annotation.save()

        plan = AnnotationPropagationService().plan_meaning_propagation(
            project.id, source_token
        )

        assert plan.updated_count == 1
        assert plan.affected_token_ids == [target_token.id]
        assert plan.command.after[target_token.id]["modern_english_meaning"] == "king"
        assert plan.command.after[target_token.id]["sense"] == "dative use"
        assert plan.command.after[target_token.id]["case"] == "d"


    def test_plan_meaning_propagation_keeps_length_marks(self, db_session):
        """A root with a macron does not overwrite the same letters without one."""
        project = create_test_project(
            db_session, name="Meaning Length", text="gōd god Gōd."
        )
        tokens = project.sentences[0].tokens
        source, short, capital = tokens[0], tokens[1], tokens[2]
        source.annotation.root = "gōd"
        source.annotation.modern_english_meaning = "good"
        source.annotation.save()
        short.annotation.root = "god"
        short.annotation.modern_english_meaning = "God"
        short.annotation.save()
        capital.annotation.root = "Gōd"
        capital.annotation.modern_english_meaning = "goods"
        capital.annotation.save()

        plan = AnnotationPropagationService().plan_meaning_propagation(
            project.id, source
        )

        assert plan.affected_token_ids == [capital.id]
        assert "gōd" in plan.dialog_message
        assert plan.command.after[capital.id]["modern_english_meaning"] == "good"
        assert short.id not in plan.affected_token_ids

    def test_plan_meaning_propagation_skips_source_token(self, db_session):
        project = create_test_project(
            db_session, name="Meaning Skip Source", text="cyning"
        )
        source_token = project.sentences[0].tokens[0]
        source_annotation = source_token.annotation
        source_annotation.root = "cyning"
        source_annotation.modern_english_meaning = "king"
        source_annotation.save()

        plan = AnnotationPropagationService().plan_meaning_propagation(
            project.id, source_token
        )

        assert plan.updated_count == 0
        assert plan.affected_token_ids == []
        assert plan.dialog_message == "No matching words found"

    def test_apply_annotation_propagation_command_is_undoable_and_redoable(
        self, db_session
    ):
        project = create_test_project(
            db_session, name="Undo Redo", text="Sē cyning. sē eorl."
        )
        tokens = project.sentences[0].tokens
        source_token = next(token for token in tokens if token.surface == "Sē")
        target_token = next(token for token in tokens if token.surface == "sē")
        source_annotation = source_token.annotation
        source_annotation.pos = "D"
        source_annotation.gender = "m"
        source_annotation.number = "s"
        source_annotation.case = "n"
        source_annotation.article_type = "d"
        source_annotation.modern_english_meaning = "the"
        source_annotation.save()

        plan = AnnotationPropagationService().plan_surface_propagation(
            project.id, source_token
        )
        undo_stack = QUndoStack()

        assert push_command(undo_stack, plan.command) is True
        db_session.refresh(target_token)
        assert target_token.annotation.pos == "D"

        undo_stack.undo()
        db_session.refresh(target_token)
        assert target_token.annotation.pos is None

        undo_stack.redo()
        db_session.refresh(target_token)
        assert target_token.annotation.pos == "D"


class TestAnnotationPropagationActions:
    """Action-level propagation tests."""

    def test_propagate_token_annotation_shows_info_and_refreshes(
        self, db_session, mock_main_window
    ):
        project = create_test_project(
            db_session, name="Action Surface", text="Sē cyning.\nsē eorl."
        )
        source_token = project.sentences[0].tokens[0]
        source_annotation = source_token.annotation
        source_annotation.pos = "D"
        source_annotation.gender = "m"
        source_annotation.number = "s"
        source_annotation.case = "n"
        source_annotation.article_type = "d"
        source_annotation.modern_english_meaning = "the"
        source_annotation.save()

        mock_main_window.app_context.current_project_id = project.id

        actions = _actions(mock_main_window)
        actions.propagate_token_annotation(source_token)

        mock_main_window.refresh_project.assert_called_once()
        mock_main_window.messages.show_information.assert_called_once()
        message = mock_main_window.messages.show_information.call_args.args[0]
        assert message.startswith("1 words updated to match ")
        assert "sē" in message

    def test_force_propagate_token_meaning_no_match_shows_exact_message(
        self, db_session, mock_main_window
    ):
        project = create_test_project(db_session, name="Action Meaning", text="cyning")
        source_token = project.sentences[0].tokens[0]
        source_annotation = source_token.annotation
        source_annotation.root = "cyning"
        source_annotation.modern_english_meaning = "king"
        source_annotation.save()

        mock_main_window.app_context.current_project_id = project.id

        actions = _actions(mock_main_window)
        actions.force_propagate_token_meaning(source_token)

        mock_main_window.refresh_project.assert_not_called()
        mock_main_window.messages.show_information.assert_called_once_with(
            "No matching words found"
        )


class TestAnnotationPropagationMenu:
    """Context-menu propagation item tests."""

    def test_context_menu_adds_propagation_actions_with_enable_rules(
        self, db_session, qapp, mock_main_window
    ):
        del qapp
        project = create_test_project(
            db_session, name="Menu Surface", text="Sē cyning"
        )
        token = project.sentences[0].tokens[0]
        token.annotation.pos = "D"
        token.annotation.root = "se"
        token.annotation.modern_english_meaning = "the"
        token.annotation.save()

        mock_main_window.app_context.current_project_id = project.id
        card = SentenceCard(
            project.sentences[0],
            undo_stack=QUndoStack(),
            main_window=mock_main_window,
        )
        text_edit = card.oe_text_edit
        text_edit.render_readonly_text()

        actions = []

        class _FakeAction:
            def __init__(self, text):
                self._text = text
                self.enabled = True
                self.triggered = MagicMock()

            def text(self):
                return self._text

            def setEnabled(self, value):
                self.enabled = value

        class _FakeMenu:
            def addSeparator(self):
                return None

            def addAction(self, text):
                action = _FakeAction(text)
                actions.append(action)
                return action

            def exec(self, _pos):
                return None

        with patch.object(
            text_edit,
            "createStandardContextMenu",
            return_value=_FakeMenu(),
        ):
            event = MagicMock()
            event.pos.return_value = QPoint(0, 0)
            event.globalPos.return_value = QPoint(0, 0)
            with (
                patch.object(text_edit, "find_token_at_position", return_value=0),
                patch.object(text_edit, "get_token", return_value=token),
            ):
                text_edit.contextMenuEvent(event)

        action_map = {action.text(): action for action in actions}
        assert action_map["Propagate annotation"].enabled is True
        assert action_map["Force propagate meaning"].enabled is True

    def test_context_menu_disables_force_propagate_without_required_fields(
        self, db_session, qapp, mock_main_window
    ):
        del qapp
        project = create_test_project(
            db_session, name="Menu Disable", text="Sē cyning"
        )
        token = project.sentences[0].tokens[0]
        token.annotation.pos = "D"
        token.annotation.save()

        mock_main_window.app_context.current_project_id = project.id
        card = SentenceCard(
            project.sentences[0],
            undo_stack=QUndoStack(),
            main_window=mock_main_window,
        )
        text_edit = card.oe_text_edit
        text_edit.render_readonly_text()

        actions = []

        class _FakeAction:
            def __init__(self, text):
                self._text = text
                self.enabled = True
                self.triggered = MagicMock()

            def text(self):
                return self._text

            def setEnabled(self, value):
                self.enabled = value

        class _FakeMenu:
            def addSeparator(self):
                return None

            def addAction(self, text):
                action = _FakeAction(text)
                actions.append(action)
                return action

            def exec(self, _pos):
                return None

        with patch.object(
            text_edit,
            "createStandardContextMenu",
            return_value=_FakeMenu(),
        ):
            event = MagicMock()
            event.pos.return_value = QPoint(0, 0)
            event.globalPos.return_value = QPoint(0, 0)
            with (
                patch.object(text_edit, "find_token_at_position", return_value=0),
                patch.object(text_edit, "get_token", return_value=token),
            ):
                text_edit.contextMenuEvent(event)

        action_map = {action.text(): action for action in actions}
        assert action_map["Propagate annotation"].enabled is True
        assert action_map["Force propagate meaning"].enabled is False

    def test_line_initial_token_can_be_remembered_from_context_menu(
        self, db_session, qapp, qtbot, mock_main_window
    ):
        """Right-click keeps a line-initial annotated token selected."""
        del qapp
        project = create_test_project(
            db_session, name="Line Start Menu", text="Hī willað\nHē hæfde"
        )
        for sentence in project.sentences:
            for token in sentence.tokens:
                if token.surface not in {"Hī", "Hē"}:
                    continue
                token.annotation.pos = "N"
                token.annotation.root = "word"
                token.annotation.modern_english_meaning = "word"
                token.annotation.save()

        mock_main_window.app_context.current_project_id = project.id

        class _FakeAction:
            def __init__(self, text):
                self._text = text
                self.enabled = True
                self.triggered = MagicMock()

            def text(self):
                return self._text

            def setEnabled(self, value):
                self.enabled = value

        class _FakeMenu:
            def __init__(self):
                self.actions = []

            def addSeparator(self):
                return None

            def addAction(self, text):
                action = _FakeAction(text)
                self.actions.append(action)
                return action

            def exec(self, _pos):
                return None

        for sentence in project.sentences:
            card = SentenceCard(
                sentence,
                undo_stack=QUndoStack(),
                main_window=mock_main_window,
            )
            card.show()
            qtbot.addWidget(card)
            text_edit = card.oe_text_edit
            text_edit.render_readonly_text()
            by_surface = {token.surface: token for token in text_edit.tokens}
            for surface in ("Hī", "Hē"):
                token = by_surface[surface]
                start, _end = text_edit.token_to_position[token.id]
                assert text_edit.find_token_at_position(start) == token.order_index
                if start:
                    assert (
                        text_edit.find_token_at_position(start - 1) == token.order_index
                    )

                text_edit.set_selected_token_index(token.order_index)
                press = QMouseEvent(
                    QEvent.Type.MouseButtonPress,
                    QPointF(2, 2),
                    QPointF(2, 2),
                    Qt.MouseButton.RightButton,
                    Qt.MouseButton.RightButton,
                    Qt.KeyboardModifier.NoModifier,
                )
                text_edit.mousePressEvent(press)
                assert text_edit.current_token_index() == token.order_index

                menu = _FakeMenu()
                cursor = MagicMock()
                cursor.position.return_value = start

                with (
                    patch.object(
                        text_edit, "createStandardContextMenu", return_value=menu
                    ),
                    patch.object(
                        text_edit, "cursorForPosition", return_value=cursor
                    ),
                ):
                    event = MagicMock()
                    event.pos.return_value = QPoint(0, 0)
                    event.globalPos.return_value = QPoint(0, 0)
                    text_edit.contextMenuEvent(event)

                action_map = {action.text(): action for action in menu.actions}
                assert action_map["Remember globally"].enabled is True
                assert action_map["Propagate annotation"].enabled is True
                assert text_edit.current_token_index() == token.order_index

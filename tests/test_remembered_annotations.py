"""Tests for remembered annotation behavior."""
# ruff: noqa: S101, PLR2004, S105, S106, PLR0915

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from oeapp.commands import push_command
from oeapp.models import Annotation, RememberedAnnotation
from oeapp.models.remembered_annotation import AmbiguousRememberedSpellingError
from oeapp.services.import_export import ProjectExporter, ProjectImporter
from oeapp.services.remembered_annotation_service import RememberedAnnotationService
from oeapp.state import AppContext
from oeapp.ui.dialogs.annotation_modal import AnnotationModal
from oeapp.ui.main_window import MainWindowActions, Messages
from oeapp.ui.menus import MainMenu
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox

from tests.conftest import MockMainWindow, create_test_project


def _sorted_tokens(sentence):
    """Return sentence tokens in display order."""
    return sorted(sentence.tokens, key=lambda token: token.order_index)


def test_remembered_annotation_sanitizes_copied_fields(db_session):
    """Remembered entries should keep only replay-safe token annotation fields."""
    project = create_test_project(db_session, name="Remembered Copy", text="ġiefu")
    token = _sorted_tokens(project.sentences[0])[0]
    annotation = Annotation.get_by_token(token.id)
    assert annotation is not None
    annotation.pos = "N"
    annotation.gender = "f"
    annotation.number = "s"
    annotation.case = "n"
    annotation.modern_english_meaning = "gift"
    annotation.sense = "gift in this line only"
    annotation.root = "ġiefu"
    annotation.confidence = 23
    annotation.last_inferred_json = json.dumps({"source": "llm"})
    annotation.save()

    remembered = RememberedAnnotation.upsert_from_token_annotation(
        token, project_id=None
    )

    assert remembered.token_text == "ġiefu"
    assert remembered.project_id is None
    assert remembered.pos == "N"
    assert remembered.gender == "f"
    assert remembered.number == "s"
    assert remembered.case == "n"
    assert remembered.modern_english_meaning == "gift"
    assert remembered.root == "ġiefu"
    assert remembered.root_normalized in {"æ", "giefu"}
    assert not hasattr(remembered, "sense")
    assert not hasattr(remembered, "confidence")
    assert not hasattr(remembered, "last_inferred_json")


def test_apply_remembered_annotations_exact_match_precedence_and_undo(db_session):
    """Apply should exact-match token surface, prefer project scope, and be undoable."""
    project = create_test_project(
        db_session,
        name="Remembered Apply",
        text="sæ sae sæ sæ",
    )
    tokens = _sorted_tokens(project.sentences[0])

    source_annotation = Annotation.get_by_token(tokens[0].id)
    assert source_annotation is not None
    source_annotation.pos = "N"
    source_annotation.gender = "f"
    source_annotation.modern_english_meaning = "sea"
    source_annotation.root = "sæ"
    source_annotation.save()

    RememberedAnnotation.upsert_from_token_annotation(tokens[0], project_id=None)
    source_annotation.modern_english_meaning = "project sea"
    source_annotation.root = "project-sæ"
    source_annotation.save()
    RememberedAnnotation.upsert_from_token_annotation(tokens[0], project_id=project.id)

    blocked_annotation = Annotation.get_by_token(tokens[2].id)
    assert blocked_annotation is not None
    blocked_annotation.pos = "V"
    blocked_annotation.root = "blocked"
    blocked_annotation.save()

    service = RememberedAnnotationService()
    plan = service.plan_apply(project.id)

    assert plan.applied_count == 1
    assert plan.skipped_count == 2
    assert plan.matched_count == 3
    assert plan.message == (
        "1 token updated.\n2 tokens skipped because they already had an annotation."
    )
    assert tokens[3].id in plan.affected_token_ids
    assert tokens[1].id not in plan.affected_token_ids
    assert tokens[2].id not in plan.affected_token_ids
    assert tokens[0].id not in plan.affected_token_ids

    state = AppContext(session=db_session)
    assert push_command(state.undo_stack, plan.command)

    db_session.refresh(tokens[3])
    db_session.refresh(tokens[1])
    db_session.refresh(tokens[2])
    assert tokens[3].annotation is not None
    assert tokens[3].annotation.modern_english_meaning == "project sea"
    assert tokens[3].annotation.root == "project-sæ"
    assert tokens[1].annotation is not None
    assert tokens[1].annotation.pos is None
    assert tokens[2].annotation is not None
    assert tokens[2].annotation.root == "blocked"

    state.undo_stack.undo()
    db_session.refresh(tokens[3])
    assert tokens[3].annotation is not None
    assert tokens[3].annotation.pos is None
    assert tokens[3].annotation.root is None

    state.undo_stack.redo()
    db_session.refresh(tokens[3])
    assert tokens[3].annotation is not None
    assert tokens[3].annotation.modern_english_meaning == "project sea"


@pytest.mark.parametrize(
    ("project_text", "expected_message"),
    [
        (
            "cyning cwæð",
            "0 tokens updated.\nNo remembered annotations matched this text.",
        ),
        (
            "sæ",
            (
                "0 tokens updated.\n"
                "1 token skipped because it already had an annotation."
            ),
        ),
    ],
)
def test_apply_remembered_annotations_reports_noop_states(
    db_session, project_text, expected_message
):
    """Apply should report both no-match and all-skipped no-op cases."""
    project = create_test_project(
        db_session,
        name=f"Remembered Noop {project_text}",
        text=project_text,
    )
    service = RememberedAnnotationService()

    if project_text == "sæ":
        token = _sorted_tokens(project.sentences[0])[0]
        annotation = Annotation.get_by_token(token.id)
        assert annotation is not None
        annotation.pos = "N"
        annotation.root = "occupied"
        annotation.save()
        RememberedAnnotation.upsert_from_token_annotation(token, project_id=None)

    plan = service.plan_apply(project.id)

    assert plan.applied_count == 0
    assert plan.message == expected_message
    assert plan.affected_token_ids == []


def test_project_export_import_round_trips_project_scoped_remembered_annotations(
    db_session, tmp_path
):
    """Project export/import should include only project-scoped remembered entries."""
    project = create_test_project(db_session, name="Remembered Export", text="sæ")
    token = _sorted_tokens(project.sentences[0])[0]
    annotation = Annotation.get_by_token(token.id)
    assert annotation is not None
    annotation.pos = "N"
    annotation.modern_english_meaning = "sea"
    annotation.root = "sæ"
    annotation.sense = "should never export to memory"
    annotation.save()

    RememberedAnnotation.upsert_from_token_annotation(token, project_id=None)
    RememberedAnnotation.upsert_from_token_annotation(token, project_id=project.id)

    export_path = tmp_path / "remembered_export.json"
    migration_service = MagicMock()
    migration_service.db_migration_version.return_value = "remembered-test"
    ProjectExporter(migration_service=migration_service).export_project_json(
        project.id, str(export_path)
    )

    payload = json.loads(export_path.read_text(encoding="utf-8"))
    remembered_payload = payload["project"]["remembered_annotations"]
    assert len(remembered_payload) == 1
    assert remembered_payload[0]["token_text"] == "sæ"
    assert remembered_payload[0]["modern_english_meaning"] == "sea"
    assert "sense" not in remembered_payload[0]

    importer_migration = MagicMock()
    importer_migration.code_migration_version.return_value = "remembered-test"
    imported_project, _ = ProjectImporter(
        migration_service=importer_migration
    ).import_project_json(str(export_path))
    assert len(imported_project.remembered_annotations) == 1
    remembered = imported_project.remembered_annotations[0]
    assert remembered.project_id == imported_project.id
    assert remembered.token_text == "sæ"
    assert remembered.root == "sæ"


def test_import_keeps_and_names_ambiguous_remembered_spellings(db_session, tmp_path):
    """Import keeps a colliding pair and can name both spellings."""
    project = create_test_project(db_session, name="Ambiguous Import", text="ðæt")
    RememberedAnnotation(
        token_text="ðæt",
        project_id=project.id,
        pos="R",
        modern_english_meaning="that",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="þæt",
        project_id=project.id,
        pos="D",
        modern_english_meaning="the",
        verb_transitivity="transitive",
    ).save()

    export_path = tmp_path / "ambiguous_remembered.json"
    migration_service = MagicMock()
    migration_service.db_migration_version.return_value = "remembered-test"
    ProjectExporter(migration_service=migration_service).export_project_json(
        project.id, str(export_path)
    )
    importer_migration = MagicMock()
    importer_migration.code_migration_version.return_value = "remembered-test"
    imported_project, _renamed = ProjectImporter(
        migration_service=importer_migration
    ).import_project_json(str(export_path))

    groups = RememberedAnnotation.ambiguous_groups_for_scope(imported_project.id)
    assert len(groups) == 1
    assert [entry.token_text for entry in groups[0]] == ["ðæt", "þæt"]


@pytest.mark.usefixtures("qapp")
def test_annotation_modal_remembered_mode_disables_sense_and_blanks_on_save(
    db_session,
):
    """Remembered editing should display-but-disable sense and never save it."""
    del db_session
    remembered = RememberedAnnotation(token_text="sæ")
    modal = AnnotationModal(remembered_annotation=remembered)

    assert not modal.sense_edit.isEnabled()
    assert "not stored" in modal.sense_edit.placeholderText().lower()
    modal.sense_edit.setText("should be discarded")
    modal.modern_english_edit.setText("sea")
    modal.root_edit.setText("sæ")
    modal.save()

    assert remembered.modern_english_meaning == "sea"
    assert remembered.root == "sæ"
    assert not hasattr(remembered, "sense")


@pytest.mark.usefixtures("qapp")
def test_tools_menu_includes_remembered_annotation_actions(db_session):
    """Tools menu should expose remembered annotation apply/manage actions."""
    main_window = MockMainWindow(db_session)
    menu = MainMenu(main_window)
    menu.build()

    tools_actions = [action.text() for action in menu.tools_menu.tools_menu.actions()]

    assert "Apply Remembered Annotations" in tools_actions
    assert "Global Remembered Annotations..." in tools_actions
    assert "Project Remembered Annotations..." in tools_actions


def test_apply_matches_partial_spelling_and_keeps_length_marks(db_session):
    """Apply fills case variants and leaves a different length mark alone."""
    project = create_test_project(
        db_session, name="Partial Apply", text="Hē hæfde hē he gōd god."
    )
    tokens = _sorted_tokens(project.sentences[0])
    he_capital, he_lower, he_short, good, god = (
        tokens[0],
        tokens[2],
        tokens[3],
        tokens[4],
        tokens[5],
    )

    he_annotation = Annotation.get_by_token(he_capital.id)
    assert he_annotation is not None
    he_annotation.pos = "R"
    he_annotation.modern_english_meaning = "he"
    he_annotation.root = "hē"
    he_annotation.save()
    RememberedAnnotation.upsert_from_token_annotation(he_capital, project_id=None)

    good_annotation = Annotation.get_by_token(good.id)
    assert good_annotation is not None
    good_annotation.pos = "A"
    good_annotation.modern_english_meaning = "good"
    good_annotation.root = "gōd"
    good_annotation.save()
    RememberedAnnotation.upsert_from_token_annotation(good, project_id=None)

    plan = RememberedAnnotationService().plan_apply(project.id)

    assert plan.applied_count == 1
    assert plan.affected_token_ids == [he_lower.id]
    assert he_short.id not in plan.affected_token_ids
    assert god.id not in plan.affected_token_ids
    assert plan.command.after[he_lower.id]["modern_english_meaning"] == "he"


def test_apply_folds_eth_dots_and_hyphens(db_session):
    """Apply treats eth, consonant dots, and hyphens as the same spelling."""
    project = create_test_project(
        db_session, name="Fold Apply", text="ðæt ġe-wāt þæt gewāt."
    )
    tokens = _sorted_tokens(project.sentences[0])
    eth, hyphenated, thorn, plain = tokens

    eth_annotation = Annotation.get_by_token(eth.id)
    assert eth_annotation is not None
    eth_annotation.pos = "R"
    eth_annotation.modern_english_meaning = "that"
    eth_annotation.root = "se"
    eth_annotation.save()
    RememberedAnnotation.upsert_from_token_annotation(eth, project_id=None)

    hyphen_annotation = Annotation.get_by_token(hyphenated.id)
    assert hyphen_annotation is not None
    hyphen_annotation.pos = "V"
    hyphen_annotation.modern_english_meaning = "went"
    hyphen_annotation.root = "gewāt"
    hyphen_annotation.save()
    RememberedAnnotation.upsert_from_token_annotation(hyphenated, project_id=None)

    plan = RememberedAnnotationService().plan_apply(project.id)

    assert set(plan.affected_token_ids) == {thorn.id, plain.id}
    assert plan.command.after[thorn.id]["modern_english_meaning"] == "that"
    assert plan.command.after[plain.id]["modern_english_meaning"] == "went"


def test_apply_reports_ambiguous_partial_spellings(db_session):
    """Two saved casings of one spelling are listed and applied to nobody."""
    project = create_test_project(db_session, name="Ambiguous Apply", text="ðæt þæt.")
    RememberedAnnotation(
        token_text="ðæt",
        project_id=None,
        pos="R",
        modern_english_meaning="that",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="þæt",
        project_id=None,
        pos="D",
        modern_english_meaning="the",
        verb_transitivity="transitive",
    ).save()

    plan = RememberedAnnotationService().plan_apply(project.id)

    assert plan.applied_count == 0
    assert plan.affected_token_ids == []
    assert "ðæt / þæt (global)" in plan.message
    assert "Ambiguous remembered annotations were not applied:" in plan.message


def test_remember_keeps_saved_spelling_when_partial_match_exists(db_session):
    """Remembering a case variant updates the saved entry and keeps its label."""
    project = create_test_project(db_session, name="Keep Spelling", text="Hē hē")
    capital, lower = _sorted_tokens(project.sentences[0])
    capital_annotation = Annotation.get_by_token(capital.id)
    assert capital_annotation is not None
    capital_annotation.pos = "R"
    capital_annotation.modern_english_meaning = "he"
    capital_annotation.root = "hē"
    capital_annotation.save()
    RememberedAnnotation.upsert_from_token_annotation(capital, project_id=None)

    lower_annotation = Annotation.get_by_token(lower.id)
    assert lower_annotation is not None
    lower_annotation.pos = "R"
    lower_annotation.modern_english_meaning = "he himself"
    lower_annotation.root = "hē"
    lower_annotation.save()
    remembered = RememberedAnnotation.upsert_from_token_annotation(
        lower, project_id=None
    )

    assert remembered.token_text == "Hē"
    assert remembered.modern_english_meaning == "he himself"
    assert len(RememberedAnnotation.list_for_scope(None)) == 1


def test_remember_refuses_when_partial_spelling_is_ambiguous(db_session):
    """Remember names both saved spellings instead of choosing one."""
    project = create_test_project(db_session, name="Refuse Ambiguous", text="ðæt")
    token = _sorted_tokens(project.sentences[0])[0]
    annotation = Annotation.get_by_token(token.id)
    assert annotation is not None
    annotation.pos = "R"
    annotation.modern_english_meaning = "that"
    annotation.root = "se"
    annotation.save()
    RememberedAnnotation(
        token_text="ðæt", project_id=None, verb_transitivity="transitive"
    ).save()
    RememberedAnnotation(
        token_text="þæt", project_id=None, verb_transitivity="transitive"
    ).save()

    with pytest.raises(AmbiguousRememberedSpellingError, match="ðæt / þæt"):
        RememberedAnnotation.upsert_from_token_annotation(token, project_id=None)


def test_editor_can_correct_one_row_of_an_ambiguous_pair(db_session):
    """Saving an open row still works, and a new spelling of the pair does not."""
    del db_session
    RememberedAnnotation(
        token_text="ðæt",
        project_id=None,
        pos="R",
        modern_english_meaning="that",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="þæt",
        project_id=None,
        pos="D",
        modern_english_meaning="the",
        verb_transitivity="transitive",
    ).save()
    row = RememberedAnnotation.get_for_scope("ðæt", None)
    assert row is not None
    payload = row.annotation_payload()
    payload["modern_english_meaning"] = "that one"
    saved = RememberedAnnotation.upsert_fields("ðæt", None, payload)

    assert saved.token_text == "ðæt"
    assert saved.modern_english_meaning == "that one"
    with pytest.raises(AmbiguousRememberedSpellingError, match="ðæt / þæt"):
        RememberedAnnotation.upsert_fields("Ðæt", None, payload)


def test_apply_lets_a_clean_project_entry_hide_a_global_conflict(db_session):
    """A single project entry wins, and an ambiguous global pair is only listed."""
    project = create_test_project(db_session, name="Scope Wins", text="ðæt hē")
    eth, he = _sorted_tokens(project.sentences[0])
    RememberedAnnotation(
        token_text="ðæt",
        project_id=None,
        pos="R",
        modern_english_meaning="global that",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="þæt",
        project_id=None,
        pos="D",
        modern_english_meaning="global the",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="hē",
        project_id=None,
        pos="R",
        modern_english_meaning="global he",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="Hē",
        project_id=project.id,
        pos="R",
        modern_english_meaning="project he",
        verb_transitivity="transitive",
    ).save()

    plan = RememberedAnnotationService().plan_apply(project.id)

    assert plan.affected_token_ids == [he.id]
    assert plan.command.after[he.id]["modern_english_meaning"] == "project he"
    assert eth.id not in plan.affected_token_ids
    assert "ðæt / þæt (global)" in plan.message


def test_apply_blocks_global_when_the_project_group_is_ambiguous(db_session):
    """An ambiguous project group hides the global entry and is not applied."""
    project = create_test_project(db_session, name="Project Ambiguous", text="ðæt")
    RememberedAnnotation(
        token_text="ðæt",
        project_id=None,
        pos="R",
        modern_english_meaning="global",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="ðæt",
        project_id=project.id,
        pos="R",
        modern_english_meaning="project a",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="þæt",
        project_id=project.id,
        pos="D",
        modern_english_meaning="project b",
        verb_transitivity="transitive",
    ).save()

    plan = RememberedAnnotationService().plan_apply(project.id)

    assert plan.applied_count == 0
    assert plan.affected_token_ids == []
    assert "ðæt / þæt (project)" in plan.message
    assert "(global)" not in plan.message


def _run_apply_dialog(qtbot, db_session, project_id: int):
    """Open Apply and dismiss the real summary dialog."""
    window = MockMainWindow(db_session)
    qtbot.addWidget(window)
    window.show()
    window.app_context.current_project_id = project_id
    window.messages = Messages(window)
    actions = MainWindowActions(window, window.app_context)
    captured: dict[str, str] = {}
    original = window.messages.show_information

    def show_information(message: str, title: str = "Information") -> None:
        captured["title"] = title
        original(message, title)

    window.messages.show_information = show_information

    def dismiss_dialog() -> None:
        dialog = QApplication.activeModalWidget()
        if not isinstance(dialog, QMessageBox):
            QTimer.singleShot(0, dismiss_dialog)
            return
        captured["text"] = dialog.text()
        captured["labels"] = " | ".join(
            child.text() for child in dialog.findChildren(QLabel) if child.text()
        )
        ok_button = dialog.button(QMessageBox.StandardButton.Ok)
        if ok_button is None:
            dialog.accept()
            return
        qtbot.mouseClick(ok_button, Qt.MouseButton.LeftButton)

    QTimer.singleShot(0, dismiss_dialog)
    actions.apply_remembered_annotations()
    return window, captured


@pytest.mark.usefixtures("qapp")
def test_apply_remembered_annotations_opens_summary_dialog(db_session, qtbot):
    """Apply opens the summary dialog and waits until it is dismissed."""
    project = create_test_project(db_session, name="Apply Dialog", text="Hē hē")
    capital, lower = _sorted_tokens(project.sentences[0])
    annotation = Annotation.get_by_token(capital.id)
    assert annotation is not None
    annotation.pos = "R"
    annotation.modern_english_meaning = "he"
    annotation.root = "hē"
    annotation.save()
    RememberedAnnotation.upsert_from_token_annotation(capital, project_id=None)

    expected = (
        "1 token updated.\n"
        "1 token skipped because it already had an annotation."
    )
    window, captured = _run_apply_dialog(qtbot, db_session, project.id)

    assert captured["title"] == "Apply Remembered Annotations"
    assert captured["text"] == expected
    assert captured["labels"] == expected
    window.refresh_project.assert_called_once()
    db_session.refresh(lower)
    assert lower.annotation.modern_english_meaning == "he"


@pytest.mark.usefixtures("qapp")
def test_apply_remembered_annotations_opens_no_match_dialog(db_session, qtbot):
    """Apply opens a dialog when no remembered spelling matches."""
    project = create_test_project(db_session, name="Apply None", text="cyning")
    expected = "0 tokens updated.\nNo remembered annotations matched this text."

    window, captured = _run_apply_dialog(qtbot, db_session, project.id)

    assert captured["title"] == "Apply Remembered Annotations"
    assert captured["text"] == expected
    assert captured["labels"] == expected
    window.refresh_project.assert_not_called()


@pytest.mark.usefixtures("qapp")
def test_apply_remembered_annotations_opens_ambiguous_dialog(db_session, qtbot):
    """Apply opens a dialog that names a conflicting pair."""
    project = create_test_project(db_session, name="Apply Conflict", text="ðæt")
    RememberedAnnotation(
        token_text="ðæt",
        project_id=None,
        pos="R",
        modern_english_meaning="that",
        verb_transitivity="transitive",
    ).save()
    RememberedAnnotation(
        token_text="þæt",
        project_id=None,
        pos="D",
        modern_english_meaning="the",
        verb_transitivity="transitive",
    ).save()
    expected = (
        "0 tokens updated.\n"
        "\n"
        "Ambiguous remembered annotations were not applied:\n"
        "- ðæt / þæt (global)"
    )

    window, captured = _run_apply_dialog(qtbot, db_session, project.id)

    assert captured["title"] == "Apply Remembered Annotations"
    assert captured["text"] == expected
    assert captured["labels"] == expected
    window.refresh_project.assert_not_called()

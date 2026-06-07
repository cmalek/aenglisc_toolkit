"""Tests for remembered annotation behavior."""
# ruff: noqa: S101, PLR2004, S105, S106, PLR0915

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from oeapp.models import Annotation, RememberedAnnotation
from oeapp.services.import_export import ProjectExporter, ProjectImporter
from oeapp.services.remembered_annotation_service import RememberedAnnotationService
from oeapp.state import AppContext
from oeapp.ui.dialogs.annotation_modal import AnnotationModal
from oeapp.ui.menus import MainMenu

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
    assert plan.message == "1 applied, 2 skipped"
    assert tokens[3].id in plan.affected_token_ids
    assert tokens[1].id not in plan.affected_token_ids
    assert tokens[2].id not in plan.affected_token_ids
    assert tokens[0].id not in plan.affected_token_ids

    state = AppContext(session=db_session)
    assert state.command_manager.execute(plan.command)

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

    assert state.command_manager.undo()
    db_session.refresh(tokens[3])
    assert tokens[3].annotation is not None
    assert tokens[3].annotation.pos is None
    assert tokens[3].annotation.root is None

    assert state.command_manager.redo()
    db_session.refresh(tokens[3])
    assert tokens[3].annotation is not None
    assert tokens[3].annotation.modern_english_meaning == "project sea"


@pytest.mark.parametrize(
    ("project_text", "expected_message"),
    [
        ("cyning cwæð", "0 applied: no remembered annotations matched this text"),
        ("sæ", "0 applied: all matched tokens already had annotations"),
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


@pytest.mark.usefixtures("qapp")
def test_annotation_modal_remembered_mode_disables_sense_and_blanks_on_save(
    db_session
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

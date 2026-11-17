"""Pool tasks use a session that is not the UI session."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QWidget

from sqlalchemy.orm import Session

from oeapp.db import get_runtime_session, push_ui_db_busy, pop_ui_db_busy, ui_db_busy
from oeapp.models.project import Project
from oeapp.services.autosave import AutosaveService
from oeapp.ui.session_task import run_session_task

from tests.conftest import create_test_project


def test_run_session_task_uses_another_session(qtbot, db_session) -> None:
    """The worker sees a different session on the same database."""
    project = create_test_project(db_session, name="Before")
    gui = get_runtime_session()
    seen: dict[str, int] = {}
    parent = QWidget()
    qtbot.addWidget(parent)

    def work() -> int:
        session = get_runtime_session()
        seen["same"] = int(session is gui)
        row = Project.get(project.id, session=session)
        assert row is not None
        row.name = "After"
        return int(row.id)

    assert run_session_task(parent, "Working…", work) == project.id
    assert seen["same"] == 0
    db_session.expire_all()
    refreshed = Project.get(project.id, session=db_session)
    assert refreshed is not None
    assert refreshed.name == "After"


def test_run_session_task_keeps_unsaved_edits(qtbot, db_session) -> None:
    """A pool task does not write edits the UI session has not saved."""
    project = create_test_project(db_session, name="Before")
    project.notes = "unsaved"
    parent = QWidget()
    qtbot.addWidget(parent)

    def work() -> int:
        session = get_runtime_session()
        row = Project.get(project.id, session=session)
        assert row is not None
        row.name = "After"
        return int(row.id)

    assert run_session_task(parent, "Working…", work) == project.id
    assert project.notes == "unsaved"
    check = Session(bind=db_session.get_bind())
    try:
        stored = Project.get(project.id, session=check)
        assert stored is not None
        assert stored.name == "After"
        assert stored.notes != "unsaved"
    finally:
        check.close()
    assert ui_db_busy() is False


@pytest.mark.enable_autosave
def test_autosave_waits_while_a_database_task_is_busy(qapp) -> None:
    """Autosave does not touch the database during a pool task."""
    calls: list[str] = []
    service = AutosaveService(lambda: calls.append("saved"), debounce_ms=60_000)
    service._pending = True
    push_ui_db_busy()
    try:
        service._save()
        assert calls == []
        assert service._pending is True
    finally:
        pop_ui_db_busy()
        if service._timer is not None:
            service._timer.stop()
    service._save()
    assert calls == ["saved"]


def test_run_session_task_reraises(qtbot) -> None:
    """An exception on the worker is raised on the UI thread."""
    parent = QWidget()
    qtbot.addWidget(parent)

    def work() -> None:
        msg = "nope"
        raise ValueError(msg)

    try:
        run_session_task(parent, "Working…", work)
    except ValueError as exc:
        assert str(exc) == "nope"
    else:  # pragma: no cover - the assertion above is the test
        raise AssertionError("worker exception was swallowed")

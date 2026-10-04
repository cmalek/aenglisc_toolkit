"""An unknown database revision stops migration before any backup or upgrade."""

import json
from unittest.mock import patch

import pytest

from oeapp.exc import UnknownDatabaseRevision
from tests.test_migration_flow import flow  # noqa: F401  (shared fixture)

UNKNOWN = "zzzzzzzzzzzz"


def _write_sidecar(backup_dir, name, revision, app_version):
    (backup_dir / f"live_{name}.db").touch()
    (backup_dir / f"live_{name}.json").write_text(
        json.dumps(
            {
                "backup_timestamp": "2026-01-01T00:00:00+00:00",
                "migration_version": revision,
                "application_version": app_version,
                "projects": [],
            }
        )
    )


def _set_revision(service, revision):
    with service.engine.begin() as conn:
        conn.exec_driver_sql(f"update alembic_version set version_num='{revision}'")


def test_known_and_unknown_revisions(flow):
    assert flow.is_known_revision(flow.code_migration_version()) is True
    assert flow.is_known_revision(UNKNOWN) is False


def test_migrate_raises_before_any_backup_or_upgrade(flow):
    _set_revision(flow, UNKNOWN)

    with (
        patch.object(flow, "apply_migrations") as apply,
        pytest.raises(UnknownDatabaseRevision) as raised,
    ):
        flow.migrate()

    assert raised.value.revision == UNKNOWN
    apply.assert_not_called()
    assert list(flow.backup_service.backup_dir.glob("*.db")) == []


def test_known_older_revision_is_not_unknown(flow):
    flow.ensure_known_revision()  # OLD_REV is real; must not raise


def test_resolution_prefers_the_catalog(flow):
    _set_revision(flow, UNKNOWN)
    flow.migration_metadata_service.versions = {UNKNOWN: "9.9.9"}
    _write_sidecar(flow.backup_service.backup_dir, "a", UNKNOWN, "1.2.0")

    with pytest.raises(UnknownDatabaseRevision) as raised:
        flow.ensure_known_revision()

    assert raised.value.required_app_version == "9.9.9"


def test_resolution_uses_the_minimum_matching_sidecar_version(flow):
    _set_revision(flow, UNKNOWN)
    backup_dir = flow.backup_service.backup_dir
    # As strings "1.10.0" < "1.9.0"; as versions 1.9.0 is the smaller.
    _write_sidecar(backup_dir, "a", UNKNOWN, "1.10.0")
    _write_sidecar(backup_dir, "b", UNKNOWN, "1.9.0")
    _write_sidecar(backup_dir, "c", "otherrevision", "0.0.1")
    _write_sidecar(backup_dir, "d", UNKNOWN, None)

    with pytest.raises(UnknownDatabaseRevision) as raised:
        flow.ensure_known_revision()

    assert raised.value.required_app_version == "1.9.0"


def test_resolution_ignores_unparseable_versions(flow):
    _set_revision(flow, UNKNOWN)
    _write_sidecar(flow.backup_service.backup_dir, "a", UNKNOWN, "not-a-version")

    with pytest.raises(UnknownDatabaseRevision) as raised:
        flow.ensure_known_revision()

    assert raised.value.required_app_version is None


def test_unresolved_when_nothing_matches(flow):
    _set_revision(flow, UNKNOWN)
    with pytest.raises(UnknownDatabaseRevision) as raised:
        flow.ensure_known_revision()
    assert raised.value.required_app_version is None


def test_a_non_object_sidecar_does_not_crash_resolution(flow):
    _set_revision(flow, UNKNOWN)
    (flow.backup_service.backup_dir / "live_a.db").touch()
    (flow.backup_service.backup_dir / "live_a.json").write_text("[1, 2]")

    with pytest.raises(UnknownDatabaseRevision) as raised:
        flow.ensure_known_revision()

    assert raised.value.required_app_version is None


def test_a_numeric_application_version_is_ignored(flow):
    _set_revision(flow, UNKNOWN)
    _write_sidecar(flow.backup_service.backup_dir, "a", UNKNOWN, 5)

    with pytest.raises(UnknownDatabaseRevision) as raised:
        flow.ensure_known_revision()

    assert raised.value.required_app_version is None

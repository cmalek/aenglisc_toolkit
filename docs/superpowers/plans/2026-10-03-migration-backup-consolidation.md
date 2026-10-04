# Migration and Backup Consolidation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `BackupService` the single backup collaborator for migrations, make migration state come from Alembic alone, and stop startup and Restore from running on a database this build cannot understand.

**Architecture:** `BackupService` gains unique filenames, a WAL-safe `sqlite3.backup()` snapshot, a `prune` switch, and sidecars that record the build that maintained the database. `MigrationService.migrate()` shrinks to: refuse unknown revisions, skip when not pending, back up (pre), upgrade on the injected engine with foreign keys OFF, back up (post), or roll back from the pre-migration backup. Unknown revisions and unrestorable backups stop with a dialog. Skip/abort and the `.pre-migration` code are deleted.

**Tech Stack:** Python 3.14, SQLAlchemy 2, Alembic, PySide6, pytest + pytest-qt, `packaging` (to be declared), Sphinx (RST), Qt Help (markdown to `.qch`).

**Spec:** `doc/source/architecture/adr_0007_migration_backup_consolidation.rst` (ADR 0007, decisions D1–D10, D2a, D2b, D6a, D6b); glossary terms **Pre-migration Backup**, **Pending Migration**, **Fresh Database**, **Unknown Database Revision** in `CONTEXT.md`. Origin: Trello card F6.

## Global Constraints

- Use `.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`. Use `/usr/bin/cd` to change directories; never bare `cd`.
- Add packages with `uv add <package>` (core). `packaging` is installed (26.3) but not declared; Task 8 declares it.
- Data models in `oeapp.models`, business logic in `oeapp.services`, UI wiring in `oeapp.ui`, dialogs in `oeapp.ui.dialogs`. Any SQLAlchemy model change needs an Alembic migration (this plan changes no model).
- Methods and function bodies are 60 lines or fewer. Prefer cohesive classes with constructor injection.
- Docs contract for non-test Python: class docstrings state the contract and list constructor `Args:`; function docstrings have a brief description plus only the applicable `Args:`, `Keyword Args:`, `Raises:`, `Returns:`, `Side Effects:` sections; Napoleon `#:` comments on class attributes, `__init__` instance attributes and module globals.
- After Python edits: `.venv/bin/ruff check <files>`, `.venv/bin/mypy <files>`, `make napoleon-gate` (known to always fail because its baseline is keyed by line number; report separately, do not chase it), then `graphify update .`.
- ADRs are RST in `doc/source/architecture/`; do not touch `docs/adr/`.
- Commit messages end with `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Implement the real change. No monkey-patching or startup hooks to dodge gate noise.
- Use SQLite stdlib `sqlite3.Connection.backup()` for snapshots and restores. No new runtime dependency except `packaging`.

## Review Focus

Failure modes the ADR implies that are most likely to bite a user, each pinned by a test in the named task:

1. A migration that fails within the same second as its backup must restore the original data, not the broken file (Task 3 filename uniqueness; Task 7 rollback test with a frozen clock).
2. `num_backups=1` must never evict the backup being used: migrate success, migrate rollback, and the Restore dialog (Tasks 4, 7, 9).
3. Batch table recreation under the app engine (`foreign_keys=ON`) must not delete child rows (Task 5 row-count test on the 1.0.0 baseline).
4. An unknown database revision with no catalog entry and no matching backup shows "Can't determine app version to use with db revision <revision>", changes nothing on disk, and exits (Tasks 8 and 10).
5. Restoring a backup whose `migration_version` is `None` is allowed; one whose revision is unknown is refused before the live database is touched (Task 9).
6. Catalog note, not a test: `oeapp/etc/migration_versions.json` maps `f38623b35077` to `0.1.0`, but tags show `1.0.0` was the first release containing it. "Install 0.1.0 or later" is true but unhelpful. Confirm with the maintainer whether to correct it; this plan does not change the value.

---

## File Structure

| File | Responsibility |
|---|---|
| `oeapp/db.py` | Add `read_alembic_revision(engine)`, the single reader for `alembic_version`. |
| `oeapp/services/backup.py` | Unique filenames, snapshot, `prune`, `maintained_by`, sidecar fields, WAL-safe restore, sidecar queries, `LAST_APP_VERSION_KEY`. |
| `oeapp/services/revision_version.py` (new) | `RevisionVersionResolver`: which app version a database revision needs (catalog, then sidecars). |
| `oeapp/services/migration.py` | `MigrationService`: injected-engine upgrade, new `migrate()`, unknown-revision check. Delete skip/abort, `.pre-migration` code, `BackupFileMetadataService`, `restore()`. |
| `oeapp/models/alembic/env.py` | Accept an injected connection, fall back to the env path. |
| `oeapp/exc.py` | Add `UnknownDatabaseRevision`; delete `MigrationSkipped`. |
| `oeapp/ui/dialogs/unknown_revision.py` (new) | `UnknownRevisionDialog` and `describe_unknown_revision`. |
| `oeapp/ui/dialogs/restore.py` | Refuse unknown-revision backups; exit after a successful restore. |
| `oeapp/ui/main_window.py` | Handle `UnknownDatabaseRevision`; drop skip/abort; use `LAST_APP_VERSION_KEY`. |
| `oeapp/ui/dialogs/__init__.py` | Export `UnknownRevisionDialog`. |
| `doc/source/overview/faq.rst`, `oeapp/help/topics/troubleshooting.md` | User-facing "Database version mismatch" help. |
| `tests/fixtures/schema_1_0_0.sql` (new), `tests/migration_baseline.py` (new) | Committed 1.0.0 release-baseline schema and shared helpers. |
| `tests/test_migration_baseline.py`, `tests/test_migration_engine.py`, `tests/test_migration_flow.py`, `tests/test_unknown_revision.py`, `tests/test_unknown_revision_dialog.py`, `tests/test_main_window_migrations.py` (new); `tests/test_backup.py`, `tests/test_db.py`, `tests/test_restore_dialog.py`, `tests/test_exc.py`, `tests/test_migration_backup_restore.py` (modified) | Tests. |

---

### Task 0: Branch and baseline

**Files:** none changed.

- [ ] **Step 1: Create the working branch**

Run: `git switch -c f6-migration-backup-consolidation`
Expected: `Switched to a new branch 'f6-migration-backup-consolidation'`

- [ ] **Step 2: Record the baseline test run**

Run: `.venv/bin/pytest -q -x -p no:cacheprovider 2>&1 | tail -5`
Expected: all tests pass (the suite baseline is 0 failures). Write down the exact pass count; Task 12 compares against it. If anything fails, stop and report it as pre-existing before changing code.

- [ ] **Step 3: Record the lint and type baseline**

Run: `.venv/bin/ruff check oeapp tests | tail -3; .venv/bin/mypy oeapp 2>&1 | tail -2`
Expected: note the counts. Later "no new errors" is measured against these.

---

### Task 1: 1.0.0 baseline fixture and schema-drift test (D7)

The Alembic chain cannot be replayed from an empty database, so the oldest real starting point is a database as release `1.0.0` created it. This task commits that schema and proves it upgrades to head with no drift from `Base.metadata.create_all`.

**Files:**
- Create: `tests/fixtures/schema_1_0_0.sql`
- Create: `tests/migration_baseline.py`
- Test: `tests/test_migration_baseline.py`

**Interfaces:**
- Produces (used by Tasks 5 and 7): in `tests/migration_baseline.py`: `BASELINE_REVISION: str = "f38623b35077"`, `SEED_COUNTS: dict[str, int]`, `build_baseline_db(path: Path) -> None` (schema plus seed rows), `build_create_all_db(path: Path) -> None`, `schema_snapshot(path: Path) -> dict[str, object]`.

- [ ] **Step 1: Generate the fixture from the 1.0.0 tag**

Run (verified procedure; the worktree is temporary):

```bash
S=/private/tmp/claude-501/-Users-cmalek-src-workspace-aenglisc-toolkit/334627fe-28d2-4ad6-bf07-e0c4f14c054a/scratchpad
git worktree add -f $S/wt100 1.0.0
mkdir -p tests/fixtures
rm -f $S/v100.db*
AENGLISC_TOOLKIT_DB_PATH=$S/v100.db AENGLISC_TOOLKIT_DATA_PATH=$S/data100 .venv/bin/python - <<E
import sys, os, sqlite3
W = "$S/wt100"; sys.path.insert(0, W); os.chdir(W)
import oeapp; assert oeapp.__file__.startswith(W), oeapp.__file__
import oeapp.models
from oeapp.db import Base
from sqlalchemy import create_engine
eng = create_engine("sqlite:///$S/v100.db"); Base.metadata.create_all(eng); eng.dispose()
con = sqlite3.connect("$S/v100.db")
con.execute("create table if not exists alembic_version (version_num varchar(32) not null primary key)")
con.execute("delete from alembic_version"); con.execute("insert into alembic_version values ('f38623b35077')"); con.commit()
dump = [l for l in con.iterdump() if not l.startswith(("BEGIN", "COMMIT"))]
open("/Users/cmalek/src/workspace/aenglisc_toolkit/tests/fixtures/schema_1_0_0.sql", "w").write("\n".join(dump) + "\n")
print(len(dump), "statements")
E
git worktree remove --force $S/wt100; git worktree prune
```

Expected: `24 statements` (the exact count may differ by one or two if the tag's models differ; it must contain 12 `CREATE TABLE` statements including `alembic_version`, and one `INSERT INTO alembic_version VALUES('f38623b35077')`). Verify: `grep -c "CREATE TABLE" tests/fixtures/schema_1_0_0.sql` prints `12`.

- [ ] **Step 2: Write the shared helpers**

Create `tests/migration_baseline.py`:

```python
"""Helpers for the committed 1.0.0 release-baseline database (ADR 0007 D7)."""

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine

from oeapp.db import Base

#: Schema of a database as release 1.0.0 created it, stamped ``BASELINE_REVISION``.
BASELINE_SQL = Path(__file__).parent / "fixtures" / "schema_1_0_0.sql"
#: Alembic revision the baseline schema is stamped with.
BASELINE_REVISION = "f38623b35077"
#: Row counts produced by ``_SEED``.
SEED_COUNTS = {"projects": 1, "sentences": 1, "tokens": 1, "annotations": 1}

_SEED = """
insert into projects (id, name, created_at, updated_at)
  values (1, 'Beowulf', '2026-01-01', '2026-01-01');
insert into sentences (id, project_id, display_order, text_oe, created_at, updated_at)
  values (1, 1, 1, 'Hwæt we Gardena', '2026-01-01', '2026-01-01');
insert into tokens (id, sentence_id, order_index, surface, surface_normalized,
                    created_at, updated_at)
  values (1, 1, 0, 'Gardena', 'gardena', '2026-01-01', '2026-01-01');
insert into annotations (id, token_id, pos, declension, updated_at,
                         verb_requires_infinitive, verb_impersonal, verb_transitivity)
  values (1, 1, 'N', 's', '2026-01-01', 0, 0, 'transitive');
"""


def build_baseline_db(path: Path) -> None:
    """Create a 1.0.0-schema database at ``path`` with the seed rows."""
    connection = sqlite3.connect(path)
    try:
        connection.executescript(BASELINE_SQL.read_text(encoding="utf-8"))
        connection.executescript(_SEED)
        connection.commit()
    finally:
        connection.close()


def build_create_all_db(path: Path) -> None:
    """Create a database at ``path`` straight from the current models."""
    import oeapp.models  # noqa: F401, PLC0415  (registers every table)

    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    engine.dispose()


def schema_snapshot(path: Path) -> dict[str, object]:
    """Return table columns and index SQL for ``path``, ignoring ``alembic_version``."""
    connection = sqlite3.connect(path)
    try:
        tables = [
            name
            for (name,) in connection.execute(
                "select name from sqlite_master where type='table' "
                "and name not like 'sqlite_%' and name != 'alembic_version' "
                "order by name"
            )
        ]
        columns = {
            table: [
                (c[1], c[2].upper().split("(")[0], c[3], c[5])
                for c in connection.execute(f"pragma table_info({table})")
            ]
            for table in tables
        }
        indexes = {
            name: " ".join((sql or "").split())
            for name, sql in connection.execute(
                "select name, sql from sqlite_master "
                "where type='index' and sql is not null order by name"
            )
        }
    finally:
        connection.close()
    return {"columns": columns, "indexes": indexes}
```

- [ ] **Step 3: Write the tests**

Create `tests/test_migration_baseline.py`:

```python
"""The 1.0.0 baseline must upgrade to the same schema ``create_all`` builds."""

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from oeapp.services.migration import MigrationService
from tests.migration_baseline import (
    SEED_COUNTS,
    build_baseline_db,
    build_create_all_db,
    schema_snapshot,
)


def _config() -> Config:
    return Config(str(MigrationService.ALEMBIC_INI_PATH))


def _upgrade(db_path: Path, monkeypatch) -> None:
    # env.py falls back to AENGLISC_TOOLKIT_DB_PATH when no connection is injected
    monkeypatch.setenv("AENGLISC_TOOLKIT_DB_PATH", str(db_path))
    command.upgrade(_config(), "head")


def test_baseline_upgrades_to_the_create_all_schema(tmp_path, monkeypatch):
    upgraded, fresh = tmp_path / "upgraded.db", tmp_path / "fresh.db"
    build_baseline_db(upgraded)
    build_create_all_db(fresh)

    _upgrade(upgraded, monkeypatch)

    assert schema_snapshot(upgraded) == schema_snapshot(fresh)


def test_baseline_upgrade_keeps_rows_and_stamps_head(tmp_path, monkeypatch):
    db_path = tmp_path / "upgraded.db"
    build_baseline_db(db_path)

    _upgrade(db_path, monkeypatch)

    connection = sqlite3.connect(db_path)
    try:
        counts = {
            table: connection.execute(f"select count(*) from {table}").fetchone()[0]
            for table in SEED_COUNTS
        }
        revision = connection.execute("select version_num from alembic_version").fetchone()[0]
    finally:
        connection.close()
    assert counts == SEED_COUNTS
    assert revision == ScriptDirectory.from_config(_config()).get_current_head()


def test_schema_snapshot_detects_drift(tmp_path):
    first, second = tmp_path / "a.db", tmp_path / "b.db"
    for path, extra in ((first, ""), (second, ", extra text")):
        connection = sqlite3.connect(path)
        connection.execute(f"create table t (id integer{extra})")
        connection.commit()
        connection.close()

    assert schema_snapshot(first) != schema_snapshot(second)
```

- [ ] **Step 4: Run the tests**

Run: `.venv/bin/pytest tests/test_migration_baseline.py -v`
Expected: 3 PASS. These are characterization tests: they pass immediately and pin current behaviour. The third proves the comparison can fail.

- [ ] **Step 5: Mutation check**

In `tests/test_migration_baseline.py` temporarily make `_upgrade` return immediately (skip the upgrade) and run `.venv/bin/pytest tests/test_migration_baseline.py -q`.
Expected: `test_baseline_upgrades_to_the_create_all_schema` and `test_baseline_upgrade_keeps_rows_and_stamps_head` FAIL (the baseline is not at head). Restore `_upgrade` and re-run: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures/schema_1_0_0.sql tests/migration_baseline.py tests/test_migration_baseline.py
git commit -m "test: pin the 1.0.0 baseline upgrade to head with no schema drift" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Single `alembic_version` reader (D10)

**Files:**
- Modify: `oeapp/db.py` (imports at top; new function after `create_engine_with_path`)
- Modify: `oeapp/services/migration.py` (`db_migration_version`)
- Modify: `oeapp/services/backup.py` (`get_current_migration_version`)
- Test: `tests/test_db.py`

**Interfaces:**
- Produces: `read_alembic_revision(engine: Engine) -> str | None` in `oeapp/db.py`. Used by Tasks 5, 7, 8.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_db.py` (add `from sqlalchemy import create_engine` and `from oeapp.db import read_alembic_revision` to its imports if absent):

```python
class TestReadAlembicRevision:
    """Tests for read_alembic_revision()."""

    def test_returns_none_without_the_table(self, tmp_path):
        engine = create_engine(f"sqlite:///{tmp_path / 'a.db'}")
        assert read_alembic_revision(engine) is None

    def test_returns_the_stored_revision(self, tmp_path):
        engine = create_engine(f"sqlite:///{tmp_path / 'b.db'}")
        with engine.begin() as conn:
            conn.exec_driver_sql("create table alembic_version (version_num varchar(32) primary key)")
            conn.exec_driver_sql("insert into alembic_version values ('abc123')")
        assert read_alembic_revision(engine) == "abc123"

    def test_returns_none_when_the_table_is_empty(self, tmp_path):
        engine = create_engine(f"sqlite:///{tmp_path / 'c.db'}")
        with engine.begin() as conn:
            conn.exec_driver_sql("create table alembic_version (version_num varchar(32) primary key)")
        assert read_alembic_revision(engine) is None
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_db.py::TestReadAlembicRevision -v`
Expected: FAIL with `ImportError: cannot import name 'read_alembic_revision'`

- [ ] **Step 3: Implement**

In `oeapp/db.py` change `from sqlalchemy import Engine, create_engine, event` to `from sqlalchemy import Engine, create_engine, event, inspect, text` (keep any names already imported). Add after `create_engine_with_path`:

```python
def read_alembic_revision(engine: Engine) -> str | None:
    """
    Read the database's current Alembic revision.

    Args:
        engine: Engine for the database to inspect

    Returns:
        The revision in ``alembic_version``, or None when the table is missing
        or empty

    """
    if "alembic_version" not in inspect(engine).get_table_names():
        return None
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).fetchone()
    return cast("str", row[0]) if row else None
```

In `oeapp/services/migration.py` add `read_alembic_revision` to the `from oeapp.db import (...)` list and replace the body of `db_migration_version` (keep its docstring) with `return read_alembic_revision(self.engine)`.

In `oeapp/services/backup.py` change the import to `from oeapp.db import get_project_db_path, read_alembic_revision` and replace the body of `get_current_migration_version` (keep its docstring) with `return read_alembic_revision(engine)`.

- [ ] **Step 4: Run tests and gates**

Run: `.venv/bin/pytest tests/test_db.py tests/test_backup.py tests/test_migration_backup_restore.py -q`
Expected: PASS (existing `test_get_current_migration_version_no_table` still passes).
Run: `.venv/bin/ruff check oeapp/db.py oeapp/services/migration.py oeapp/services/backup.py` and remove any import ruff reports as unused (`inspect`/`text` may now be unused in `backup.py`). Then `.venv/bin/mypy oeapp/db.py oeapp/services/migration.py oeapp/services/backup.py`.
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add oeapp/db.py oeapp/services/migration.py oeapp/services/backup.py tests/test_db.py
git commit -m "refactor: one alembic_version reader in oeapp.db" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `create_backup` contract (D2, D2a, D2b)

Unique filenames, WAL-safe snapshot, `prune` switch, `maintained_by`, `created_by_version`, and a revision that survives a project-listing failure.

**Files:**
- Modify: `oeapp/services/backup.py` (imports; `extract_backup_metadata`; `create_backup`; new private helpers; new constant)
- Test: `tests/test_backup.py`

**Interfaces:**
- Produces (used by Tasks 4, 5, 7): `LAST_APP_VERSION_KEY: Final[str] = "app/current_version"` (module global); `BackupService.create_backup(self, *, prune: bool = True, maintained_by: str | None = __version__) -> Path`; `BackupService.extract_backup_metadata(self, engine, *, maintained_by: str | None = __version__) -> dict[str, Any]`; sidecar keys `application_version` (maintained by) and `created_by_version` (always `__version__`).

- [ ] **Step 1: Write the failing tests**

Append to `class TestBackupService` in `tests/test_backup.py` (add `import sqlite3` at the top of the file):

```python
    def test_create_backup_includes_pages_still_in_the_wal(self, backup_service, tmp_path):
        db_path = tmp_path / "wal.db"
        live = sqlite3.connect(db_path)
        live.execute("pragma journal_mode=wal")
        live.execute("pragma wal_autocheckpoint=0")
        live.execute("create table t (v text)")
        live.execute("insert into t values ('in-the-wal')")
        live.commit()
        backup_service.db_path = db_path

        backup_path = backup_service.create_backup()
        live.close()

        copy = sqlite3.connect(backup_path)
        assert copy.execute("select v from t").fetchall() == [("in-the-wal",)]
        copy.close()

    def test_backups_in_the_same_instant_get_distinct_files(self, backup_service):
        fixed = datetime(2026, 10, 3, 12, 0, 0, 123456, tzinfo=UTC)
        with patch("oeapp.services.backup.datetime") as clock:
            clock.now.return_value = fixed
            first = backup_service.create_backup()
            second = backup_service.create_backup()

        assert first != second
        assert first.exists() and second.exists()
        assert first.with_suffix(".json").exists()
        assert second.with_suffix(".json").exists()

    def test_sidecar_records_maintaining_and_creating_versions(self, backup_service):
        from oeapp import __version__

        default = json.loads(backup_service.create_backup().with_suffix(".json").read_text())
        stamped = json.loads(
            backup_service.create_backup(maintained_by="0.9.0").with_suffix(".json").read_text()
        )
        unknown = json.loads(
            backup_service.create_backup(maintained_by=None).with_suffix(".json").read_text()
        )

        assert default["application_version"] == __version__
        assert stamped["application_version"] == "0.9.0"
        assert unknown["application_version"] is None
        assert {default["created_by_version"], stamped["created_by_version"]} == {__version__}

    def test_prune_false_defers_retention(self, backup_service):
        backup_service.settings.setValue("backup/num_backups", 1)

        backup_service.create_backup(prune=False)
        backup_service.create_backup(prune=False)
        assert len(list(backup_service.backup_dir.glob("*.db"))) == 2

        backup_service.cleanup_old_backups()
        assert len(list(backup_service.backup_dir.glob("*.db"))) == 1

    def test_sidecar_keeps_the_revision_when_projects_cannot_be_listed(self, backup_service):
        engine_db = backup_service.db_path
        connection = sqlite3.connect(engine_db)
        connection.execute("create table alembic_version (version_num varchar(32) primary key)")
        connection.execute("insert into alembic_version values ('f38623b35077')")
        connection.commit()
        connection.close()

        with patch("oeapp.services.backup.Project.list", side_effect=SQLAlchemyError("no table")):
            sidecar = json.loads(backup_service.create_backup().with_suffix(".json").read_text())

        assert sidecar["migration_version"] == "f38623b35077"
        assert sidecar["projects"] == []
```

Add `from sqlalchemy.exc import SQLAlchemyError` to the imports of `tests/test_backup.py`.

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_backup.py -k "wal or same_instant or maintaining or prune_false or keeps_the_revision" -v`
Expected: 5 FAIL (WAL: `no such table: t`; same-instant: files equal or overwritten; others: `unexpected keyword argument`).

- [ ] **Step 3: Implement**

In `oeapp/services/backup.py`:

1. Imports: add `import sqlite3`; remove `import shutil` and `from sqlalchemy.orm import sessionmaker` after the edits below if ruff reports them unused. Keep `create_engine`, `SQLAlchemyError`, `Project`.
2. Add a module global after the imports (below `if TYPE_CHECKING:` block):

```python
#: QSettings key holding the application version that last started successfully.
LAST_APP_VERSION_KEY: Final[str] = "app/current_version"
```
(add `Final` to the `typing` import).

3. Replace `extract_backup_metadata` entirely with:

```python
    def extract_backup_metadata(
        self, engine: Engine, *, maintained_by: str | None = __version__
    ) -> dict[str, Any]:
        """
        Extract metadata from the database for a backup sidecar.

        Args:
            engine: SQLAlchemy engine for the database being backed up

        Keyword Args:
            maintained_by: Application version that maintained the captured state

        Returns:
            Dictionary containing backup metadata

        """
        db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
        return {
            "backup_timestamp": datetime.now(UTC).isoformat(),
            "database_file_size": db_size,
            "migration_version": self.get_current_migration_version(engine),
            "application_version": maintained_by,
            "created_by_version": __version__,
            "projects": self._project_summaries(),
        }

    def _project_summaries(self) -> list[dict[str, Any]]:
        """
        Summarise each project for the sidecar.

        Returns:
            One dict per project, or an empty list when projects cannot be read

        """
        try:
            return [
                {
                    "id": project.id,
                    "name": project.name,
                    "last_updated": project.updated_at.isoformat(),
                    "token_count": project.total_token_count(),
                }
                for project in Project.list()
            ]
        except SQLAlchemyError as e:
            self.logger.warning("backup.projects.failed", error=e)
            return []
```

4. Replace `create_backup` entirely (from `def create_backup` to just before `def cleanup_old_backups`) with:

```python
    def create_backup(
        self, *, prune: bool = True, maintained_by: str | None = __version__
    ) -> "Path":
        """
        Create a backup of the database immediately.

        Keyword Args:
            prune: Whether to enforce the retention limit afterwards
            maintained_by: Application version that maintained the database
                state being captured (the running version unless a caller is
                capturing state the previous version left)

        Side Effects:
            Writes a ``.db`` snapshot and ``.json`` sidecar to the backup
            directory and updates the last-backup time.

        Raises:
            BackupFailed: If the database is missing or the backup fails

        Returns:
            Path to the created backup file

        """
        if not self.db_path.exists():
            raise BackupFailed(OSError("Database file does not exist"), self.db_path)
        backup_path, metadata_path = self._free_backup_paths()
        try:
            self._snapshot(self.db_path, backup_path)
        except (OSError, sqlite3.Error) as e:
            self.logger.exception(
                "backup.failed", error=e, backup_path=str(backup_path)
            )
            raise BackupFailed(e, backup_path) from e
        metadata = self._collect_metadata(maintained_by)
        try:
            with metadata_path.open("w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        except (OSError, TypeError) as e:
            self.logger.exception(
                "backup.metadata.save.failed",
                error=e,
                backup_path=str(backup_path),
            )
            raise BackupFailed(e, metadata_path) from e
        self.set_last_backup_time(datetime.now(UTC))
        if prune:
            self._prune_quietly()
        self.logger.info("backup.success", backup_path=str(backup_path))
        return backup_path

    def _free_backup_paths(self) -> tuple["Path", "Path"]:
        """
        Pick a backup path and sidecar path that do not exist yet.

        Returns:
            The ``.db`` path and its ``.json`` sidecar path

        """
        stamp = datetime.now(UTC).strftime("%Y-%m-%d_%H-%M-%S-%f")
        base = f"{self.db_path.stem}_{stamp}"
        attempt = 0
        while True:
            name = base if attempt == 0 else f"{base}-{attempt}"
            backup_path = self.backup_dir / f"{name}.db"
            metadata_path = backup_path.with_suffix(".json")
            if not backup_path.exists() and not metadata_path.exists():
                return backup_path, metadata_path
            attempt += 1

    @staticmethod
    def _snapshot(source_path: "Path", target_path: "Path") -> None:
        """
        Copy a database with SQLite's backup API (WAL-safe).

        Args:
            source_path: Database to read
            target_path: File to write

        """
        source = sqlite3.connect(source_path)
        target = sqlite3.connect(target_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def _collect_metadata(self, maintained_by: str | None) -> dict[str, Any]:
        """
        Build the sidecar metadata, falling back to minimal metadata on failure.

        Args:
            maintained_by: Application version that maintained the captured state

        Returns:
            Sidecar metadata dictionary

        """
        engine = create_engine(
            f"sqlite:///{self.db_path}", connect_args={"check_same_thread": False}
        )
        try:
            return self.extract_backup_metadata(engine, maintained_by=maintained_by)
        except (SQLAlchemyError, OSError) as e:
            self.logger.exception("backup.metadata.extraction.failed", error=e)
            return {
                "backup_timestamp": datetime.now(UTC).isoformat(),
                "database_file_size": 0,
                "migration_version": None,
                "application_version": maintained_by,
                "created_by_version": __version__,
                "projects": [],
            }
        finally:
            engine.dispose()

    def _prune_quietly(self) -> None:
        """Enforce retention, logging instead of failing the backup."""
        try:
            self.cleanup_old_backups()
        except OSError as e:
            self.logger.warning("backup.cleanup.failed", error=e)
```

(`restore_backup` still uses `shutil` until Task 4; keep the `shutil` import for now and remove it in Task 4.)

- [ ] **Step 4: Run tests and gates**

Run: `.venv/bin/pytest tests/test_backup.py -q`
Expected: all PASS.
Run: `.venv/bin/ruff check oeapp/services/backup.py tests/test_backup.py` and `.venv/bin/mypy oeapp/services/backup.py`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add oeapp/services/backup.py tests/test_backup.py
git commit -m "feat: WAL-safe, collision-free backups with maintained-by sidecar versions" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: WAL-safe `restore_backup` that never prunes first (D3)

**Files:**
- Modify: `oeapp/services/backup.py` (`restore_backup`; new `read_backup_metadata`, `_restore_snapshot`; remove `shutil` import)
- Modify: `tests/test_backup.py` (rewrite `test_restore_backup_copies_file`; add new tests)

**Interfaces:**
- Consumes: Task 3's `create_backup(prune=...)`.
- Produces (used by Tasks 7, 9): `BackupService.restore_backup(self, backup_path: Path) -> dict[str, Any] | None` (None when the file is missing or the restore fails; otherwise the sidecar metadata, `{}` when none); `BackupService.read_backup_metadata(self, backup_path: Path) -> dict[str, Any]` (`{}` when the sidecar is missing or corrupt).

- [ ] **Step 1: Write the failing tests and fix the fake-file test**

In `tests/test_backup.py` add module-level helpers below the imports:

```python
def _make_sqlite(path: Path, value: str) -> None:
    connection = sqlite3.connect(path)
    connection.execute("create table t (v text)")
    connection.execute("insert into t values (?)", (value,))
    connection.commit()
    connection.close()


def _read_value(path: Path) -> str:
    connection = sqlite3.connect(path)
    try:
        return connection.execute("select v from t").fetchone()[0]
    finally:
        connection.close()
```

Replace the body of `test_restore_backup_copies_file` with:

```python
        backup_file = temp_backup_dir / "backup.db"
        _make_sqlite(backup_file, "restored")

        with patch.object(backup_service, "create_backup"):
            backup_service.restore_backup(backup_file)

        assert _read_value(mock_db_path) == "restored"
```

Append to `class TestBackupService`:

```python
    def test_restore_never_prunes_before_the_copy(self, backup_service):
        backup_service.settings.setValue("backup/num_backups", 1)
        _make_sqlite(backup_service.db_path, "original")
        backup_path = backup_service.create_backup()
        connection = sqlite3.connect(backup_service.db_path)
        connection.execute("update t set v='changed'")
        connection.commit()
        connection.close()

        metadata = backup_service.restore_backup(backup_path)

        assert metadata is not None
        assert metadata["application_version"]  # sidecar read before pruning removed it
        assert _read_value(backup_service.db_path) == "original"

    def test_restore_proceeds_when_the_safety_copy_fails(self, backup_service, temp_backup_dir):
        backup_file = temp_backup_dir / "backup.db"
        _make_sqlite(backup_file, "restored")

        with patch.object(
            backup_service, "create_backup", side_effect=BackupFailed(OSError("disk full"), backup_file)
        ):
            metadata = backup_service.restore_backup(backup_file)

        assert metadata is not None
        assert _read_value(backup_service.db_path) == "restored"

    def test_read_backup_metadata_tolerates_a_missing_or_corrupt_sidecar(self, backup_service, temp_backup_dir):
        backup_file = temp_backup_dir / "x.db"
        backup_file.touch()
        assert backup_service.read_backup_metadata(backup_file) == {}

        backup_file.with_suffix(".json").write_text("{not json")
        assert backup_service.read_backup_metadata(backup_file) == {}
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_backup.py -k "restore or read_backup_metadata" -v`
Expected: `test_restore_never_prunes_before_the_copy` FAIL (`assert None is not None`: the safety copy pruned the source), `test_restore_proceeds_when_the_safety_copy_fails` FAIL (`BackupFailed` propagates), `test_read_backup_metadata_...` FAIL (`AttributeError`), `test_restore_backup_copies_file` FAIL (old code copies bytes, new fixture reads fine; it may pass before the change, which is acceptable).

- [ ] **Step 3: Implement**

Replace `restore_backup` in `oeapp/services/backup.py` and add the helpers:

```python
    def restore_backup(self, backup_path: "Path") -> dict[str, Any] | None:
        """
        Restore a backup over the current database.

        Retention is enforced only after the copy, so the safety copy of the
        current database can never evict the backup being restored.

        Args:
            backup_path: Path to the backup file to restore

        Side Effects:
            Overwrites the live database and may prune old backups.

        Returns:
            The backup's sidecar metadata (empty when it has none), or None if
            the file is missing or the restore failed

        """
        if not backup_path.exists():
            return None
        try:
            self.create_backup(prune=False)
        except BackupFailed:
            self.logger.warning("backup.restore.safety-copy.failed")
        try:
            self._restore_snapshot(backup_path)
        except (OSError, sqlite3.Error) as e:
            self.logger.exception(
                "backup.restore.failed", error=e, backup_path=str(backup_path)
            )
            return None
        metadata = self.read_backup_metadata(backup_path)  # before pruning may delete it
        self._prune_quietly()
        return metadata

    def _restore_snapshot(self, backup_path: "Path") -> None:
        """
        Write a backup over the live database with SQLite's backup API.

        Args:
            backup_path: Backup file to read

        """
        source = sqlite3.connect(backup_path)
        target = sqlite3.connect(self.db_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()

    def read_backup_metadata(self, backup_path: "Path") -> dict[str, Any]:
        """
        Read a backup's sidecar JSON.

        Args:
            backup_path: Path to the backup file

        Returns:
            The sidecar metadata, or an empty dict if it is missing or corrupt

        """
        json_file = backup_path.with_suffix(".json")
        if not json_file.exists():
            return {}
        try:
            with json_file.open("r", encoding="utf-8") as f:
                return cast("dict[str, Any]", json.load(f))
        except (OSError, json.JSONDecodeError) as e:
            self.logger.warning(
                "backup.metadata.load.failed", error=e, backup_path=str(backup_path)
            )
            return {}
```

Remove the now-unused `import shutil` from `oeapp/services/backup.py`.

- [ ] **Step 4: Run tests and gates**

Run: `.venv/bin/pytest tests/test_backup.py tests/test_restore_dialog.py -q`
Expected: all PASS.
Run: `.venv/bin/ruff check oeapp/services/backup.py tests/test_backup.py && .venv/bin/mypy oeapp/services/backup.py`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add oeapp/services/backup.py tests/test_backup.py
git commit -m "fix: restore never prunes before the copy and uses the SQLite backup API" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The injected engine is authoritative, with foreign keys OFF (D8)

**Files:**
- Modify: `oeapp/services/backup.py` (`__init__` takes `db_path`)
- Modify: `oeapp/services/migration.py` (`__init__`; `apply_migrations`; new `_upgrade_to_head`)
- Modify: `oeapp/models/alembic/env.py` (`run_migrations_online`)
- Test: `tests/test_migration_engine.py` (new)

**Interfaces:**
- Consumes: Task 1's `build_baseline_db`, `SEED_COUNTS`, `BASELINE_REVISION`; Task 2's `read_alembic_revision`.
- Produces: `BackupService.__init__(self, db_path: Path | None = None)`; `MigrationService.db_path: Path`; `MigrationService._upgrade_to_head(self) -> None` (private, used by `apply_migrations`); `env.py` honours `config.attributes["connection"]`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_migration_engine.py`:

```python
"""Migrations act on the injected engine's database, with foreign keys OFF."""

import sqlite3
from unittest.mock import MagicMock, patch

from oeapp.db import create_engine_with_path, read_alembic_revision
from oeapp.services.migration import MigrationService
from tests.migration_baseline import SEED_COUNTS, build_baseline_db


def _service(engine) -> MigrationService:
    return MigrationService(
        backup_service=MagicMock(), engine=engine, migration_metadata_service=MagicMock()
    )


def test_upgrade_targets_the_injected_engine_not_the_env_path(tmp_path, monkeypatch):
    real, decoy = tmp_path / "real.db", tmp_path / "decoy.db"
    build_baseline_db(real)
    monkeypatch.setenv("AENGLISC_TOOLKIT_DB_PATH", str(decoy))
    engine = create_engine_with_path(real)
    service = _service(engine)

    service.apply_migrations()

    assert read_alembic_revision(engine) == service.code_migration_version()
    assert not decoy.exists() or decoy.stat().st_size == 0


def test_upgrade_runs_with_foreign_keys_off_then_restores_them(tmp_path):
    db_path = tmp_path / "live.db"
    build_baseline_db(db_path)
    engine = create_engine_with_path(db_path)
    seen: list[int] = []

    def fake_upgrade(config, revision):
        connection = config.attributes["connection"]
        seen.append(connection.exec_driver_sql("PRAGMA foreign_keys").scalar())

    with patch("oeapp.services.migration.command.upgrade", side_effect=fake_upgrade):
        _service(engine).apply_migrations()

    assert seen == [0]
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1


def test_upgrade_with_the_app_engine_keeps_every_row(tmp_path):
    db_path = tmp_path / "live.db"
    build_baseline_db(db_path)
    engine = create_engine_with_path(db_path)  # foreign_keys=ON listener, like the app

    _service(engine).apply_migrations()

    connection = sqlite3.connect(db_path)
    try:
        counts = {
            table: connection.execute(f"select count(*) from {table}").fetchone()[0]
            for table in SEED_COUNTS
        }
    finally:
        connection.close()
    assert counts == SEED_COUNTS
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_migration_engine.py -v`
Expected: FAIL. Test 1: the revision is still the baseline (Alembic upgraded the decoy path). Test 2: `KeyError: 'connection'`. Test 3 may pass or fail depending on the pragma; it must pass after the change.

- [ ] **Step 3: Implement**

`oeapp/services/backup.py`: change `__init__` to

```python
    def __init__(self, db_path: "Path | None" = None) -> None:
        """
        Initialize backup service.

        Args:
            db_path: Database file to back up (defaults to the project database)

        """
        super().__init__()
        #: The global settings for the application.
        self.settings = QSettings()
        #: The path to the project database.
        self.db_path = db_path if db_path is not None else get_project_db_path()
        #: The directory to store backups.
        self.backup_dir = self.db_path.parent / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        #: The logger
        self.logger = get_logger(__name__)
```
(`Path` is already imported under `TYPE_CHECKING`; keep the string annotation.)

`oeapp/services/migration.py`: replace the engine/backup section of `MigrationService.__init__` so the engine is built first and the backup service follows it:

```python
        #: The logger for the migration service.
        self.logger = get_logger(__name__)
        #: Engine.
        self.engine = engine if engine is not None else create_engine_with_path()
        #: Database file the engine points at; backup, upgrade and restore all use it.
        database = self.engine.url.database
        self.db_path = Path(database) if database else get_project_db_path()
        #: Allow dependency injection for testing, but create defaults for normal use
        self.backup_service = (
            backup_service
            if backup_service is not None
            else BackupService(db_path=self.db_path)
        )
        #: Migration metadata service.
        self.migration_metadata_service = (
            migration_metadata_service
            if migration_metadata_service is not None
            else MigrationMetadataService()
        )
```

In `apply_migrations`, replace the line `command.upgrade(self.config, "head")` with `self._upgrade_to_head()` and add:

```python
    def _upgrade_to_head(self) -> None:
        """
        Run ``alembic upgrade head`` on the injected engine's database.

        Foreign keys are switched OFF on the migration connection before any
        statement, because batch table recreation under ``foreign_keys=ON`` can
        cascade-delete child rows. The pragma is a no-op once a transaction has
        begun, so it must come first. It is switched back ON afterwards because
        the pooled connection is reused.

        Side Effects:
            Upgrades the database schema and commits.

        """
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            config = self.config
            config.attributes["connection"] = connection
            try:
                command.upgrade(config, "head")
                connection.commit()
            finally:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
```

`oeapp/models/alembic/env.py`: replace `run_migrations_online` with:

```python
def _run_with_connection(connection) -> None:
    """Configure Alembic on ``connection`` and run the migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        render_as_batch=True,  # Enable batch mode for SQLite
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    When the caller injected a connection (``config.attributes["connection"]``)
    it is used as is; otherwise an engine is built from the configured URL.
    """
    injected = config.attributes.get("connection")
    if injected is not None:
        _run_with_connection(injected)
        return
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _run_with_connection(connection)
```

- [ ] **Step 4: Run tests and gates**

Run: `.venv/bin/pytest tests/test_migration_engine.py tests/test_migration_baseline.py tests/test_migration_backup_restore.py tests/test_backup.py -q`
Expected: all PASS (the baseline tests use the env-path fallback, guarding that Alembic run from the command line is unchanged).
Run: `.venv/bin/ruff check oeapp/services oeapp/models/alembic/env.py tests/test_migration_engine.py && .venv/bin/mypy oeapp/services/migration.py oeapp/services/backup.py`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add oeapp/services/backup.py oeapp/services/migration.py oeapp/models/alembic/env.py tests/test_migration_engine.py
git commit -m "fix: migrations act on the injected engine with foreign keys OFF" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Delete skip/abort and dead code (D9, D10)

**Files:**
- Modify: `oeapp/services/migration.py` (delete `should_abort`, `BackupFileMetadataService`, `MigrationService.restore`; drop `skip_until_version`; drop the `MigrationSkipped` import)
- Modify: `oeapp/exc.py` (delete `MigrationSkipped`)
- Modify: `oeapp/ui/main_window.py` (`_handle_migrations`)
- Modify: `tests/test_exc.py` (delete the `MigrationSkipped` class and import)

**Interfaces:**
- Produces: `MigrationService.migrate(self) -> MigrationResult` (no argument). Task 7 rewrites its body.

- [ ] **Step 1: Prove what is unreferenced**

Run: `grep -rn "should_abort\|MigrationSkipped\|BackupFileMetadataService\|skip_until_version\|\.restore(" oeapp tests --include=*.py | grep -v "^tests/test_exc.py"`
Expected: matches only in `oeapp/services/migration.py`, `oeapp/exc.py` and `oeapp/ui/main_window.py` (no test calls them). If anything else appears, stop and inspect it before deleting.

- [ ] **Step 2: Delete**

- `oeapp/services/migration.py`: remove `def should_abort`, the whole `class BackupFileMetadataService`, `def restore`; change the signature to `def migrate(self) -> MigrationResult:`, remove the `skip_until_version` docstring entry and the `if skip_until_version:` block (the three lines raising `MigrationSkipped`), and remove `MigrationSkipped` from the `from oeapp.exc import (...)` list.
- `oeapp/exc.py`: delete `class MigrationSkipped`.
- `oeapp/ui/main_window.py` `_handle_migrations`: delete the `skip_until_version = cast(...)` statement and call `migration_service.migrate()`.
- `tests/test_exc.py`: delete `class TestMigrationSkipped` and `MigrationSkipped` from the import.

- [ ] **Step 3: Run tests and gates**

Run: `.venv/bin/pytest -q -x -p no:cacheprovider 2>&1 | tail -4`
Expected: PASS (same count as the baseline minus the deleted `TestMigrationSkipped` tests).
Run: `.venv/bin/ruff check oeapp tests/test_exc.py` and remove any import ruff reports as unused (`cast` may remain used); `.venv/bin/mypy oeapp/services/migration.py oeapp/ui/main_window.py oeapp/exc.py`
Expected: no new errors.

- [ ] **Step 4: Commit**

```bash
git add oeapp tests/test_exc.py
git commit -m "refactor: delete unreachable skip/abort and unused backup-metadata service" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 7: New `migrate()` flow (D1, D2a stamping, D4, D5)

**Files:**
- Modify: `oeapp/services/migration.py` (`has_pending_migrations`, `migrate`, new private helpers; delete `_get_pre_migration_backup_path`, `_create_pre_migration_backup`, `_restore_pre_migration_backup`, `_delete_pre_migration_backup`)
- Modify: `oeapp/ui/main_window.py` (use `LAST_APP_VERSION_KEY`)
- Modify: `tests/test_migration_backup_restore.py` (delete `TestPreMigrationBackup`, `TestMigrationFlow`, `TestMigrationFailureDialog`)
- Test: `tests/test_migration_flow.py` (new)

**Interfaces:**
- Consumes: Task 3's `create_backup(prune=, maintained_by=)`, `LAST_APP_VERSION_KEY`; Task 4's `restore_backup`.
- Produces: `MigrationService.migrate(self) -> MigrationResult`; `MigrationFailed(error, backup_app_version, backup_migration_version)` where `backup_app_version` is the pre-migration sidecar's `application_version`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_migration_flow.py`:

```python
"""migrate(): backups before and after, rollback, and no backup for a fresh database."""

import json
from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from PySide6.QtCore import QSettings

from oeapp import __version__
from oeapp.db import create_engine_with_path
from oeapp.exc import BackupFailed, MigrationFailed
from oeapp.services.backup import LAST_APP_VERSION_KEY, BackupService
from oeapp.services.migration import MigrationResult, MigrationService
from tests.test_migration_backup_restore import InMemoryMigrationMetadataService

#: A real, older revision from the chain.
OLD_REV = "f38623b35077"


def _value(db_path) -> str:
    import sqlite3

    connection = sqlite3.connect(db_path)
    try:
        return connection.execute("select v from t").fetchone()[0]
    finally:
        connection.close()


def _set(service: MigrationService, statement: str) -> None:
    with service.engine.begin() as conn:
        conn.exec_driver_sql(statement)


@pytest.fixture
def flow(tmp_path):
    QSettings().clear()
    db_path = tmp_path / "live.db"
    engine = create_engine_with_path(db_path)
    with engine.begin() as conn:
        conn.exec_driver_sql("create table t (v text)")
        conn.exec_driver_sql("insert into t values ('original')")
        conn.exec_driver_sql(
            "create table alembic_version (version_num varchar(32) not null primary key)"
        )
        conn.exec_driver_sql(f"insert into alembic_version values ('{OLD_REV}')")
    service = MigrationService(
        backup_service=BackupService(db_path=db_path),
        engine=engine,
        migration_metadata_service=InMemoryMigrationMetadataService(),
    )
    yield service
    engine.dispose()


def _succeeding_apply(service: MigrationService):
    head = service.code_migration_version()

    def apply() -> MigrationResult:
        _set(service, f"update alembic_version set version_num='{head}'")
        return MigrationResult(app_version=__version__, migration_version=head)

    return apply


def _failing_apply(service: MigrationService):
    def apply() -> MigrationResult:
        _set(service, "update t set v='half-migrated'")
        msg = "boom"
        raise RuntimeError(msg)

    return apply


def _backups(service: MigrationService) -> list[dict]:
    return sorted(
        service.backup_service.get_backup_list(), key=lambda b: b["backup_timestamp"]
    )


class TestPending:
    def test_pending_ignores_the_catalog(self, flow):
        head = flow.code_migration_version()
        _set(flow, f"update alembic_version set version_num='{head}'")
        flow.migration_metadata_service.versions = {head: "0.0.1", OLD_REV: __version__}

        assert flow.has_pending_migrations() is False

    def test_pending_when_the_database_is_behind(self, flow):
        assert flow.has_pending_migrations() is True

    def test_not_pending_without_any_migration_files(self, flow):
        with patch.object(flow, "code_migration_version", return_value=None):
            assert flow.has_pending_migrations() is False


class TestMigrate:
    def test_no_pending_takes_no_backup(self, flow):
        with patch.object(flow, "has_pending_migrations", return_value=False):
            flow.migrate()
        assert _backups(flow) == []

    def test_success_takes_pre_and_post_backups(self, flow):
        QSettings().setValue(LAST_APP_VERSION_KEY, "1.0.0")
        head = flow.code_migration_version()
        with patch.object(flow, "apply_migrations", side_effect=_succeeding_apply(flow)):
            flow.migrate()

        pairs = [(b["migration_version"], b["application_version"]) for b in _backups(flow)]
        assert pairs == [(OLD_REV, "1.0.0"), (head, __version__)]

    def test_success_with_one_retained_backup_keeps_the_post_migration_one(self, flow):
        QSettings().setValue("backup/num_backups", 1)
        head = flow.code_migration_version()
        with patch.object(flow, "apply_migrations", side_effect=_succeeding_apply(flow)):
            flow.migrate()

        remaining = _backups(flow)
        assert [b["migration_version"] for b in remaining] == [head]

    def test_a_failed_post_migration_backup_does_not_fail_the_migration(self, flow):
        real = flow.backup_service.create_backup
        calls: list[dict] = []

        def flaky(**kwargs):
            calls.append(kwargs)
            if len(calls) == 2:
                raise BackupFailed(OSError("disk full"), flow.db_path)
            return real(**kwargs)

        head = flow.code_migration_version()
        with (
            patch.object(flow.backup_service, "create_backup", side_effect=flaky),
            patch.object(flow, "apply_migrations", side_effect=_succeeding_apply(flow)),
        ):
            result = flow.migrate()

        assert result.migration_version == head
        assert flow.db_migration_version() == head

    def test_a_failed_pre_migration_backup_stops_before_upgrading(self, flow):
        with (
            patch.object(
                flow.backup_service,
                "create_backup",
                side_effect=BackupFailed(OSError("no"), flow.db_path),
            ),
            patch.object(flow, "apply_migrations") as apply,
            pytest.raises(MigrationFailed),
        ):
            flow.migrate()
        apply.assert_not_called()

    def test_failure_within_one_second_restores_the_original_data(self, flow):
        QSettings().setValue(LAST_APP_VERSION_KEY, "1.0.0")
        fixed = datetime(2026, 10, 3, 12, 0, 0, 5, tzinfo=UTC)
        with (
            patch("oeapp.services.backup.datetime") as clock,
            patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)),
        ):
            clock.now.return_value = fixed
            with pytest.raises(MigrationFailed) as failure:
                flow.migrate()

        assert _value(flow.db_path) == "original"
        assert failure.value.backup_app_version == "1.0.0"
        assert failure.value.backup_migration_version == OLD_REV
        assert len(_backups(flow)) == 2  # pre-migration copy and failed-state safety copy

    def test_failure_with_one_retained_backup_still_restores(self, flow):
        QSettings().setValue("backup/num_backups", 1)
        with patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)):
            with pytest.raises(MigrationFailed):
                flow.migrate()
        assert _value(flow.db_path) == "original"

    def test_failure_never_names_the_running_version(self, flow):
        # LAST_APP_VERSION_KEY is unset: the previous build is unknown
        with patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)):
            with pytest.raises(MigrationFailed) as failure:
                flow.migrate()
        assert failure.value.backup_app_version is None

    def test_pre_migration_sidecar_does_not_carry_the_running_version(self, flow):
        QSettings().setValue(LAST_APP_VERSION_KEY, "1.0.0")
        with patch.object(flow, "apply_migrations", side_effect=_failing_apply(flow)):
            with pytest.raises(MigrationFailed):
                flow.migrate()
        first = _backups(flow)[0]
        sidecar = json.loads(first["metadata_path"].read_text())
        assert sidecar["application_version"] == "1.0.0"
        assert sidecar["created_by_version"] == __version__

    def test_fresh_database_takes_no_backup(self, tmp_path):
        QSettings().clear()
        engine = create_engine_with_path(tmp_path / "fresh.db")
        service = MigrationService(
            backup_service=BackupService(db_path=tmp_path / "fresh.db"),
            engine=engine,
            migration_metadata_service=InMemoryMigrationMetadataService(),
        )

        result = service.migrate()

        assert service.backup_service.get_backup_list() == []
        assert result.migration_version == service.code_migration_version()
        engine.dispose()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_migration_flow.py -v`
Expected: FAIL (the old `migrate()` uses `.pre-migration` files and ignores `BackupService`: e.g. `[] != [(OLD_REV, '1.0.0'), ...]`, `AttributeError`, wrong failure data).

- [ ] **Step 3: Implement**

In `oeapp/services/migration.py`:

- Imports: add `LAST_APP_VERSION_KEY` to `from .backup import BackupService` (`from .backup import LAST_APP_VERSION_KEY, BackupService`), add `from sqlalchemy.exc import SQLAlchemyError`.
- Delete `_get_pre_migration_backup_path`, `_create_pre_migration_backup`, `_restore_pre_migration_backup`, `_delete_pre_migration_backup`.
- Replace `has_pending_migrations` (keep a docstring) with:

```python
    def has_pending_migrations(self) -> bool:
        """
        Check whether the database revision differs from the Alembic head.

        Alembic is the only source of truth: the application-version catalog
        plays no part.

        Returns:
            True if the database revision is not the head, False otherwise

        """
        head_version = self.code_migration_version()
        if head_version is None:
            return False
        return self.db_migration_version() != head_version
```

- Replace `migrate` with the following and add the helpers after it:

```python
    def migrate(self) -> MigrationResult:
        """
        Migrate the database to the latest version.

        A Fresh Database is built and stamped with no backup. Otherwise a
        Pre-migration Backup is taken, the upgrade runs, and a post-migration
        backup follows. On failure the pre-migration backup is restored.

        Side Effects:
            Writes backups, upgrades the database, and prunes old backups.

        Raises:
            MigrationFailed: If the backup or the migration fails

        Returns:
            The resulting migration state

        """
        if not self.has_pending_migrations():
            self.logger.info("migration.no-pending-migrations")
            db_version = self.db_migration_version()
            return MigrationResult(
                app_version=__version__,
                migration_version=db_version if db_version else "",
            )
        if self.db_migration_version() is None:
            return self.apply_migrations()  # Fresh Database: nothing to protect
        backup_path = self._backup_before_migration()
        try:
            result = self.apply_migrations()
        except Exception as e:
            raise self._roll_back(e, backup_path) from e
        self._backup_after_migration()
        return result

    def _backup_before_migration(self) -> Path:
        """
        Take the Pre-migration Backup, stamped with the previous build's version.

        Raises:
            MigrationFailed: If the backup cannot be created

        Returns:
            Path to the backup

        """
        previous = cast(
            "str | None", QSettings().value(LAST_APP_VERSION_KEY, None, type=str)
        )
        try:
            return self.backup_service.create_backup(
                prune=False, maintained_by=previous or None
            )
        except BackupFailed as e:
            raise MigrationFailed(e, None, None) from e

    def _backup_after_migration(self) -> None:
        """
        Take the post-migration backup and enforce retention once.

        A failure here is logged, never raised: the migration has committed.
        """
        try:
            self.backup_service.create_backup(prune=False)
        except BackupFailed:
            self.logger.exception("migration.post-backup.failed")
        try:
            self.backup_service.cleanup_old_backups()
        except OSError:
            self.logger.exception("migration.cleanup.failed")

    def _roll_back(self, error: Exception, backup_path: Path) -> MigrationFailed:
        """
        Restore the pre-migration backup and describe the failure.

        Args:
            error: The exception that aborted the migration
            backup_path: The Pre-migration Backup to restore

        Side Effects:
            Overwrites the live database with the backup.

        Returns:
            The exception to raise, carrying the previous build's version and the
            restored database's revision

        """
        metadata = self.backup_service.restore_backup(backup_path)
        if metadata is None:
            self.logger.error("migration.restore.failed", backup_path=str(backup_path))
        try:
            migration_version = self.db_migration_version()
        except (OSError, SQLAlchemyError) as version_error:
            self.logger.debug("migration.restore.version-unreadable", error=version_error)
            migration_version = None
        return MigrationFailed(
            error, (metadata or {}).get("application_version"), migration_version
        )
```

In `oeapp/ui/main_window.py` import `LAST_APP_VERSION_KEY` (`from oeapp.services.backup import LAST_APP_VERSION_KEY`) and replace the literal `"app/current_version"` with it.

In `tests/test_migration_backup_restore.py` delete `class TestPreMigrationBackup`, `class TestMigrationFlow` and `class TestMigrationFailureDialog` (their behaviour moved to `tests/test_migration_flow.py`); keep `InMemoryMigrationMetadataService`, the fixtures, `TestHasPendingMigrations`, `TestMigrationMetadataWriteGuards` and `TestFreshDatabaseStamp`. Remove imports left unused (`BackupFailed`, `MigrationFailed`, `logging`).

- [ ] **Step 4: Run tests and gates**

Run: `.venv/bin/pytest tests/test_migration_flow.py tests/test_migration_backup_restore.py tests/test_migration_failure_dialog.py -q`
Expected: all PASS.
Run: `.venv/bin/ruff check oeapp tests/test_migration_flow.py tests/test_migration_backup_restore.py` (remove imports ruff flags, for example `shutil`, `get_project_db_path`) and `.venv/bin/mypy oeapp/services/migration.py oeapp/ui/main_window.py`
Expected: no new errors.

- [ ] **Step 5: Mutation check**

Make each mutation, run `.venv/bin/pytest tests/test_migration_flow.py -q`, expect at least one FAIL, then revert it:
1. In `_backup_before_migration` pass `maintained_by=None` always (the sidecar stamp test must fail).
2. In `has_pending_migrations` return `False` when `db_version is None` instead of comparing (fresh test fails).
3. In `migrate` pass `prune=True` for the pre-migration backup (the `num_backups=1` failure test must fail).
4. In `_roll_back` skip `restore_backup` (restore tests fail).
Re-run: all PASS after reverting.

- [ ] **Step 6: Commit**

```bash
git add oeapp tests
git commit -m "feat: migrate() backs up through BackupService, rolls back safely, skips fresh databases" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Unknown database revision and version resolution (D6)

**Files:**
- Create: `oeapp/services/revision_version.py`
- Modify: `oeapp/exc.py` (`UnknownDatabaseRevision`)
- Modify: `oeapp/services/backup.py` (`application_versions_for`)
- Modify: `oeapp/services/migration.py` (`known_revisions`, `is_known_revision`, `ensure_known_revision`; call it first in `migrate`)
- Modify: `pyproject.toml` / `uv.lock` (declare `packaging`)
- Test: `tests/test_unknown_revision.py` (new)

**Interfaces:**
- Consumes: Task 7's `migrate()`; Task 3/4 sidecar fields.
- Produces: `UnknownDatabaseRevision(revision: str, required_app_version: str | None)` with attributes `.revision`, `.required_app_version`; `RevisionVersionResolver(metadata_service, backup_service).required_app_version(revision: str) -> str | None`; `BackupService.application_versions_for(revision: str) -> list[str]`; `MigrationService.is_known_revision(revision: str) -> bool`, `.ensure_known_revision() -> None`, `.revision_versions: RevisionVersionResolver`.

- [ ] **Step 1: Declare the dependency**

Run: `uv add packaging`
Expected: `pyproject.toml` gains a `packaging` entry and `uv.lock` updates. Verify: `grep -n packaging pyproject.toml`.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_unknown_revision.py`:

```python
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

    with patch.object(flow, "apply_migrations") as apply, pytest.raises(UnknownDatabaseRevision) as raised:
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
```

- [ ] **Step 3: Run to verify failure**

Run: `.venv/bin/pytest tests/test_unknown_revision.py -v`
Expected: FAIL (`ImportError: cannot import name 'UnknownDatabaseRevision'`).

- [ ] **Step 4: Implement**

`oeapp/exc.py`, add next to `MigrationFailed`:

```python
class UnknownDatabaseRevision(Exception):  # noqa: N818
    """
    Exception raised when the database revision is unknown to this build.

    Args:
        revision: The database's Alembic revision.
        required_app_version: Application version that understands it, or None
            when it cannot be determined.

    """

    def __init__(self, revision: str, required_app_version: str | None):
        """
        Initialize the instance.

        Args:
            revision: The database's Alembic revision.
            required_app_version: Application version that understands it, or
                None when it cannot be determined.

        """
        #: The database's Alembic revision.
        self.revision = revision
        #: Application version that understands the revision, if known.
        self.required_app_version = required_app_version
        super().__init__(f"Unknown database revision: {revision}")
```

`oeapp/services/backup.py`, add to `BackupService`:

```python
    def application_versions_for(self, revision: str) -> list[str]:
        """
        List the application versions recorded for backups at ``revision``.

        Args:
            revision: Alembic revision to match

        Returns:
            The ``application_version`` of every backup whose sidecar has that
            ``migration_version`` and a recorded application version

        """
        return [
            backup["application_version"]
            for backup in self.get_backup_list()
            if backup["migration_version"] == revision
            and backup["application_version"]
        ]
```

Create `oeapp/services/revision_version.py`:

```python
"""Resolve which application version a database revision needs."""

from typing import TYPE_CHECKING

from packaging.version import InvalidVersion, Version

if TYPE_CHECKING:
    from .backup import BackupService
    from .migration import MigrationMetadataService


class RevisionVersionResolver:
    """
    Name the application version that understands a database revision.

    The bundled catalog is consulted first. Backup sidecars come next: every
    build that took a backup at a revision understood it, so the smallest
    recorded version is the tightest answer.

    Args:
        metadata_service: Reads the revision-to-version catalog.
        backup_service: Lists backups and their sidecar versions.

    """

    def __init__(
        self,
        metadata_service: "MigrationMetadataService",
        backup_service: "BackupService",
    ) -> None:
        """
        Initialize the resolver.

        Args:
            metadata_service: Reads the revision-to-version catalog.
            backup_service: Lists backups and their sidecar versions.

        """
        #: Reads the revision-to-version catalog.
        self.metadata_service = metadata_service
        #: Lists backups and their sidecar versions.
        self.backup_service = backup_service

    def required_app_version(self, revision: str) -> str | None:
        """
        Find the application version that understands ``revision``.

        Args:
            revision: Alembic revision to look up

        Returns:
            A version string, or None when neither source knows

        """
        catalog = self.metadata_service.get_min_version_for_migration(revision)
        if catalog:
            return str(catalog)
        parsed: list[tuple[Version, str]] = []
        for raw in self.backup_service.application_versions_for(revision):
            try:
                parsed.append((Version(raw), raw))
            except InvalidVersion:
                continue
        return min(parsed)[1] if parsed else None
```

`oeapp/services/migration.py`: import `from oeapp.exc import ... UnknownDatabaseRevision` and `from .revision_version import RevisionVersionResolver`; in `__init__`, after `migration_metadata_service` is set, add:

```python
        #: Resolves which application version a database revision needs.
        self.revision_versions = RevisionVersionResolver(
            self.migration_metadata_service, self.backup_service
        )
```

Add methods to `MigrationService` (near `db_migration_version`):

```python
    def known_revisions(self) -> set[str]:
        """
        List every revision this build's Alembic scripts define.

        Returns:
            The set of revision IDs

        """
        return {script.revision for script in self.script.walk_revisions()}

    def is_known_revision(self, revision: str) -> bool:
        """
        Check whether this build understands a database revision.

        Args:
            revision: Alembic revision to check

        Returns:
            True if the revision is one of this build's scripts

        """
        return revision in self.known_revisions()

    def ensure_known_revision(self) -> None:
        """
        Refuse to proceed with a database this build does not understand.

        Raises:
            UnknownDatabaseRevision: If the database revision is not one of this
                build's scripts

        """
        revision = self.db_migration_version()
        if revision is None or self.is_known_revision(revision):
            return
        raise UnknownDatabaseRevision(
            revision, self.revision_versions.required_app_version(revision)
        )
```

In `migrate()`, add `self.ensure_known_revision()` as the first statement and add `UnknownDatabaseRevision` to its `Raises:` docstring.

- [ ] **Step 5: Run tests and gates**

Run: `.venv/bin/pytest tests/test_unknown_revision.py tests/test_migration_flow.py tests/test_backup.py -q`
Expected: all PASS.
Run: `.venv/bin/ruff check oeapp tests/test_unknown_revision.py && .venv/bin/mypy oeapp/services oeapp/exc.py`
Expected: no new errors.

- [ ] **Step 6: Commit**

```bash
git add oeapp pyproject.toml uv.lock tests/test_unknown_revision.py
git commit -m "feat: refuse an unknown database revision and name the version it needs" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Unknown-revision dialog and Restore refusal (D6, D6a)

**Files:**
- Create: `oeapp/ui/dialogs/unknown_revision.py`
- Modify: `oeapp/ui/dialogs/__init__.py` (import and `__all__`)
- Modify: `oeapp/ui/dialogs/restore.py` (`restore_backup`; new `_refuse_unknown_revision`)
- Test: `tests/test_unknown_revision_dialog.py` (new), `tests/test_restore_dialog.py` (modified)

**Interfaces:**
- Consumes: Task 8's `UnknownDatabaseRevision`, `MigrationService.is_known_revision`; Task 4's `read_backup_metadata`, `restore_backup`.
- Produces: `describe_unknown_revision(revision: str, required_app_version: str | None) -> str`; `FAQ_URL: str`; `UnknownRevisionDialog(main_window, error: UnknownDatabaseRevision)` with `.build()` and `.execute()`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_unknown_revision_dialog.py`:

```python
"""UnknownRevisionDialog and its message."""

from oeapp.exc import UnknownDatabaseRevision
from oeapp.ui.dialogs.unknown_revision import (
    FAQ_URL,
    UnknownRevisionDialog,
    describe_unknown_revision,
)


def test_message_names_the_version_when_it_is_known():
    text = describe_unknown_revision("zzz", "1.9.0")
    assert "1.9.0" in text
    assert "zzz" in text
    assert "Can't determine" not in text


def test_message_says_it_cannot_determine_the_version_otherwise():
    text = describe_unknown_revision("zzz", None)
    assert "Can't determine app version to use with db revision zzz" in text
    assert FAQ_URL in text


def test_dialog_builds_with_the_message(mock_main_window, qapp):
    error = UnknownDatabaseRevision("zzz", "1.9.0")
    dialog = UnknownRevisionDialog(mock_main_window, error)

    dialog.build()

    assert "version" in dialog.dialog.windowTitle().lower()
    assert dialog.message_label.text() == describe_unknown_revision("zzz", "1.9.0")
```

Append to `tests/test_restore_dialog.py` (add `from datetime import UTC, datetime` and `from unittest.mock import patch`):

```python
def _dialog(mock_main_window, backup_path):
    backups = [
        {
            "backup_path": backup_path,
            "backup_timestamp": datetime.now(UTC),
            "file_size": 10,
            "migration_version": "zzz",
            "application_version": "1.9.0",
        }
    ]
    with patch("oeapp.ui.dialogs.restore.BackupService") as service_cls:
        service_cls.return_value.get_backup_list.return_value = backups
        dialog = RestoreDialog(mock_main_window)
        dialog.build()
    dialog.backup_table.setCurrentCell(0, 0)
    return dialog


class TestRestoreRefusalAndExit:
    def test_refuses_a_backup_with_an_unknown_revision(self, mock_main_window, qapp, tmp_path):
        dialog = _dialog(mock_main_window, tmp_path / "b.db")
        with (
            patch("oeapp.ui.dialogs.restore.BackupService") as service_cls,
            patch("oeapp.ui.dialogs.restore.MigrationService") as migration_cls,
            patch("oeapp.ui.dialogs.restore.QMessageBox") as box,
        ):
            service_cls.return_value.read_backup_metadata.return_value = {
                "migration_version": "zzz",
                "application_version": "1.9.0",
            }
            migration_cls.return_value.is_known_revision.return_value = False

            dialog.restore_backup()

        service_cls.return_value.restore_backup.assert_not_called()
        box.assert_not_called()  # refused before asking for confirmation
        warning = mock_main_window.messages.show_warning.call_args
        assert "1.9.0" in warning.args[0]

    def test_a_backup_without_a_revision_is_not_refused(self, mock_main_window, qapp, tmp_path):
        dialog = _dialog(mock_main_window, tmp_path / "b.db")
        with (
            patch("oeapp.ui.dialogs.restore.BackupService") as service_cls,
            patch("oeapp.ui.dialogs.restore.MigrationService"),
            patch("oeapp.ui.dialogs.restore.QMessageBox") as box,
            patch("oeapp.ui.dialogs.restore.QApplication") as app,
        ):
            service_cls.return_value.read_backup_metadata.return_value = {}
            service_cls.return_value.restore_backup.return_value = {}
            box.return_value.exec.return_value = box.StandardButton.Yes

            dialog.restore_backup()

        service_cls.return_value.restore_backup.assert_called_once()
        app.quit.assert_called_once_with()

    def test_exits_after_a_successful_restore(self, mock_main_window, qapp, tmp_path):
        dialog = _dialog(mock_main_window, tmp_path / "b.db")
        with (
            patch("oeapp.ui.dialogs.restore.BackupService") as service_cls,
            patch("oeapp.ui.dialogs.restore.MigrationService") as migration_cls,
            patch("oeapp.ui.dialogs.restore.QMessageBox") as box,
            patch("oeapp.ui.dialogs.restore.QApplication") as app,
        ):
            service_cls.return_value.read_backup_metadata.return_value = {
                "migration_version": "f38623b35077"
            }
            migration_cls.return_value.is_known_revision.return_value = True
            service_cls.return_value.restore_backup.return_value = {
                "migration_version": "f38623b35077"
            }
            box.return_value.exec.return_value = box.StandardButton.Yes

            dialog.restore_backup()

        app.quit.assert_called_once_with()
        mock_main_window.messages.show_information.assert_called_once()
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_unknown_revision_dialog.py tests/test_restore_dialog.py -v`
Expected: FAIL (`ModuleNotFoundError: oeapp.ui.dialogs.unknown_revision`; restore tests fail on the missing `QApplication` name in `restore.py`).

- [ ] **Step 3: Implement the dialog**

Create `oeapp/ui/dialogs/unknown_revision.py`:

```python
"""Dialog shown when the database revision is unknown to this build."""

from typing import TYPE_CHECKING, Final

from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

if TYPE_CHECKING:
    from oeapp.exc import UnknownDatabaseRevision
    from oeapp.ui.main_window import MainWindow

#: FAQ entry that lists every known database version.
FAQ_URL: Final[str] = (
    "https://aenglisc-toolkit.readthedocs.io/en/latest/overview/faq.html"
    "#database-version-mismatch"
)


def describe_unknown_revision(revision: str, required_app_version: str | None) -> str:
    """
    Explain an unknown database revision to the user.

    Args:
        revision: The database's Alembic revision
        required_app_version: Application version that understands it, or None

    Returns:
        The message text

    """
    if required_app_version:
        return (
            "This database was last used by a newer version of Ænglisc Toolkit "
            f"(database revision {revision}).\n\n"
            f"Install application version {required_app_version} or later, then "
            "start the application again.\n\n"
            "Your data has not been changed."
        )
    return (
        f"Can't determine app version to use with db revision {revision}.\n\n"
        "See the FAQ entry 'Database version mismatch' for the list of known "
        f"versions: {FAQ_URL}\n\n"
        "Your data has not been changed."
    )


class UnknownRevisionDialog:
    """
    Dialog shown at startup when the database revision is unknown.

    Args:
        main_window: Main window instance
        error: The exception describing the revision and the version it needs

    """

    #: Dialog width
    DIALOG_WIDTH: Final[int] = 560
    #: Dialog height
    DIALOG_HEIGHT: Final[int] = 240

    def __init__(
        self, main_window: "MainWindow", error: "UnknownDatabaseRevision"
    ) -> None:
        """
        Initialize the instance.

        Args:
            main_window: Main window.
            error: Error.

        """
        #: Main window.
        self.main_window = main_window
        #: Error.
        self.error = error

    def build(self) -> None:
        """
        Build the dialog.
        """
        self.dialog = QDialog(self.main_window)
        self.dialog.setWindowTitle("Database Version Mismatch")
        self.dialog.setMinimumSize(self.DIALOG_WIDTH, self.DIALOG_HEIGHT)
        layout = QVBoxLayout(self.dialog)
        #: Message label.
        self.message_label = QLabel(
            describe_unknown_revision(
                self.error.revision, self.error.required_app_version
            )
        )
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        exit_button = QPushButton("Exit Application")
        exit_button.clicked.connect(self.dialog.accept)
        layout.addWidget(exit_button)

    def execute(self) -> None:
        """
        Execute the dialog.
        """
        self.build()
        self.dialog.exec()
```

In `oeapp/ui/dialogs/__init__.py` add `from .unknown_revision import UnknownRevisionDialog` next to the `MigrationFailureDialog` import and `"UnknownRevisionDialog",` to `__all__` (keep alphabetical order as the file does).

- [ ] **Step 4: Implement the Restore changes**

In `oeapp/ui/dialogs/restore.py`:

- Add `QApplication` to the `PySide6.QtWidgets` import list; add `from .unknown_revision import describe_unknown_revision`.
- Replace `restore_backup` with:

```python
    def restore_backup(self) -> None:
        """
        Restore the selected backup, then exit the application.

        A backup whose database revision this build does not know is refused
        before anything is overwritten.
        """
        selected_row = self.backup_table.currentRow()
        if selected_row < 0:
            self.main_window.messages.show_warning("Please select a backup to restore.")
            return
        time_item = self.backup_table.item(selected_row, 0)
        if not time_item:
            return
        backup_path = time_item.data(Qt.ItemDataRole.UserRole)
        if not backup_path:
            return

        backup_service = BackupService()
        metadata = backup_service.read_backup_metadata(Path(backup_path))
        if self._refuse_unknown_revision(metadata):
            return
        if not self._confirm_restore():
            return

        restored = backup_service.restore_backup(Path(backup_path))
        if restored is None:
            self.main_window.messages.show_error("Failed to restore backup.")
            return
        backup_migration = restored.get("migration_version")
        if backup_migration:
            QSettings().setValue("migration/last_working_version", backup_migration)
        self.main_window.messages.show_information(
            "Backup restored successfully. The application will now exit; "
            "start it again to continue.",
            title="Restore Complete",
        )
        self.dialog.accept()
        QApplication.quit()

    def _refuse_unknown_revision(self, metadata: dict[str, Any]) -> bool:
        """
        Refuse a backup whose database revision this build does not know.

        A backup with no recorded revision cannot be judged and is allowed.

        Args:
            metadata: The backup's sidecar metadata

        Returns:
            True if the restore was refused

        """
        revision = metadata.get("migration_version")
        if not revision or MigrationService().is_known_revision(revision):
            return False
        self.main_window.messages.show_warning(
            describe_unknown_revision(revision, metadata.get("application_version")),
            title="Cannot Restore Backup",
        )
        return True

    def _confirm_restore(self) -> bool:
        """
        Ask the user to confirm the restore.

        Returns:
            True if the user chose Yes

        """
        msg_box = QMessageBox(
            QMessageBox.Icon.Question,
            "Confirm Restore",
            "This will replace your current database with the selected backup.\n"
            "A backup of your current database will be created first, and the "
            "application will exit afterwards.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            self.dialog,
        )
        logo_pixmap = get_logo_pixmap(75)
        if logo_pixmap:
            msg_box.setIconPixmap(logo_pixmap)
        return msg_box.exec() == QMessageBox.StandardButton.Yes
```

Add `Any` to the `typing` import (`from typing import TYPE_CHECKING, Any, Final`). Remove `MigrationService` from the import only if no longer used (it is still used by `_refuse_unknown_revision`).

- [ ] **Step 5: Run tests and gates**

Run: `.venv/bin/pytest tests/test_unknown_revision_dialog.py tests/test_restore_dialog.py -q`
Expected: all PASS.
Run: `.venv/bin/ruff check oeapp/ui/dialogs tests/test_unknown_revision_dialog.py tests/test_restore_dialog.py && .venv/bin/mypy oeapp/ui/dialogs/restore.py oeapp/ui/dialogs/unknown_revision.py`
Expected: no new errors.

- [ ] **Step 6: Commit**

```bash
git add oeapp/ui/dialogs tests/test_unknown_revision_dialog.py tests/test_restore_dialog.py
git commit -m "feat: unknown-revision dialog; Restore refuses unknown backups and exits after restoring" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Startup handles `UnknownDatabaseRevision` (D6)

**Files:**
- Modify: `oeapp/ui/main_window.py` (`_handle_migrations`; imports)
- Test: `tests/test_main_window_migrations.py` (new)

**Interfaces:**
- Consumes: Task 8's `UnknownDatabaseRevision`; Task 9's `UnknownRevisionDialog`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_main_window_migrations.py`:

```python
"""MainWindow startup: an unknown database revision shows a dialog, then exits."""

from unittest.mock import MagicMock, patch

import pytest

from oeapp.exc import UnknownDatabaseRevision
from oeapp.ui.main_window import MainWindow


def test_unknown_revision_shows_the_dialog_then_exits():
    window = MagicMock()
    error = UnknownDatabaseRevision("zzz", "1.9.0")
    with (
        patch("oeapp.ui.main_window.MigrationService") as service_cls,
        patch("oeapp.ui.main_window.UnknownRevisionDialog") as dialog_cls,
    ):
        service_cls.return_value.migrate.side_effect = error
        with pytest.raises(SystemExit) as exit_info:
            MainWindow._handle_migrations(window)

    dialog_cls.assert_called_once_with(window, error)
    dialog_cls.return_value.execute.assert_called_once_with()
    assert exit_info.value.code == 1
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/pytest tests/test_main_window_migrations.py -v`
Expected: FAIL (`AttributeError: ... has no attribute 'UnknownRevisionDialog'`).

- [ ] **Step 3: Implement**

In `oeapp/ui/main_window.py`: change `from oeapp.exc import MigrationFailed` to `from oeapp.exc import MigrationFailed, UnknownDatabaseRevision`; add `UnknownRevisionDialog,` to the `from oeapp.ui.dialogs import (...)` list (alphabetical, after `SettingsDialog`); and in `_handle_migrations` add a clause before `except MigrationFailed`:

```python
        except UnknownDatabaseRevision as e:
            UnknownRevisionDialog(self, e).execute()
            sys.exit(1)
```

- [ ] **Step 4: Run tests and gates**

Run: `.venv/bin/pytest tests/test_main_window_migrations.py -q`
Expected: PASS.
Run: `.venv/bin/ruff check oeapp/ui/main_window.py tests/test_main_window_migrations.py && .venv/bin/mypy oeapp/ui/main_window.py`
Expected: no new errors.

- [ ] **Step 5: Commit**

```bash
git add oeapp/ui/main_window.py tests/test_main_window_migrations.py
git commit -m "feat: startup shows a dialog and exits on an unknown database revision" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 11: User-facing documentation (D6b)

**Files:**
- Modify: `doc/source/overview/faq.rst` (new section under Troubleshooting)
- Modify: `oeapp/help/topics/troubleshooting.md` (new section)
- Regenerate: `oeapp/help/assets/*` via `make help-assets`
- Modify: `doc/source/changelog.rst` (Unreleased entry)

- [ ] **Step 1: Add the FAQ entry**

In `doc/source/overview/faq.rst`, directly before the `Getting help` heading (after the existing Troubleshooting entry), insert:

```rst
Database version mismatch
^^^^^^^^^^^^^^^^^^^^^^^^^

If the app says it can't use your database, the database was last used by a
newer version of ``Ænglisc Toolkit`` than the one you are running. Your data
has not been changed. Install the version named in the message (or any newer
one) and start the app again.

If the message says it **can't determine** the version, find your database
revision (shown in the message) in the list below. Each line maps a database
revision to the application version that introduced it. If your revision is not
listed, install the newest release from the
`GitHub Releases page <https://github.com/cmalek/aenglisc_toolkit/releases>`_.

.. literalinclude:: ../../../oeapp/etc/migration_versions.json
   :language: json
```

- [ ] **Step 2: Add the in-app help section**

In `oeapp/help/topics/troubleshooting.md`, under `### Database Issues` (after the "Can't open project file" item), add:

```markdown
**Problem**: "Database Version Mismatch" at startup, or "Can't determine app version to use with db revision ..."

- **Solution**: Your database was last used by a newer version of the application than the one you are running. Your data has not been changed. Install the application version named in the message (or any newer release), then start the app again. If the message cannot name a version, install the newest release from the project's GitHub Releases page. The same check stops you from restoring a backup made by a newer version.
```

- [ ] **Step 3: Rebuild the help assets**

Run: `make help-assets 2>&1 | tail -5`
Expected: the `.html`/`.qch`/`.qhc` assets regenerate. Run `git status --short oeapp/help/assets` and confirm `troubleshooting.html` and the compiled help files changed.
Run: `.venv/bin/pytest tests -q -k "help" 2>&1 | tail -3`
Expected: PASS.

- [ ] **Step 4: Add the changelog entry**

At the top of `doc/source/changelog.rst`, directly under the `CHANGELOG` title block and above `1.0.1 (2026-09-06)`, insert:

```rst
Unreleased
----------

Fixes
^^^^^

- Backups and restores use SQLite's backup API, so pages still in the
  write-ahead log are no longer missed.
- A failed migration now restores the database that was backed up. Backup
  filenames no longer collide, and restoring a backup can no longer delete that
  backup when only one backup is kept.
- Migrations run with foreign keys off on the database that was opened, so a
  table rebuild cannot delete child rows.

Changed
^^^^^^^

- A migration now takes a backup before and after it runs; both appear in the
  Restore dialog. Restoring a backup exits the application.
- Starting the app on a database made by a newer version, or restoring such a
  backup, shows which version to install instead of failing later.
- Removed the unused ``migration/skip_until_version`` setting.
```

- [ ] **Step 5: Build the docs and check for new warnings**

Run: `.venv/bin/python -m sphinx -b html doc/source /private/tmp/claude-501/-Users-cmalek-src-workspace-aenglisc-toolkit/334627fe-28d2-4ad6-bf07-e0c4f14c054a/scratchpad/docs-html 2>&1 | grep -i "faq\|adr_0007\|changelog\|index" | head`
Expected: no warnings or errors mentioning `faq.rst`, `adr_0007_migration_backup_consolidation.rst`, `changelog.rst` or `architecture/index.rst`. Confirm the page contains the include: `grep -c "f38623b35077" .../docs-html/overview/faq.html` prints at least `1`.

- [ ] **Step 6: Commit**

```bash
git add doc oeapp/help
git commit -m "docs: database version mismatch FAQ, in-app help, and changelog" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Full verification and close-out

**Files:**
- Modify: `doc/source/architecture/adr_0007_migration_backup_consolidation.rst` (Status)

- [ ] **Step 1: Real execution of the migration path**

Run, using a throwaway copy of the baseline (no user data touched):

```bash
S=/private/tmp/claude-501/-Users-cmalek-src-workspace-aenglisc-toolkit/334627fe-28d2-4ad6-bf07-e0c4f14c054a/scratchpad
rm -rf $S/e2e && mkdir -p $S/e2e
AENGLISC_TOOLKIT_DB_PATH=$S/e2e/default.db AENGLISC_TOOLKIT_DATA_PATH=$S/e2e/data .venv/bin/python - <<'E'
import sqlite3, os
from pathlib import Path
from tests.migration_baseline import build_baseline_db
db = Path(os.environ["AENGLISC_TOOLKIT_DB_PATH"]); build_baseline_db(db)
from oeapp.services.migration import MigrationService
r = MigrationService().migrate()
print("result:", r)
print("backups:", sorted(p.name for p in (db.parent / "backups").glob("*")))
print("rows:", sqlite3.connect(db).execute("select count(*) from tokens").fetchone())
E
```

Expected: `result` shows `migration_version='7cd945e38aff'`; `backups` lists two `.db` and two `.json` files; `rows: (1,)`. Then simulate an unknown revision:

```bash
AENGLISC_TOOLKIT_DB_PATH=$S/e2e/default.db AENGLISC_TOOLKIT_DATA_PATH=$S/e2e/data .venv/bin/python - <<'E'
import sqlite3, os
db = os.environ["AENGLISC_TOOLKIT_DB_PATH"]
c = sqlite3.connect(db); c.execute("update alembic_version set version_num='zzzzzzzzzzzz'"); c.commit()
from oeapp.services.migration import MigrationService
from oeapp.exc import UnknownDatabaseRevision
try:
    MigrationService().migrate()
except UnknownDatabaseRevision as e:
    print("raised:", e.revision, e.required_app_version)
E
```

Expected: `raised: zzzzzzzzzzzz None` and no new files in `backups/`.

- [ ] **Step 2: Full suite, types, lint**

Run: `.venv/bin/pytest -q -p no:cacheprovider 2>&1 | tail -4`
Expected: PASS. Compare the count with Task 0 (new tests added, `TestMigrationSkipped` and the old flow classes removed, no failures).
Run: `.venv/bin/ruff check oeapp tests | tail -3; .venv/bin/mypy oeapp 2>&1 | tail -2`
Expected: no more errors than the Task 0 baseline.
Run: `make napoleon-gate; echo "exit $?"`
Expected: report the result separately; it is known to fail because its baseline is keyed by line number, so a failure here is not new evidence.

- [ ] **Step 3: Shuffled run for suite health**

Run: `.venv/bin/pytest -q -p no:cacheprovider -p no:randomly tests/test_migration_flow.py tests/test_unknown_revision.py tests/test_backup.py tests/test_restore_dialog.py 2>&1 | tail -3` then the same four files in reverse order (`tests/test_restore_dialog.py tests/test_backup.py tests/test_unknown_revision.py tests/test_migration_flow.py`).
Expected: both orders PASS (the flow tests clear `QSettings` in their fixture, so no order dependence).

- [ ] **Step 4: Update the knowledge graph**

Run: `graphify update .`
Expected: completes without error (AST-only).

- [ ] **Step 5: Accept the ADR**

In `doc/source/architecture/adr_0007_migration_backup_consolidation.rst` change `:Status: Proposed` to `:Status: Accepted`. Run the docs build from Task 11 Step 5 again and confirm no new warnings.

- [ ] **Step 6: Run the gauntlet**

Invoke the `gauntlet` skill. This change touches data loss (backup, restore, migration), so it is Tier 3: write the failure model from the Review Focus list, and map each line to the test that pins it (Task 3 `same_instant`, Task 7 `within_one_second`, Task 7 and Task 4 `one_retained`, Task 5 `keeps_every_row`, Task 8 `unresolved`, Task 9 `without_a_revision_is_not_refused`). Report the exact commands and counts in its evidence table.

- [ ] **Step 7: Commit**

```bash
git add doc/source/architecture/adr_0007_migration_backup_consolidation.rst graphify-out
git commit -m "docs: accept ADR 0007" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

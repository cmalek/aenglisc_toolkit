.. _adr_0007_migration_backup_consolidation:

=====================================================================
ADR 0007: One migration backup path and one source of migration state
=====================================================================

:Status: Accepted
:Date: 2026-10-03

Context
=======

Audit finding F6 (resolve order 7 of 12 in the 2026-09-13 architecture and
capability audit): ``MigrationService`` (``oeapp/services/migration.py``) mixes
Alembic, a version catalog and a second backup path.

- Two backup mechanisms exist. ``MigrationService`` copies the database to
  ``{db}.pre-migration`` with ``shutil.copy2``. ``BackupService.create_backup``
  writes a timestamped ``.db`` plus metadata JSON under ``backups/`` and prunes
  to the retention limit. The injected ``BackupService`` is used only by
  ``MigrationService.restore()``, which has no callers.
- The database runs in SQLite WAL mode. Both mechanisms copy only the main
  ``.db`` file, so pages still in the ``-wal`` file can be missing from the
  copy.
- ``oeapp/models/alembic/env.py`` takes the database path from
  ``get_project_db_path()`` and ignores the engine injected into
  ``MigrationService``. ``BackupService`` also hardcodes
  ``get_project_db_path()``. With a custom engine, inspection, upgrade, backup
  and restore can each act on a different file.
- ``has_pending_migrations`` consults three sources: the ``alembic_version``
  row, the Alembic head, and the ``migration_versions.json`` catalog. Nearly
  every branch reduces to ``db != head``. One branch returns pending when the
  database is already at head but the current application version maps to an
  older revision, which causes a backup and a no-op upgrade on every launch.
- ``alembic_version`` is read in two places
  (``MigrationService.db_migration_version`` and
  ``BackupService.get_current_migration_version``).
- ``should_abort`` compares revision IDs with ``<`` on random hex strings,
  which is meaningless. It is driven by the QSettings key
  ``migration/skip_until_version``, which nothing in the application writes.
  ``MainWindow._handle_migrations`` does not catch ``MigrationSkipped``.
- Every database from a public release carries ``alembic_version``, so "no
  ``alembic_version`` table" identifies a Fresh Database. Pre-release,
  unversioned databases are out of scope.
- Replaying the Alembic chain on an empty database fails at the first revision
  (``NoSuchTableError: annotations``), so a Fresh Database cannot be built by
  upgrading.
- ``BackupFileMetadataService`` has no callers.
- The application engine sets ``PRAGMA foreign_keys=ON`` and
  ``journal_mode=WAL`` on every connection (``oeapp/db.py``). ``env.py`` builds
  its own plain engine, so foreign keys are OFF during migrations today.
  Sixteen revisions use ``batch_alter_table``, and ``fix_check_constraints``
  drops and renames ``annotations`` directly. ``PRAGMA foreign_keys`` is a
  no-op inside a transaction (verified), so it only takes effect when issued
  before a connection's first ``BEGIN``.
- ``create_backup`` names files ``{stem}_{YYYY-MM-DD_HH-MM-SS}.db`` with
  one-second resolution and does not check for an existing file. A migration
  that fails fast takes the pre-migration copy and then, in
  ``restore_backup``, a safety copy of the failed database inside the same
  second: the safety copy overwrites the pre-migration copy and the restore
  then copies the broken database back over the live one.
- The Settings dialog allows ``num_backups`` as low as 1.
  ``BackupService.restore_backup`` calls ``create_backup()`` (which prunes)
  before copying, so with a low limit the safety copy can evict the backup
  being restored.
- ``restore_backup`` overwrites the live database with ``shutil.copy2``. In WAL
  mode a stale ``-wal`` or ``-shm`` beside the restored file can be replayed
  against the wrong main file, and the process holds open connections (the
  module-level ``_engine``, ``SessionLocal`` and the runtime session).
- Comparing application versions needs ``packaging.version``; ``packaging`` is
  not a declared dependency in ``pyproject.toml``.
- If the database revision is unknown to the code (a newer build was run
  first, or a Backup from a newer build was restored), ``db != head`` would call
  it pending and ``upgrade`` would fail with "Can't locate revision". The app
  is likely to misbehave even without a migration.
- ``migration_versions.json`` is bundled with the app and written in the same
  commit as each revision file, so it can only contain revisions the running
  code already knows. It keeps only the latest revision per application
  version (``MigrationMetadataService.update``). It therefore cannot name the
  version needed for a newer database.
- Every Backup sidecar JSON records ``migration_version`` and
  ``application_version``. ``extract_backup_metadata`` stamps
  ``application_version`` with ``__version__``, the *running* process. For a
  Pre-migration Backup that is the newly installed build, although the file
  holds the database as the previous build left it. Reading "downgrade to
  version X" from that sidecar would name the build that just failed.
- ``MainWindow`` writes QSettings ``app/current_version`` after every
  successful startup and nothing reads it. When a newly installed build starts,
  the value is still the previous build's, because the new build has not yet
  migrated.
- The Restore dialog loads that metadata but does not compare it with the
  code's revisions before overwriting the database
  (``oeapp/ui/dialogs/restore.py`` restores first and warns about a mismatch
  afterwards).
- ``create_backup`` calls ``set_last_backup_time``, and ``should_backup`` waits
  for the user's interval (default 720 minutes). A Pre-migration Backup is
  stamped with the pre-migration revision, so after a migration the newest
  Backup can describe the old revision for a whole interval. With
  ``num_backups=1`` it is the only one. A user who downgrades in that window
  has no sidecar naming the new revision.
- ``MainWindow.__init__`` runs ``_handle_migrations`` before
  ``_setup_backup_checking``, so a startup that exits writes no Backup.

- The card's scope IN covers backup consolidation, skip/abort, the empty-DB
  policy, dead code and the shared reader. The WAL-safe restore (D3) and the
  unknown-revision handling (D6, D6a, D6b) go beyond it. They are kept in this
  ADR by decision, because they share the Backup sidecar and Restore changes.

Decision
========

D1 — ``BackupService`` is the only backup collaborator
------------------------------------------------------

``MigrationService.migrate`` calls ``backup_service.create_backup()`` before a
Pending Migration and keeps the returned path. On failure it calls
``backup_service.restore_backup(path)`` and reads the version information for
``MigrationFailed`` from that backup's sidecar. ``backup_app_version`` is the
sidecar's ``application_version``, which D2a defines as the build that
maintained the database, so the failure dialog never tells the user to
"downgrade" to the build that just failed. The ``.pre-migration`` file and
its private create, restore, delete and path methods are removed, as is the
uncalled ``MigrationService.restore()``.

D2 — Backups use the SQLite backup API
--------------------------------------

``create_backup`` copies the database with ``sqlite3.Connection.backup()``
instead of ``shutil.copy2``, producing a consistent snapshot that includes
pages still in the WAL. ``extract_backup_metadata`` reads ``migration_version``
independently of the project listing, so a failure listing projects leaves the
revision in the sidecar instead of dropping it.

D2a — The sidecar records the build that maintained the database state
----------------------------------------------------------------------

``application_version`` means the application version that maintained the
database state the Backup captured, and ``created_by_version`` (new, always
``__version__``) records the build that wrote the file.

- Periodic, manual and post-migration Backups capture state the running build
  maintains, so ``application_version`` is ``__version__``.
- A Pre-migration Backup captures state the previous build left, so
  ``application_version`` is read from QSettings ``app/current_version`` before
  the migration runs, which is still the previous build's value. When it is
  unset (first run or a legacy install) the value is ``None`` and the failure
  dialog falls back to generic text.
- The safety copy of a failed database takes ``__version__``. It is a failed
  state, is never offered as a version to install, and cannot lower the
  minimum used in D6.

The QSettings key is a shared constant used by the writer in ``MainWindow`` and
the reader. QSettings is per-user and not tied to the database file, so a database selected
with ``AENGLISC_TOOLKIT_DB_PATH`` or a restored older database can disagree with
it. That is accepted: the supported failure case is a normal startup on the
default database. Storing the version inside the database would need a schema
migration and would still leave legacy databases without it.

D2b — Backup filenames are unique and never overwrite
------------------------------------------------------

``create_backup`` stamps filenames with microsecond precision
(``%Y-%m-%d_%H-%M-%S-%f``) and, if the target path or its sidecar still exists,
appends a counter until it finds a free name. An existing Backup is never
overwritten. This keeps the pre-migration, post-migration and safety copies
distinct even when a migration finishes or fails within a second. The
``{stem}_*.db`` glob used for listing and retention still matches.

D3 — Restore is WAL-safe
------------------------

``restore_backup`` also uses ``sqlite3.Connection.backup()`` (backup file into
the live database) instead of ``shutil.copy2``, so no stale ``-wal`` or
``-shm`` is replayed against a different main file. The backup API writes
through SQLite, so open pooled connections (verified with an idle reader on a
WAL database) do not need to be disposed first.

The real hazard is the running application continuing on a replaced database
with stale ORM state, which would write into the restored file. The Restore
dialog therefore exits the application after a successful restore, instead of
asking the user to restart, following the same dialog-then-exit model as a
failed migration. Nothing disposes the module-level ``oeapp.db`` engine or the
runtime session.

``restore_backup`` never prunes before the copy: it takes the safety copy of
the current database without pruning, copies the selected Backup over the
database, and only then prunes. This fixes the Restore dialog as well: with
``num_backups=1`` the safety copy can no longer evict the Backup being
restored. If the safety copy itself fails, the failure is logged and the
restore still proceeds, because a rollback must not depend on having room for
one more copy.

If the rollback restore itself fails, ``MigrationFailed`` carries
``restored=False`` plus the backup and database paths, and the failure dialog
says so and names the backup to restore by hand.

D4 — Pruning is deferred, and a successful migration takes a post-migration backup
------------------------------------------------------------------------------------

A Pre-migration Backup is an ordinary Backup: it lives in ``backups/``, is
listed in the Restore dialog and counts toward retention. Recovery must not
depend on the retention setting, so ``create_backup`` takes
``prune: bool = True`` and ``migrate`` passes ``prune=False`` for the
pre-migration copy. ``restore_backup`` always defers pruning (D3).

After a *successful* migration, ``migrate`` takes a **post-migration backup**
(``prune=False``), which carries the new revision and the running application
version. Without it the newest Backup would describe the old revision until the
user's interval elapses, and the sidecar lookup in D6 would have nothing to
find for the new revision. After success ``migrate`` then calls
``cleanup_old_backups()`` once. After a rollback it does not prune itself:
``restore_backup`` prunes after the copy, and nothing is pruned if the restore
fails. With ``num_backups=1`` the
retained Backup is the newest one: the post-migration backup after success, or
the failed-state safety copy after a rollback. The pre-migration copy cannot be
evicted before it is used; ``restore_backup`` reads its sidecar before pruning,
so the failure dialog keeps the previous build's version.

If the post-migration backup fails (for example the disk is full, since it is a
second full copy), ``migrate`` logs the failure and continues. The migration has
committed, so it is neither reported as ``MigrationFailed`` nor rolled back.

A Fresh Database takes neither backup.

D5 — Pending means ``db revision != Alembic head``, for known revisions
-----------------------------------------------------------------------

``has_pending_migrations`` compares the database revision with
``script.get_current_head()`` only (the current code diverges in the
``expected_revisions`` branch of ``has_pending_migrations``). A Fresh Database
never takes a backup, because there is nothing to protect. "Fresh" means the
database has no ``alembic_version`` table. The
``migration_versions.json`` catalog stays for project import/export version
gating (``get_min_version_for_migration``) and is no longer read by
``MigrationService``.

D6 — An unknown database revision stops startup with a dialog
-------------------------------------------------------------

If the database revision is not in the Alembic script directory,
``MigrationService`` raises ``UnknownDatabaseRevision(revision,
required_app_version)`` before any backup or upgrade. Nothing is backed up or
restored, because nothing has changed. ``MainWindow`` catches it in the same way
as ``MigrationFailed``: a dialog with instructions, then ``sys.exit(1)`` once the
user acknowledges. The existing exit behaviour is unchanged.

``required_app_version`` is resolved in this order, first hit wins:

1. ``migration_versions.json`` (``get_min_version_for_migration``).
2. Backup sidecars: among sidecars whose ``migration_version`` equals the
   database revision, the smallest ``application_version`` (compared with
   ``packaging.version.Version``, added as an explicit dependency with
   ``uv add packaging``, not as strings). Any such build had the database open at that
   revision, so it understands it, and the minimum gives the tightest answer.
   The post-migration backup from D4 guarantees one exists whenever the newer
   build reached that revision.
3. Unresolved (``None``).

The dialog says "Install application version X or later" when resolved. When
unresolved it says "Can't determine app version to use with db revision
<revision>" and links to the FAQ entry that lists every known revision.
Corrupt or hand-edited revisions land in the unresolved case. The dialog is a
new small class beside ``MigrationFailureDialog``, which is not reused because
its text claims a backup was restored.

D6a — The Restore dialog refuses a Backup with an unknown revision
------------------------------------------------------------------

Before overwriting the database, the Restore dialog compares the selected
backup's ``migration_version`` with the code's revisions. If it is unknown, it
refuses and shows the backup's ``application_version`` as the version to
install. The database is not touched, so the user is not left with a file the
application cannot open. A Backup whose ``migration_version`` is ``None`` (a
missing or corrupt sidecar, a sidecar from before the field existed, or the
fallback metadata written when extraction failed) cannot be judged and is not
refused; a restored file with an unknown revision still reaches the D6 dialog on
the next start.

D6b — Documentation
-------------------

``doc/source/overview/faq.rst`` gains an entry (with a stable label the dialog
links to) that explains the message and ``literalinclude``\ s
``oeapp/etc/migration_versions.json`` (``:language: json``), so users can look
up their revision. An entry in the in-app Troubleshooting help (``oeapp.help``)
covers the same ground. Because the catalog keeps only the latest revision per
application version, a revision between releases can be missing from the list,
and the entry says to use the newest version in that case.

D7 — Fresh Database policy: ``create_all`` and stamp head
---------------------------------------------------------

Kept as the policy, because the chain cannot be replayed from an empty
database. The claim that the ``create_all`` schema equals the head schema was
checked against a real release baseline: a database built by the ``1.0.0`` tag's
models and stamped ``f38623b35077`` upgrades to head (``7cd945e38aff``) with no
column or index drift against ``Base.metadata.create_all``, and seeded rows
survive. That baseline becomes a committed fixture
(``tests/fixtures/schema_1_0_0.sql``), and a test repeats the comparison so
future model or migration changes that drift fail. When a later release adds a
revision, the test is extended by the maintainer, not by replaying older
history.

D8 — The injected engine is authoritative, with foreign keys OFF
----------------------------------------------------------------

``MigrationService`` passes its connection to Alembic through
``config.attributes["connection"]``. ``env.py`` uses that connection when
present and falls back to ``get_project_db_path()`` otherwise. Because the
application engine enforces foreign keys, ``MigrationService`` opens a fresh
connection, issues ``PRAGMA foreign_keys=OFF`` as its first statement before any
``BEGIN`` (it is a no-op inside a transaction), hands that connection to
Alembic, and does not rely on the connect-time listener that turns it ON. This
matches what ``env.py`` does today and stops batch table recreation from
cascade-deleting child rows. A test asserts the pragma reads ``0`` while
migrations run. A rehearsal test upgrades the populated ``1.0.0`` baseline and asserts row
counts are unchanged. ``BackupService`` takes an optional ``db_path``,
which ``MigrationService`` derives from ``engine.url.database``, so backup,
upgrade and restore act on one file.

D9 — Skip/abort is deleted
--------------------------

``should_abort``, ``migrate(skip_until_version)``, the QSettings read in
``MainWindow._handle_migrations`` and ``MigrationSkipped`` (with its test in
``tests/test_exc.py``) are removed. The feature is unreachable and its
comparison is wrong. A stale ``migration/skip_until_version`` key on user
machines is harmless and is left alone.

D10 — One ``alembic_version`` reader in ``oeapp.db``; dead code removed
-----------------------------------------------------------------------

A single ``read_alembic_revision(engine)`` function in ``oeapp/db.py`` serves
both services, so neither service depends on the other.
``BackupFileMetadataService`` is deleted.

Consequences
============

- A failed migration restores the file that was backed up, the backup is a
  consistent snapshot in WAL mode, and recovery does not depend on the
  retention setting.
- Migration runs consume retention slots, applied after the migration settles,
  so a user with ``num_backups`` set low can lose older backups sooner.
- The pre-migration backup becomes a durable recovery point that the user can
  see and restore, instead of a hidden file deleted on success.
- ``create_backup`` and ``restore_backup`` gain a ``prune`` argument and change
  copy mechanism, which affects the Restore dialog and the periodic backup
  timer in ``MainWindow``.
- ``env.py`` gains a connection-or-fallback branch. Command-line Alembic runs
  (``bin/create_migration.py``) take the fallback, which is unchanged, but this
  has to be verified by a test.
- ``MigrationFailed.backup_app_version`` carries the previous build's version
  (from the Pre-migration Backup's sidecar) instead of always being ``None``.
- Sidecars gain a ``created_by_version`` field. Older sidecars lack it, and
  readers treat it as optional.
- A successful restore now exits the application. Previously the user could
  keep working after the "please restart" message.
- Startup gains a second dialog-and-exit path (``UnknownDatabaseRevision``),
  and the Restore dialog gains a refusal path.
- A successful migration writes two Backups (pre and post), so each migration
  uses two retention slots until the single prune at the end.
- The sparse catalog means resolution step 1 only helps for catalogs shipped
  with a newer build (the bundled catalog lists only revisions this build
  already knows); step 2 carries the common case. Backing every revision in the catalog would need git archaeology
  and is out of scope.
- Removing skip/abort drops the only guard against migrating past a chosen
  revision. If that is wanted later it needs a real setting and a script-graph
  comparison.
- D7 and D8 rely on the committed ``1.0.0`` baseline fixture. Tests come first
  and must include: failure rollback against a temp-path engine, a
  ``num_backups=1`` rollback, restore over a WAL database with leftover
  sidecars, a populated-database upgrade that checks row counts,
  a Restore that exits the application and does not leave it running on the
  replaced database, two backups created within the same second that stay distinct, a
  rollback within one second that restores the original database, a Restore
  with ``num_backups=1`` that restores the selected Backup, a post-migration
  backup that fails and leaves the migration committed, a Backup with
  ``migration_version=None`` that is not refused, a Pre-migration Backup whose sidecar carries the previous build's version
  and not ``__version__``, a failure dialog that never names the running
  version, a migration with ``num_backups=1`` that leaves a sidecar carrying the new
  revision and the current application version, an unknown-revision start
  (resolved from the catalog, resolved from a sidecar, choosing the minimum
  version among several, and unresolved), a Restore of a Backup with an unknown revision, and the ``create_all`` versus upgrade schema
  comparison.

Alternatives considered
=======================

- **Keep both backup paths, share only the file copy.** Leaves two retention
  and metadata models and two places to get the path wrong.
- **Stamp every Backup with ``__version__``.** Simplest, but a Pre-migration
  Backup would name the build that is about to fail, which makes the failure
  dialog and the Restore mismatch message wrong.
- **Store the application version inside the database.** Self-describing and
  independent of QSettings, but needs a schema migration, and every existing
  database lacks it until it has been opened by a build that writes it.
- **Dispose the global engine and reload the UI after a restore.** Keeps the
  application running, but needs a reload of project state across 100+
  ``app_context.session`` call sites and is risky. Exiting is simpler and the
  dialog already asks for a restart.
- **Skip the post-migration backup and rely on the periodic one.** A recent
  periodic Backup suppresses the next one for the whole interval, so whether the
  new revision gets a sidecar is not deterministic.
- **Treat an unknown revision as pending and let rollback handle it.** Data is
  preserved but the user sees a generic migration failure with no guidance. The
  user asked for a specific "install version X" message instead.
- **A non-pruned, exempt Pre-migration Backup slot.** Avoids evicting user
  backups but adds a second backup concept and a second cleanup policy. D4
  keeps one concept and defers pruning instead.
- **Keep skip/abort and compare via the Alembic script graph.** Builds a
  feature around a setting no user can reach.
- **Rewrite the baseline migration so an empty database can replay upgrades.**
  A larger, riskier change than this finding warrants; ``create_all`` and stamp
  head already works.

Related
=======

- :ref:`adr_0006_copied_annotation` (the previous finding in the audit order).
- Trello card F6, "MigrationService mixes Alembic, version catalog, and a
  second backup path".

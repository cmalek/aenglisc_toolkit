.. _adr_0015_off_ui_thread:

==========================================================
ADR 0015: Run Tectonic and database jobs off the UI thread
==========================================================

:Status: Accepted
:Date: 2026-11-16

Context
=======

Full Translation PDF export called ``subprocess.run`` on the UI thread
inside ``compile_latex_with_tectonic``. A slow or hung Tectonic compile
froze the window. The same thread also wrote DOCX, project JSON, reading
text, new-project ingest, append, and backups. Those calls held the UI
session's SQLite transaction. SQLite then returned ``database is locked``
to a second writer, or the UI thread waited on ``busy_timeout``.

:ref:`adr_0011_runtime_session_freeze` keeps one registered runtime
session on ``_RUNTIME_STATE``. ``get_runtime_session`` returns it.
Sessions are not safe to share across threads. The engine is created with
``check_same_thread=False`` and WAL. A second registered session was
rejected by that ADR. The workers below open a session that is not
registered.

:ref:`adr_0013_pdf_glossary_aggregation` left the Tectonic call on the UI
thread and pointed at the backlog card for moving it. Replacing Tectonic
stays out of scope. Migration backups in ``MigrationService`` stay on the
calling thread. This decision covers the UI paths that were freezing the
window.

Decision
========

D1 — Tectonic compiles in a ``QProcess``
----------------------------------------

``PdfExportJob`` owns a ``QProcess``. ``tectonic_compile_command`` passes
an absolute program path from ``Path.resolve``. The GUI thread prepares
the work directory with ``prepare_side_by_side_tex`` and finalizes the
PDF after the process exits. The compile itself is the ``QProcess``.

``finished`` is ``Signal(bool, int, str, str)``: cancelled, exit code,
stdout, and stderr. Exit code ``-1`` means the program failed to start.
``errorOccurred(Crashed)`` is ignored because ``finished`` also fires.
``FailedToStart`` reports immediately. ``_report`` emits ``finished``
once. Slots are methods, not lambdas.

Cancel sets a flag and calls ``QProcess.kill``. Closing the Full
Translation window disconnects ``finished``, cancels, and
``wait_until_finished`` (five seconds) before it deletes the work
directory and destroys the window. That wait is what keeps the
``QProcess`` destructor from blocking the GUI thread inside
``Destroyed while process``.

``compile_latex_with_tectonic`` stays synchronous and accepts
``timeout``. ``FullTranslationPDFExporter`` takes an optional
``compile_pdf`` callable so tests can inject a fake. When that argument
is omitted, the exporter looks up ``compile_latex_with_tectonic`` at
call time.

D2 — Database jobs use a private session on the UI engine
---------------------------------------------------------

``SessionRunnable`` runs on ``QThreadPool.globalInstance``.
``setAutoDelete(False)`` keeps the runnable alive until the UI slot has
run. ``SessionTaskSignals`` is a ``QObject`` parented to a GUI object, so
the cross-thread connection is queued.

The runnable opens ``Session(bind=engine)`` on the engine behind the UI
session. ``thread_runtime_session`` installs that session on a
``threading.local``. ``get_runtime_session`` returns the override on
that thread and the registered session everywhere else. The GUI thread
does not set the override. The worker commits, then closes its session,
before the queued slot runs. The slot therefore receives plain values
(an id, a bool, a ``Path``), and the GUI reloads by id and calls
``expire_all`` after a write.

The worker callable constructs ``ProjectImporter``, ``DOCXExporter``,
``ReadingTextExporter``, and ``WyrdcraeftIngestService``. It does not
receive ORM instances from the UI session. ``BackupService`` stays a
``QObject`` on the GUI thread. The worker calls ``create_backup`` on it.
``_open_settings`` uses the service's ``QSettings`` on the service's own
thread and a fresh ``QSettings`` after ``sync`` on any other thread.

``run_session_task`` shows a ``WindowModal`` ``QProgressDialog`` with no
cancel button and waits in a nested ``QEventLoop``. The menu action or
test still receives the return value or the exception. The event loop
keeps running, so the window can paint. Input to that window and its
parent is blocked until the job finishes.

Automatic backup uses ``start_session_task`` and does not show a dialog.
The status bar says "Backing up…". ``delete_project`` still waits for its
pre-delete backup through ``run_session_task``.

D3 — Releasing the SQLite lock does not save unsaved edits
----------------------------------------------------------

The UI session often holds a transaction after a read. The worker cannot
update until that transaction ends. ``_release_ui_lock`` copies dirty
column and relationship history, new objects, and deleted objects, rolls
the UI session back, then writes those values back onto the identity map
with ``setattr``, ``add``, and ``delete``.

The rollback is not a commit. A commit would persist edits the user had
not saved, including a backup started by the five-minute timer while
autosave is off. SQLAlchemy 2.1 ``Session`` has no
``expire_on_rollback`` attribute. Rollback expires the instances, and the
restore assigns the captured values again. Those values stay dirty and
are not flushed.

D4 — One database writer at a time, and database jobs do not cancel
-------------------------------------------------------------------

``push_ui_db_busy`` and ``pop_ui_db_busy`` count in-flight database jobs.
Only the GUI thread changes the count. ``start_session_task`` waits until
the count is zero, then increments it. The queued success and failure
slots decrement it. ``AutosaveService._save`` rearms its timer while the
count is positive. ``MainWindow._check_backup`` returns while the count
is positive or an automatic backup is already running.

Database jobs have no cancel control. ``QRunnable`` has no
``requestInterruption``. Closing the dialog while the worker still writes
would let the UI session and the worker session use the database
together, which is the lock this decision removes. A hung database job
leaves the modal up until the worker returns. PDF cancel is the
``QProcess.kill`` in D1. That process is not a SQLAlchemy session.

D5 — The freeze allowlist records the new lookups
-------------------------------------------------

``tests/test_runtime_session_freeze.py`` records the
``get_runtime_session`` calls this change added, including
``_worker_engine``, ``prepare_side_by_side_tex``,
``MainWindowActions._run_busy``, ``_write_reading_text``, and the nested
callables in the new-project and append dialogs. The test still checks
that the dict matches the tree. It still cannot see why a count moved.
``set_runtime_session`` is still the only way to register the process
session. ``SessionLocal()`` inside ``get_runtime_session`` is still the
only product creation of that session.

Consequences
============

- A hung Tectonic compile no longer freezes the GUI thread. The user can
  cancel it, and a failure shows the compiler log. Closing the Full
  Translation window kills the process and waits up to five seconds. If
  the process is still running after that wait, destroying the
  ``QProcess`` can still block.
- DOCX export, project import and export, reading-text export, Backup
  Now, delete-project's pre-delete backup, new-project ingest, and append
  wait on a progress dialog. The application paints. Those windows do not
  take input until the job finishes. Help text says that.
- Automatic backup does not show a dialog and does not write unsaved
  edits. It waits while another database job holds the counter.
- The worker and the UI thread do not share a session or a ``QSettings``
  instance. A return value that is an ORM object is unusable after the
  worker closes its session.
- :ref:`adr_0011_runtime_session_freeze` still has one registered runtime
  session. The thread-local override is how a worker sees a different
  session without ``set_runtime_session``. F8 is not rewritten.
- Migration backups stay synchronous.
- The synchronous Tectonic helper remains for tests and for a caller that
  passes ``timeout``.

Alternatives considered
=======================

- **Keep** ``subprocess.run`` **and only add** ``timeout``. Rejected as
  the product fix. The timeout is the stop-gap on the synchronous helper.
  The window path uses ``QProcess`` so cancel and paint work during the
  compile.
- **Register a second runtime session with** ``set_runtime_session``.
  Rejected. ADR 0011 keeps one registered session. The worker session is
  thread-local and closed before the UI slot runs.
- **Commit the UI session before the worker starts.** Rejected. That
  releases the SQLite lock and also writes every dirty object, including
  from the automatic backup timer when the user has not saved.
- **A cancel button on database jobs.** Rejected. The worker would keep
  writing after the dialog closed. Two sessions would use the database
  again.
- **Move migration backups onto the pool.** Rejected for this change.
  ``MigrationService`` calls ``create_backup`` on the thread that is
  migrating.

Related
=======

- :ref:`adr_0011_runtime_session_freeze`, D1. This ADR does not register
  a second session.
- :ref:`adr_0013_pdf_glossary_aggregation`, D3. That ADR left the compile
  on the UI thread. D1 of this ADR moves it.
- Tectonic through ``QProcess``: https://trello.com/c/yDN152tV
- DOCX, import, export, and backup on the pool:
  https://trello.com/c/v4DxIqrd
- F8, the one registered session: https://trello.com/c/RqmuEu67

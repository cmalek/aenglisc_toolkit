=========
Updating
=========

Getting a new version
=======================

``Ænglisc Toolkit`` has no auto-update mechanism yet — update the same way
you installed it:

- **Packaged app (macOS)**: download the latest ``.dmg`` from the
  `Releases page <https://github.com/cmalek/aenglisc_toolkit/releases>`_ and
  drag it into **Applications** again, replacing the old copy. See
  :doc:`/overview/installation`.
- **From source**: ``git pull`` the latest changes, then run ``uv sync`` to
  pick up any dependency changes, before launching the app again.

Your database (all projects, settings, and backups) lives outside the
application bundle, so updating never touches your data directly — only
the database migration step described below does.

Database migrations
=====================

Each release may include schema changes to the local database (adding
fields, tables, etc.). These are handled as **migrations**, which run
automatically the next time you launch the application after an update — no
separate command required.

What happens on startup
--------------------------

1. **Check for pending migrations.** If the database is already at the
   current version, the application starts normally and nothing else in
   this section applies.
2. **Backup first.** Before applying any migration, the application makes a
   full backup of the database (the same kind of backup described in
   :doc:`/overview/backups`).
3. **Apply the migrations.**
4. **On success**, the backup is discarded and the application starts
   normally.
5. **On failure**, the application:

   - Restores the database from the backup taken in step 2, so your data is
     back exactly as it was before the update.
   - Shows a **Migration Failed** dialog with the full exception trace, and
     buttons to **Save Stack Trace** to a file or **Copy to Clipboard**.
     Please attach this trace when
     `filing an issue <https://github.com/cmalek/aenglisc_toolkit/issues>`_
     so the migration can be fixed.
   - Exits the application once you close the dialog. Since your database
     was restored to its pre-migration state, it's safe to keep using the
     previous version of the application (the dialog tells you which
     application version the restored backup was made with) until a fix is
     available.

Because the restore happens automatically before you ever see the failure
dialog, a failed migration cannot leave your database partially migrated or
corrupted — you either end up fully on the new version, or fully back on
the old one.

.. important::

  If the update fails, look at the **Migration Failed** dialog for the full exception trace -- this will tell you the version of the application that was running when the backup was made.  You can then download that version from the `Releases page <https://github.com/cmalek/aenglisc_toolkit/releases>`_ and install it manually to get back to a working version of the application.
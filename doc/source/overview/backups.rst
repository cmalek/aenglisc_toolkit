=======
Backups
=======

``Ænglisc Toolkit`` protects your work at two levels: whole-database
backups (all projects, automatic and manual), and per-project export/import
files you can use to move a single project between machines or keep as an
independent archive.

Database backups
=================

Automatic backups
------------------

Every 5 minutes, the application checks whether it's time to make an
automatic backup of the whole database. A backup is taken if the configured
interval has elapsed since the last one (or if no backup has been made yet).

- **How often**: every 12 hours (720 minutes) by default. Change this under
  **Preferences → Backup interval (minutes)**.
- **How many are kept**: the 5 most recent automatic/manual backups are
  kept; older ones are deleted automatically. Change this under
  **Preferences → Number of backups to keep**.

Backups are also taken automatically before risky operations, such as
deleting a project or restoring another backup, so those actions can't
destroy data that wasn't already backed up.

Manual backups
---------------

Use **Tools → Backup Now** to create a backup immediately, regardless of
the automatic schedule. A status bar message confirms when the backup has
been created, and it counts toward the same retention limit as automatic
backups.

Listing existing backups
--------------------------

Use **Tools → Backups...** to open a table of every backup currently on
disk, showing its date/time, file size, the database migration version and
application version it was made with, and the number of projects and tokens
it contains.

Restoring a backup
--------------------

Use **Tools → Restore...** (or the same list from **Backups...**) to pick a
backup and restore it. Restoring:

1. Takes a backup of the *current* database first, so restoring is itself
   undoable.
2. Copies the selected backup file over the current database.
3. Warns you if the backup's migration version doesn't match the version
   the running application expects, since restoring an incompatible backup
   can cause SQL errors.

The application must be restarted after a restore completes.

Per-project backups
====================

Use **Project → Export...** and **Project → Import...** to save or load a
single project as a standalone file, independent of the automatic/manual
database backups above. This is useful for archiving a finished project,
sharing one project with someone else, or moving a project between
machines without copying the whole database.

Export writes a JSON file (optionally gzip-compressed, ``.json.gz``)
containing the project's metadata, its full chapter/section/paragraph
hierarchy, every sentence with its tokens and annotations, and any
project-scoped remembered annotations. The file also records the database
migration version it was exported from, so importing into a newer version
of the application can transform older data forward automatically. If a
project with the same name already exists, the import gives the new
project a distinguishing name (e.g. ``Project (1)``) rather than
overwriting it.

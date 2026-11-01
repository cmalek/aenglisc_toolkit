CHANGELOG
=========

1.1.0 (2026-10-04)
------------------

Enhancements
^^^^^^^^^^^^

- Added a **Project > Export** submenu with three items: **Project file...**
  (JSON or ``.json.gz``, importable), **Old English...** and **Translation...**
  (plain ``.txt`` reading copies with official titles, verse indent and a line
  number every five verse lines, no notes or annotations). The reading-text
  items are disabled until there is text to export, and importing one of those
  ``.txt`` files now fails with an explanation instead of a confusing error.
- Highlighting is now layered: the highlighting mode, the selected token or
  span, and search matches are independent, so changing the mode no longer
  clears the selected span, and search matches always show on top.
- Pasting a copied annotation onto another token now gives the target a fresh
  updated time instead of the source's timestamps.
- Copying an annotation that cannot be validated is refused with "Cannot copy
  annotation: invalid data" and your previous copy is kept; the details are
  written to the application log (**Window > View Logs**).
- Starting the app on a database made by a newer version, or restoring such a
  backup, now tells you which version to install (or that it can't tell, with a
  link to the FAQ) instead of failing later. The FAQ has a new "Database
  version mismatch" entry.

Fixes
^^^^^

- Annotation fields now have one label and one order everywhere. The sidebar
  shows "Class", "Type", "Degree" and so on, matching the annotation form, and
  a value that is unset or unrecognised shows ``?``.
- Annotation presets store field codes instead of labels. Older presets and
  imports that used label forms for declension and verb class are repaired
  automatically, and presets can no longer save an invalid value for them.
- Corrected the annotation guide to match the annotation form: Governed Case
  lists Instrumental, and the Conjunction **Type** field (coordinating or
  subordinating) is documented.
- Fixed token-id search being lost when a sentence card first renders, and
  highlight colours not updating for every layer when the light/dark theme is
  switched while the app is running.
- Fixed verse-line numbering in the reading-text exports: lines are counted
  from the Old English text, a number appears whenever a stanza crosses a
  multiple of five, and the count restarts after prose.
- Backups and restores use SQLite's backup API, so pages still in the
  write-ahead log are no longer missed.
- A failed migration now restores the database that was backed up. Backup
  filenames no longer collide, and restoring a backup can no longer delete a
  backup before it is restored.
- Restoring a backup is refused when its database revision is not one this
  version knows, and an empty or missing backup file can no longer overwrite
  your database.
- Migrations run with foreign keys off on the database that was opened, so a
  table rebuild cannot delete child rows.
- When a failed migration cannot be rolled back automatically, the failure
  dialog now says so and names the backup to restore by hand, instead of
  claiming the database was restored.

Changed
^^^^^^^

- Switch to direnv from autoenv for environment management.
- Added the `make backup` and `make restore` commands to the Makefile, which backup your entire application data to a tar.gz file in the current directory and restore it respectively.
- A migration now takes a backup before and after it runs; both appear in the
  Restore dialog. Restoring a backup exits the application.
- Removed the unused ``migration/skip_until_version`` setting.
- Reworked the application internals toward Qt models and controllers (token
  table, search, project workspace, sentence cards). There are no intended
  behaviour changes.
- Docs: the architecture section now records ADRs 0003 to 0007, screenshots were
  retaken, and readthedocs installs only the documentation dependencies.

1.0.1 (2026-09-06)
------------------

Enhancements
^^^^^^^^^^^^

- Published the full Sphinx user's guide for readthedocs.org.

Fixes
^^^^^

- Fixed the macOS app bundle not including the Qt theme files, which
  silently left dark/light themes unavailable.
- Reduced macOS app startup time by switching the PyInstaller build from
  onefile to onedir mode, which previously required re-extracting the
  entire app on every launch.
- Fixed missing ``.ttf`` font files in the macOS PyInstaller bundle.
- Fixed dark text being used for OE token selection highlighting in dark
  mode.
- Fixed the Bosworth-Toller dictionary icon not following the light/dark
  theme.

Changed
^^^^^^^

- Renamed the ``OE_ANNOTATOR_*`` environment variables to
  ``AENGLISC_TOOLKIT_*`` (affects ``AENGLISC_TOOLKIT_TECTONIC_BINARY`` and
  ``AENGLISC_TOOLKIT_TECTONIC_BUNDLE``). Update any scripts or environment
  configuration that set the old names.
- Renamed the application log file from ``oe_annotator.log.json`` to
  ``aenglisc_toolkit.log.json``.

1.0.0 (2026-09-04)
------------------

Enhancements
^^^^^^^^^^^^

- Initial release.

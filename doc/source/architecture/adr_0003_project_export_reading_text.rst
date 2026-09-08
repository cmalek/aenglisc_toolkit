.. _adr_0003_project_export_reading_text:

=================================================================
ADR 0003: Project Export menu splits JSON from reading-text files
=================================================================

:Status: Accepted
:Date: 2026-09-07

Context
=======

``Project → Export...`` writes one **Project Export**: JSON (optionally
gzip) of a project's complete data — sentences, tokens, annotations, and
notes. That file is for Toolkit-to-Toolkit sharing and for archiving a
single project. It is not a **Backup** (whole-database recovery) and it is
not a reading copy of the text.

Translators also need to share **Old English Text** and **Modern English
Translation** with people who do not use the app — paste, email, and other
plain interchange. Formatted side-by-side reading copies already exist as
File-menu DOCX and Full Translation PDF. Those remain the formats for
people who want both languages together on one page.

Calling the JSON item "Combined" would blur Project Export with reading
text. Dumping ``[...]`` placeholders from the Modern English column would
leak editor chrome into a file meant for sharing.

Decision
========

Replace the single ``Export...`` action with one ``Export`` submenu that
has three items (not three nested submenus): **Project file...**, **Old
English...**, **Translation...**.

Parent label is ``&Export`` (no ellipsis). Children: ``&Project file...``,
``&Old English...``, ``&Translation...``. No new keyboard shortcut;
``Ctrl+E`` stays on File-menu DOCX. Items stay enabled at rest unless the
empty-project / empty-translation rules below disable them. No-project is
still the existing warning after invoke, matching JSON/DOCX.

Save before any of the three writes, so dirty sentence-card text is in the
file. Then use the same save-dialog contract as JSON/DOCX: cancel writes
nothing; overwrite uses native ``getSaveFileName`` confirm; success/error
toasts follow the JSON export pattern.

Project file
------------

**Project file...** is the existing Project Export JSON dialog (gzip
unchanged). Default name: sanitized project name with ``.json``. Dialog
title stays ``Export Project``.

Old English
-----------

**Old English...** writes a UTF-8 ``.txt`` **Old English Text Export**.
Default name: ``{name}-oe.txt``. Dialog title: ``Export Old English Text``.
Filter: ``Text Files (*.txt);;All Files (*)``. Force ``.txt`` if the user
omits the extension.

Disable this item (and Translation) when the project has no sentences.

Translation
-----------

**Translation...** writes a UTF-8 ``.txt`` **Translation Export**. Default
name: ``{name}-translation.txt``. Dialog title: ``Export Translation``.
Same ``.txt`` filter and extension enforcement as Old English.

Disable this item when the project has no sentences **or** no Modern
English Translation on any sentence. Empty translations stay empty — no
``[...]``.

How text is built
-----------------

A dedicated reading-text service builds both strings from persisted
``Project.sentences`` after save. It is **not** used by Full Translation:
that window keeps notes, annotation markup, and its own QTextCursor
renderers. Do not scrape those widgets. Do not claim live parity with the
window as an acceptance test.

Both ``.txt`` files exclude notes and annotation markup. They include
official chapter/section titles (the Full Translation visibility rule:
auto-generated titles such as ingest ``Lines 1-25`` are omitted), sentence
gaps, and four-space verse indent.

Verse line numbers in the ``.txt`` files are an export convention, not a
dump of stored ``verse_line_end``: print a number every five verse lines.
If the last stanza has fewer than five lines, print no number there. On
Translation Export, do not print a verse number on a stanza whose Modern
English is empty.

Do not treat either ``.txt`` as importable Project Export. Project Import
must reject non-JSON and name the three export kinds so a collaborator who
picked a reading-text file is not told the project is corrupt.

Empty project / blank translation: do not write an empty file; the menu
items are disabled instead.

Alternatives considered
=======================

- **Label "Combined"** for JSON. Rejected: Combined does not say
  Toolkit interchange; Project Export already names that payload.
- **Label "Backup"** for JSON. Rejected: Backup is database-wide recovery.
- **One shared layout owner called by Full Translation and export.**
  Rejected: the window must keep notes and annotation rendering; the
  reading-text service stays export-only.
- **Translation ``.txt`` using Old English column rules** (token walk, note
  digits). Rejected: notes live on Old English surfaces; Modern English
  already has its own column layout.
- **Keep ``[...]``** so Translation export matches the window
  byte-for-byte. Rejected: the file is for sharing, not dumping UI
  placeholders.
- **Emit stored** ``verse_line_end`` **so the file matches the window.**
  Rejected: reading-text files follow the common OE-poetry every-five
  numbering, including no number on a short last stanza.
- **One paired OE+ME artifact for outsiders.** Rejected: these items are
  single-language files; side-by-side sharing is PDF or DOCX.
- **Notes-on reading-text variant.** Rejected for this change: share copies
  are clean text.
- **Header with Source / Project Notes.** Rejected for this change.
- **Omit chapter/section titles.** Rejected: official titles are part of
  the reading layout; auto titles stay hidden.
- **Three sibling menu items** or **one Export dialog with a format
  picker**. Rejected: one ``Export`` submenu with three items is the
  smallest match for "three choices under Export."
- **Default all three to** ``Name.ext``. Rejected: two ``.txt`` exports in
  the same folder would clobber each other.

Consequences
============

- Project Export stays JSON-only and importable. Reading-text files are
  share copies, not round-trip project files.
- Full Translation layout and reading-text layout **will diverge** (notes,
  placeholders, verse numbering). That is intentional.
- ``.txt`` owns paste/email/plain interchange. DOCX/PDF own formatted
  reading copies.
- Glossary distinguishes Project Export, Old English Text Export, and
  Translation Export (see ``CONTEXT.md``).
- Help for Project Export must describe the three submenu items and that
  ``.txt`` cannot recreate a project.
- Follow-up: implement the submenu, the export-only text service, Import
  rejection copy, menu enablement, save-before-export, and tests for
  official titles only, every-five verse numbers, short last stanza, empty
  translation (no placeholder, no floating verse number), and notes
  omitted.

Related
=======

- Domain language: ``CONTEXT.md`` (Project Export, Old English Text
  Export, Translation Export, Backup, Full Translation).

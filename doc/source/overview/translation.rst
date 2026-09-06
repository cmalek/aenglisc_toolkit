===========
Translation
===========

This page covers writing the Modern English translation, notes, the Full
Translation reading view, exporting, and search. It condenses the in-app
**Notes Guide**, **Full Translation Window**, **Export Formatting**,
**Project Export/Import**, and **Search Guide** help topics — press
**F1** in the app for the full reference.

Editing the Old English text
============================

Occasionally, the source text itself needs a correction.  When this happens, you can edit the Old English text directly in the sentence card.

To do this, click the sentence's **Edit OE** button. This hides the **Edit
OE**/**Add Note** buttons and shows
**Save OE**/**Cancel Edit** in their place. Make your change, then click *Save
*OE** to commit it (undoable) or **Cancel Edit** to discard it —
either way the original buttons return. Editing re-tokenizes the sentence, so
annotations on unaffected tokens are kept and note/idiom spans are adjusted
automatically — a note or idiom whose range is entirely deleted is removed with
it.

Writing the translation
=======================

Each sentence card has a ``Modern English translation`` field below its ``Old
English text`` field. Type your translation there; it autosaves as you work.

You can press **T** to jump straight to a sentence's translation field from anywhere in that sentence.

Notes
=====

.. TODO: screenshot shot-notes, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-notes.png
   :alt: A note attached to a word span, shown with its superscript
         marker and the note text in the sentence's Notes section.

Attach explanatory commentary to any span of words:

1. Click the first word of the span, then **Shift+Click** the last word
   (Shift-click the same word twice for a one-word note).
2. Click **Add Note** (to the left of **Edit OE**).
3. Type the note text and click **Save**.

Note references in the Old English text appear as superscript numbers after the
last word in their span, and the related note is listed in full under the
sentence's ``Notes`` section. Click a listed note to highlight its words in the
text; double-click it to edit or delete.  Numbering, highlighting, and span
adjustment (when the underlying words change) are all automatic.

To edit a note, double-click the note in the Notes section, update the note, and click the **Save** button.

To delete a note, double-click the note in the Notes section and click the **Delete** button.

The Full Translation window
===========================

.. TODO: screenshot shot-full-translation, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-full-translation.png
   :alt: The Full Translation window, showing synchronized Old English
         and Modern English columns with the details sidebar open.

**Window → Full Translation** (**Ctrl+Shift+F**) opens a focused,
project-wide reading view:

- Old English and Modern English side by side, with synchronized
  scrolling.
- A toolbar search field that highlights matches across both text panes
  and the note list.
- Click a listed note to highlight its word span in the Old English pane.
- Click a word to open its annotation details in the sidebar, or
  double-click it to jump back to that sentence in the main editor.

This is also where you export to PDF (see below).

Exporting
=========

.. TODO: screenshot shot-pdf-glossary, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-pdf-glossary.png
   :alt: A page from an exported PDF showing the two-column glossary.

There are three exports, each for a different purpose:

.. list-table::
   :header-rows: 1

   * - Export
     - Where
     - Use it for
   * - DOCX
     - File → DOCX Export... (**Ctrl+E**)
     - A formatted Word document — annotations as superscripts/subscripts
       on the Old English text, translation below.  This is meant for exporting to a word processor for further editing.
   * - PDF
     - Full Translation window → **Export PDF**
     - A publication-style, landscape, side-by-side layout with real
       footnotes and an auto-generated glossary. Built with a bundled
       LaTeX (Tectonic) pipeline.
   * - JSON
     - Project → Export...
     - A complete, re-importable copy of one project — for sharing,
       backing up a specific project, or moving it between machines. See
       :doc:`/overview/backups` for the difference between
       this and an automatic Backup.

The PDF's glossary groups one entry per unique root + part-of-speech pair,
merging duplicate senses and showing verb classifiers like ``[impers]``,
``[intrans]``, or ``(+ inf)`` where relevant — it's built entirely from
your annotations, so a more complete annotation pass produces a richer
glossary.

To bring a JSON export back in, use **Project → Import...**; the app
handles both plain ``.json`` and gzip-compressed ``.json.gz`` files, and
resolves a project-name collision by renaming the import.

Search
======

Use the search bar at the top of the main window (or the toolbar search
in the Full Translation window). Choose a scope — **OE Text**, **ModE
text**, **Notes**, or **All** — then press **Enter** to jump to the first
match, **N**/**Shift+N** for next/previous. Old English matching is
diacritic- and case-insensitive and partial, so ``cyn`` matches
``cyning``.

Related topics
================

- :doc:`/overview/annotation` — annotating tokens and idioms
- :doc:`/overview/project_organization` — backups, Settings, and project
  structure
- :doc:`/overview/backups` — backups, Settings, and project structure
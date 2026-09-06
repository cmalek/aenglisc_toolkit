=======================
Remembered Annotations
=======================

Remembered annotations let you save a token annotation as a reusable
template and apply it later to matching tokens — useful when the same Old
English word appears many times with the same analysis and you don't want
to re-enter it repeatedly. (This is a companion to
:doc:`/overview/presets`, which reuses grammatical fields for a *part of
speech*; remembered annotations instead reuse a whole annotation for one
exact *spelling*.)

.. note::

   The idea here is that as you become more proficient in Old English, you will start recognizing words that you know the morphology of on sight.  For example, you might start knowing on sight that ``wæs`` is the 3rd person singular past indicative of **wesan**, *to be*, and that **wesan** is an anomolous verb which takes a nominative object.  To save yourself from having to re-enter this annotation for each occurrence of ``wæs`` in your project, you can remember this annotation and apply it to other occurrences of ``wæs`` in your project with ``Tools → Apply Remembered Annotations``.

What gets remembered
=======================

Remembered annotations are **token-only** — they save the grammatical
fields and shared metadata you'd normally set on a token annotation: part
of speech, inflectional details, Modern English meaning, and root. They do
**not** remember idiom annotations, and they don't store per-instance
sense information, since sense is specific to one occurrence in context.

Exact matching
=================

Remembered annotations match by the token's exact Old English surface
text — case-sensitive and diacritic-sensitive. A remembered entry for
``sæ`` matches ``sæ``, not ``sae`` or any other spelling. Enter the exact
token text you want to reuse when creating an entry manually.

Scopes
========

There are two remembered-annotation scopes:

- **Global** — available across all projects.
- **Project** — available only inside the current project.

If both a global and a project remembered annotation exist for the same
exact token text, the **project** one wins inside that project.

Remembering an annotation from the text
==========================================

.. TODO: screenshot shot-remember-context-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-remember-context-menu.png
   :alt: Right-click context menu on an already-annotated token in the Old
         English text, showing "Remember globally" and "Remember for
         project" options.

To save a token's current annotation as a remembered annotation:

1. In the Old English text area, right-click a token that already has an
   annotation.
2. Choose **Remember globally** to save it as a global remembered
   annotation, or **Remember for project** to save it only for the current
   project.

These options are only available when the token already has an annotation
to copy from.

Managing remembered annotations
===================================

.. TODO: screenshot shot-remembered-annotations-dialog, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-remembered-annotations-dialog.png
   :alt: The Remembered Annotations management dialog, showing a table of
         entries (Token, POS, Summary, Root, Modern English) with
         New/Edit/Delete/Close buttons.

Use the **Tools** menu to manage remembered annotations directly:

- **Tools → Global Remembered Annotations...**
- **Tools → Project Remembered Annotations...**

Each opens a table of that scope's entries (token text, part of speech, a
short grammatical summary, root, and Modern English meaning). From there
you can:

- **New** — create an entry by typing the exact token text it should
  match, then filling in its annotation in the same modal used for regular
  token annotation. If an entry for that text already exists in the scope,
  the dialog opens it for editing instead of creating a duplicate.
- **Edit** (or double-click a row) — reopen an entry's annotation for
  changes.
- **Delete** — remove an entry you no longer want, with confirmation.

Applying remembered annotations
===================================

.. TODO: screenshot shot-apply-remembered-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-apply-remembered-menu.png
   :alt: The Tools menu with "Apply Remembered Annotations" highlighted.

To apply remembered annotations across the current project:

1. Choose **Tools → Apply Remembered Annotations**.
2. The app finds every token in the project whose exact surface text
   matches a remembered entry visible to that project (global entries, plus
   any project-scoped entries, with project entries taking precedence).
3. Matching tokens that are safe to auto-fill are updated in a single
   batch.

The app never blindly overwrites an existing annotation — tokens that
already contain meaningful annotation data are skipped, so it's safe to run
this repeatedly as you add new remembered entries.

Undo support
============

Applying remembered annotations is undoable as a single batch operation:
**Ctrl+Z** undoes the whole batch apply, and redo (**Ctrl+Y** /
**Ctrl+Shift+Z**) restores it. This makes it safe to try applying
remembered annotations and roll back if the result isn't what you wanted.

When to use remembered annotations
==================================

Remembered annotations work best when:

- the same exact token spelling repeats often with a stable reading,
- you want a project-specific override for one spelling, or
- you've settled on a stable annotation for a common form.

.. important::

   Do be careful when remembering annotations for words that can legitimately take different analyses in different contexts.  Examples of words that are not good candidates for remembered annotations are:

   - ``hild``  This is a feminine noun that takes two entirely different meanings in different contexts.  In poetry, it can take the meaning of *war, battle*, but in other places it can take the meaning of *safe-keeping, safety, preservation*.  So this would not be a good candidate for a remembered annotation.
   - ``brocen`` This is a past participle which can come from either **brūcan**, *to make use of*, or **brecan**, *to break*.  Again, not disambiguated enough globally to be a good candidate for a remembered annotation.

Related topics
==============

- :doc:`/overview/annotation` — annotating tokens and idioms
- :doc:`/overview/presets` — saving and applying grammatical field presets

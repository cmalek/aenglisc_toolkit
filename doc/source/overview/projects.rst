========
Projects
========

Starting a new project
=========================

.. TODO: screenshot shot-new-project-dialog, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-new-project-dialog.png
   :alt: The New Project dialog, showing Project Title, Source,
         Translator, and Notes fields, and the Old English text input
         method selector.

**File → New Project...** (**Ctrl+N**) opens the **New Project** dialog.
Fill in:

- **Project Title:** — required
- **Source:** — the bibliographic origin of the text (edition, manuscript,
  anthology, etc.); multi-line
- **Translator:** — pre-filled with your system username, editable
- **Notes:** — free-form project-level notes (not the same as a per-word
  Note; see :doc:`/overview/translation`); multi-line

Loading the Old English text
===============================

The same dialog includes an **Input Method** choice:

- **Paste in text** — paste or type directly into the **Old English
  Text:** box.
- **Import from file** — browse to a file. Supported formats: ``.txt``,
  ``.xml``, ``.tei``, ``.md``.

Click **Ok** to create the project. Your text is automatically split into
sentences and tokenized, ready for annotation.

Adding more text to an existing project
==========================================

Use **Project → Append OE text...** to open the same paste-or-file input
(the **Append OE Text** dialog) and add more text onto the end of the
current project without starting over.

Editing project metadata later
==================================

Use **Project → Edit Project...** to change the title, source, translator,
or notes after creation.

Next steps
============

- :doc:`/overview/project_organization` — chapter/section structure,
  Settings, backups
- :doc:`/overview/annotation` — annotating the text you just loaded

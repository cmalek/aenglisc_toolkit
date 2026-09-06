======================
Project Organization
======================

Text hierarchy: chapters, sections, paragraphs
==================================================

A project's text is organized as Chapter → Section → Paragraph →
Sentence (see :doc:`/overview/domain_language` for what each level means).
You don't create these ahead of time — you mark sentence boundaries as you
work through the text.

.. TODO: screenshot shot-mark-as-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-mark-as-menu.png
   :alt: The "Mark as ..." dropdown on a sentence card, showing Paragraph
         Start, Section Start, and Chapter Start options.

Each sentence card has a **Mark as ...** dropdown with one of the following options:

- **Paragraph Start** / **Not Paragraph Start**
- **Section Start** / **Not Section Start**
- **Chapter Start** / **Not Chapter Start**

Which item is listed depends on the current sentence's position in the hierarchy.

These toggle whether the current sentence begins a new paragraph, section,
or chapter. All of these split/merge actions are undoable with **Ctrl+Z**.
(The dropdown is hidden on a project's very first sentence, since it's
always the start of everything.)

Navigating the hierarchy
========================

.. TODO: screenshot shot-chapter-section-toolbar, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-chapter-section-toolbar.png
   :alt: The Chapter/Section navigation toolbar at the top of the main
         window, showing prev/next buttons and chapter/section dropdowns.

A toolbar at the top of the main window shows:

- **Chapter:** a previous (``<``) button, a dropdown of chapters, and a
  next (``>``) button
- **Section:** the same pattern, scoped to the current chapter

Use these to jump directly to any chapter or section instead of scrolling.

Using the in-app help
========================

.. TODO: screenshot shot-help-center, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-help-center.png
   :alt: The in-app Help Center dialog, showing the topic list and a
         rendered help page.

Press **F1**, or use **Help → Help**, to open the Help Center at any time
— it's non-modal, so you can keep it open for reference while you work. It
covers every workflow topic (annotation, idioms, notes, search, export,
backups, keybindings, troubleshooting) in more field-by-field detail than
these docs, and stays in sync with the version of the app you're running.

Settings
=========

.. TODO: screenshot shot-settings, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-settings.png
   :alt: The Settings/Preferences dialog, showing backup interval, backup
         count, and theme controls.

Open Settings from **[Application menu] → Preferences...** (**Cmd+,**) on
macOS. Available settings:

- **Number of backups to keep** (1–100)
- **Backup interval in minutes** (1–1440)
- **Theme** — ``dark`` or ``light``

.. note::

   Changing the theme takes effect after you fully quit and restart the
   app — it does not apply live.

Backups
=======

The app automatically backs up your project database — separate from a
per-project JSON export (see :doc:`/overview/translation`; a Backup covers
every project in the database and is restored, not imported). By default
it keeps the 5 most recent backups, created every 12 hours, configurable
in Settings above.

See :doc:`/overview/backups` for more details on backups.


Next steps
==========

- :doc:`/overview/annotation` — annotating tokens and idioms
- :doc:`/overview/translation` — writing the translation and exporting

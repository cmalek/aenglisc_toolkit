========================
Annotation Presets
========================

A preset is a named, saved set of grammatical field values for one part of
speech — for example, "Weak Masc Nom Sg" for nouns, or "3rd Sg Present
Indicative" for verbs. Presets let you fill in the repetitive grammatical
fields of an annotation in one click instead of re-selecting them every
time, and are a companion to :ref:`annotation-incremental` and
:doc:`/overview/annotation`'s remembered annotations — remembered
annotations reapply a whole annotation to a recurring *spelling*, while
presets reapply just the grammatical fields to any word of the same part of
speech.

Presets are supported for **Noun, Verb, Adjective, Pronoun, and Article**
only. Adverbs, Prepositions, Conjunctions, Interjections, and Numbers have
too few fields (0–1) for a preset to save any real effort, so they're
intentionally left out.

Applying a preset while annotating
=====================================

.. TODO: screenshot shot-annotation-preset-dropdown, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-annotation-preset-dropdown.png
   :alt: The annotation modal with a part of speech selected, showing the
         Preset dropdown and "Apply Preset" button populated with saved
         presets for that part of speech.

1. Open the annotation modal for a token (see :doc:`/overview/annotation`)
   and choose its part of speech.
2. If any presets exist for that part of speech, the **Preset** dropdown
   next to the grammatical fields becomes enabled, listing them by name.
3. Choose a preset and click **Apply Preset** to fill in its saved field
   values. Only fields the preset actually sets are applied — fields it
   left blank are untouched, so you can layer a preset on top of values
   you've already entered.
4. Continue filling in whatever the preset didn't cover (root, meaning,
   confidence, etc.), then **Apply** the annotation as usual.

Changing the part of speech clears the preset selection, since a preset is
always specific to one part of speech.

Saving a preset from the annotation modal
============================================

.. TODO: screenshot shot-save-as-preset-button, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-save-as-preset-button.png
   :alt: The annotation modal's "Save as Preset" button, enabled after
         grammatical fields have been filled in for a supported part of
         speech.

While annotating, once you've filled in the grammatical fields for a
supported part of speech, the **Save as Preset** button becomes enabled.
Clicking it opens a small save dialog pre-loaded with the values currently
in the form:

1. Enter a name for the preset (must be unique for that part of speech).
2. Adjust any fields if needed.
3. Click **Save** to store it for reuse, or **Cancel** to discard.

The **Save as Preset** button is disabled while editing a remembered
annotation, since remembered annotations already capture a full field set
for a specific spelling.

Managing presets
===================

.. TODO: screenshot shot-pos-presets-dialog, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-pos-presets-dialog.png
   :alt: The POS Presets management dialog, showing one tab per supported
         part of speech with a preset list, detail form, and
         New/Edit/Delete/Clear/Save buttons.

Use **Tools → POS Presets...** to open the full preset management dialog.
It has one tab per supported part of speech. Each tab has:

- A **list** of existing presets for that part of speech.
- **New**, **Edit**, and **Delete** buttons for the selected preset (Delete
  asks for confirmation).
- A **detail form** showing the grammatical fields for that part of speech,
  plus **Clear** (empties the form) and **Save** (creates or updates the
  preset) buttons.

Selecting a preset in the list loads it into the detail form for editing.
Preset names must be unique within a part of speech, but the same name can
be reused across different parts of speech.

Presets are stored in the local database (not per-project), so they're
available across every project and included in :doc:`/overview/backups`
like the rest of your data — they are **not** included in a per-project
export/import file, since they're independent of any one project.

Related topics
================

- :doc:`/overview/annotation` — annotating tokens and idioms
- :doc:`/overview/backups` — how presets are backed up

==========
Annotation
==========

This page walks through annotating tokens and idioms. It's a condensed,
screenshot-illustrated version of the in-app **Annotation Guide**,
**Idioms Guide**, and **Incremental Annotation** help topics — press
**F1** in the app for the full reference with every field and edge case.
Remembered annotations have their own page:
:doc:`/overview/remembered_annotations`.

Annotating a single token
============================

.. TODO: screenshot shot-annotation-modal, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-annotation-modal.png
   :alt: The annotation modal open for a selected token, showing POS field
         selection.

1. Select a word in the Old English text.
2. Press **Enter** or double-click the word to open the annotation modal.
3. Choose a part of speech, either from the dropdown or with a keyboard
   shortcut:

   ========  =================
   Key       Part of Speech
   ========  =================
   ``N``     Noun
   ``V``     Verb
   ``A``     Adjective
   ``R``     Pronoun
   ``D``     Determiner/Article
   ``B``     Adverb
   ``C``     Conjunction
   ``E``     Preposition
   ``I``     Interjection
   ========  =================

4. Fill in the grammatical fields that appear for that part of speech
   (case, number, gender, declension, verb class, and so on — see the
   in-app **Morphological Tag Reference** for the full set of codes).
5. Fill in the metadata fields, common to every part of speech:

   - **Confidence** — a 0–100% slider for how certain you are
   - **TODO** — flag the annotation as needing further review
   - **Definition of root word** — the dictionary Meaning (e.g. "time,
     season")
   - **Meaning/Sense in this instance** — the contextual Sense (e.g.
     "season in this line")
   - **Root** — the dictionary headword (e.g. ``sumor``)

6. Click **Apply** or press **Enter** to save. **Clear** empties the
   form; **Cancel** or **Escape** discards your changes.

You don't have to fill in every field at once — see
:ref:`annotation-incremental` below.

.. _annotation-incremental:

Incremental annotation
========================

Annotation is iterative by design:

1. Start broad — tag just the part of speech across a whole sentence or
   passage.
2. Come back later and add grammatical detail (gender, case, verb class,
   etc.) as you firm up your reading.
3. For a genuinely ambiguous form, lower **Confidence** and set the
   **TODO** flag for later review, rather than guessing.

The annotation modal remembers your last-used values per part of speech,
so annotating a run of similar words (a string of nouns, say) gets faster
as you go — fill in the first fully, then adjust only what differs on the
rest.

Presets
=======

For fields you fill in the same way over and over (a recurring noun
declension, a common verb tense), save them as a reusable **preset** and
apply them in one click instead of re-selecting each field — see
:doc:`/overview/presets` for the full walkthrough.

Multi-word idioms
=================

.. TODO: screenshot shot-idiom-selection, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-idiom-selection.png
   :alt: A multi-word span selected in the Old English text, ready for
         idiom annotation.

Use an idiom when meaning or grammatical function belongs to a phrase as a
whole, not to one head word.

1. In the Old English text (not edit mode), **Cmd/Ctrl+Click** a word to
   start an idiom range selection.
2. **Cmd/Ctrl+Click** additional words to extend the span.
3. Press **A** to open the annotation modal for that span, and annotate it
   the same way as a single token — choose the part of speech that matches
   the *phrase's* role in the sentence, not just its head word.
4. Click **Apply** (or press **Enter**) to save.

Clicking any word that belongs to a saved idiom selects the whole idiom
span. To inspect an idiom's individual words, open the idiom's annotation
modal — the words are shown as clickable labels at the top — or select the
word's row directly in the token table.

If a phrase is genuinely ambiguous, the idioms guide's advice is the same
as above: lower **Confidence** and mark **TODO**.

The Annotation sidebar
========================

.. TODO: screenshot shot-annotation-sidebar, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-annotation-sidebar.png
   :alt: The Annotation (details) sidebar showing the full annotation for
         a selected token.

Selecting a token (in the text or in the token table) shows its full
annotation — every grammatical field, the root, meaning, sense, and
metadata — in the sidebar alongside the sentence you're working on. Use it
to check a word's morphology at a glance without re-opening the annotation
modal, especially useful while reviewing an idiom's individual words.

Bosworth-Toller's Anglo-Saxon Dictionary Online
-----------------------------------------------

Note the button outlined in light blue in the screenshot above -- it contains an icon of a book.  Clicking this button will open your default browser to the search results for the value of **Root** on the `Bosworth-Toller's Anglo-Saxon Dictionary Online <https://bosworthtoller.com/>`_ website.

Remembered annotations
======================

When the same Old English spelling recurs often with the same reading,
save time by remembering it — right-click an already-annotated token and
choose **Remember globally** or **Remember for project**, then later use
**Tools → Apply Remembered Annotations** to batch-fill matching tokens
across the project in one undoable step. See
:doc:`/overview/remembered_annotations` for the full workflow, including
scopes, matching rules, and managing saved entries.

Propagating an annotation or meaning
=====================================

.. TODO: screenshot shot-propagate-context-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-propagate-context-menu.png
   :alt: Right-click context menu on an already-annotated token in the Old
         English text, showing "Propagate annotation" and "Force propagate
         meaning" options alongside the Remember options.

Right-clicking an already-annotated token also offers two one-shot,
project-wide actions, next to **Remember globally**/**Remember for
project**:

- **Propagate annotation** — copies this token's whole annotation (every
  grammatical field and root, but not its per-instance sense) onto every
  *other* token in the project with the same normalized surface form —
  but only into tokens that don't already have a meaningful annotation. It
  never overwrites existing work.
- **Force propagate meaning** — copies just this token's **Modern English
  meaning** onto every token in the project that shares the same
  normalized root, *even if those tokens already have a meaning set*. Use
  this when you've corrected or refined a root's meaning and want that
  correction to apply everywhere at once. It's disabled until the token has
  both a root and a Modern English meaning filled in.

Both actions show a confirmation dialog reporting how many words were
updated (or that no matching words were found), and both are undoable in
one step with **Ctrl+Z**.

Propagation differs from :doc:`/overview/remembered_annotations` in two
ways: it acts immediately on tokens already in the current project instead
of saving a template for future use, and it matches by *normalized*
surface/root rather than exact spelling — so, unlike remembered
annotations, it isn't sensitive to case or diacritics. Because "Force
propagate meaning" can overwrite existing meanings, use it deliberately,
and prefer plain **Propagate annotation** when you only want to fill in
tokens that are still blank.

Undo
====

Annotation changes, idiom creation, and batch-applying remembered
annotations are all undoable with **Ctrl+Z** (redo: **Ctrl+Y** /
**Ctrl+Shift+Z**). Project-level destructive actions (like deleting a
project) are not — see :doc:`/overview/project_organization` for backups
and export as your safety net there.

Related topics
================

- :doc:`/overview/presets` — saving and applying grammatical field presets
- :doc:`/overview/remembered_annotations` — reusing whole annotations for
  recurring spellings
- :doc:`/overview/translation` — writing the translation and exporting
- :doc:`/overview/project_organization` — project structure, Settings, and
  backups

.. _adr_0005_pos_field_catalog:

==================================================================
ADR 0005: One POS field catalog shared by form, preset and sidebar
==================================================================

:Status: Proposed
:Date: 2026-10-02

Context
=======

Audit finding F2 (resolve order 5 of 12 in the 2026-09-13 architecture and
capability audit): the fields shown for each part of speech are defined three
times.

- The annotation modal builds them in each ``*Fields.build()`` in
  ``oeapp/ui/dialogs/pos_form_system.py`` (``add_combo(attr, label, MAP)``).
- The preset dialog declares them as ``FIELD_SPECS`` tuples of ``PosFieldSpec``
  in the same module, for N/V/A/R/D only.
- The token details sidebar renders them by hand in each ``*Renderer.render()``
  in ``oeapp/ui/token_details_sidebar.py``.

Adding a morphology field has needed three UI edits, and the copies have
drifted: the sidebar says "Verb Class" where the modal says "Class" and the
preset says "Class:"; verb field order differs on every surface; the preset
declares ``declension`` and ``verb_class`` as *editable* combos, a leftover of
the ``d2b3f2b`` refactor, whose dropdown items are display labels.

That last difference is a data bug, reproduced against
``PresetNounFields`` and ``PresetVerbFields``: selecting "Strong (s)" makes
``extract_values`` return ``"Strong (s)"`` (``currentText()``), not the code
``"s"``, and loading the code ``"s"`` shows ``s`` in the text box.
The models declare ``CHECK`` constraints on these columns for ``annotations``
and ``remembered_annotations``, but a real database at head
(``f38623b35077``) has them only on ``remembered_annotations``: its
``annotations`` table carries a single ``CHECK``. Nothing therefore stops
label-form values reaching ``annotations``, and they have: that database holds
6 ``annotations`` rows with ``declension = 'Strong (s)'`` (shown as ``?`` by the
sidebar), 31 with ``declension = ''``, and 1 label-form ``annotation_presets``
row. No value matched neither a code nor a label, and ``remembered_annotations``
is clean. Repairing the missing ``annotations`` constraints is the separate
backlog card; this change repairs the values it can see.

The live preset path is ``PresetPosFormManager``. The ``_set_combo_value`` and
related ``*_REVERSE_MAP`` helpers in ``annotation_preset_management.py`` are
retained only for direct unit tests.

Presets can also store ``CLEAR_SENTINEL`` (``"__CLEAR__"``) meaning "clear this
field". ``declension`` and ``verb_class`` currently opt out
(``preset_clear_mode=False``), so no existing row holds the sentinel in those
columns.

The code-to-label maps already live on ``AnnotationLookupsMixin``. The ORM owns
the allowed codes through its ``CHECK`` constraints. Alembic autogenerate does
not track ``CHECK`` constraints (see the no-op revision ``b4241a8588cc``).

Decision
========

D1 — A UI-only catalog
----------------------

A new module ``oeapp/ui/pos_field_catalog.py`` defines one ``PosField`` per
field and, through ``PosFieldCatalog``, one ordered tuple of them per part of
speech. The annotation modal,
the preset dialog and the sidebar all consume it. It holds data only: no Qt
types, no form framework. Lookup maps stay on ``AnnotationLookupsMixin`` and
are referenced, not copied. The ORM stays the authority on allowed codes.

D2 — One label and one order
----------------------------

Each field has one canonical label (the modal's, for example "Class") and each
part of speech one field order. Renderers add punctuation. This changes some
visible text: the sidebar "Verb Class" becomes "Class" (and "Pronoun Type",
"Article Type", "Conjunction Type" become "Type", "Adverb Degree" becomes
"Degree"), and the preset verb order follows the modal. The sidebar shows ``?``
for any unset or unrecognised value; today some fields show a blank instead.

D3 — Surface differences are explicit flags
-------------------------------------------

Preset coverage is a catalog property (``PosFieldCatalog.preset_supported``)
set for N/V/A/R/D, not a second list: the five per-POS preset field classes
and the manager's class table are removed, and one preset field group takes the
POS code. The preset's blank/No/Yes boolean maps are
dropped, since the preset combo already prepends a blank. Preset
``object_name`` values are derived as ``{pos}_{attr}_combo``. The ``editable``
flag is removed, so ``declension`` and ``verb_class`` are code-mapped combos on
every surface. These two keep ``preset_clear_mode=False``: removing
``editable`` must not let ``CLEAR_SENTINEL`` into columns that carry a
``CHECK``. The dead ``_set_combo_value`` helpers and ``*_REVERSE_MAP`` entries
in ``annotation_preset_management.py`` are removed together with the tests that
exist only for them.

D4 — Cross-field rules stay out of the schema
----------------------------------------------

Choosing verb class ``pp`` sets "Requires Infinitive" in the modal only. It
stays in ``VerbFields`` as hand-written code. The sidebar is read-only and a
preset should store exactly what was picked.

D5 — All parts of speech migrate
--------------------------------

Every part of speech moves to the catalog in this change, committed Noun, then
Verb, then the rest.

D6 — Repair existing data
-------------------------

A hand-written Alembic revision, in the style of ``d6d8b613bc53``, acts on
``annotation_presets`` and ``annotations`` (``remembered_annotations`` already
enforces codes). On both tables, in order, it:

1. maps label-form ``declension`` and ``verb_class`` values to codes, in
   tiers, stopping at the first that applies:

   a. the value is already a valid code: leave it;
   b. the value ends in a parenthesised valid code, as every label does
      (``"Strong (s)"`` gives ``s``); this also covers reworded or misspelled
      labels such as ``"Anomolous (a)"``;
   c. the value equals a known label after case and whitespace normalisation,
      using a label-to-code table frozen inside the revision that covers every
      label the maps have carried (taken from the history of
      ``oeapp/ui/mixins.py``), not only today's;

   Fuzzy matching is deliberately not used: the labels differ by one character
   ("Strong Class 1 (s1)" against "Strong Class 2 (s2)"), so a near match
   could silently pick the wrong class.
2. sets the empty string to ``NULL`` (a blank combo artefact, not a value);
3. leaves ``NULL`` and ``"__CLEAR__"`` untouched;
4. leaves any value no tier matches in place and logs it;
5. on ``annotation_presets`` only, adds the ``CHECK`` constraints in batch
   mode, but only if no unmatched value remains; otherwise it skips them and
   reports. ``annotations`` constraints belong to the backlog card.

The downgrade does nothing, because the earlier state was corrupt data. Startup
already backs up the database, migrates, and restores on failure.

JSON import gets an optional per-revision ``values`` section in
``oeapp/etc/field_mappings.json`` that maps the same labels to codes. It is
applied wherever ``declension`` or ``verb_class`` keys appear in the payload,
so it also visits annotations and remembered annotations; their values are
already codes and pass through. A test asserts that the JSON table and the
revision's table are identical, and a malformed ``values`` section must raise
rather than be swallowed by the existing ``_transform_data`` handler.

D7 — Verification
-----------------

Tests: a data-migration test seeding label-form presets at the previous
revision; a parity test that every catalog attr is a real ``Annotation`` column
(and an ``AnnotationPreset`` column when ``preset_supported``) and that
lookup-map codes match the ``CHECK`` codes (equal today for ``declension`` and
``verb_class``; one documented exception: the ``verb_aspect`` ``CHECK`` allows
``'f'`` but the UI has no label for it, and no row uses it; the CHECK-drift backlog card drops ``'f'`` from the ``CHECK`` and removes the exception); and an import test
using a pre-change export. The test reproducing the stored-label bug is written
first, within the preset task.

D8 — Display helpers tolerate unrecognised codes
------------------------------------------------

``AnnotationTextualMixin.format_pos``, ``format_gender`` and ``format_context``
fall back to the stored text when a map does not know a code, as the PDF
exporter already does. Today a single unrecognised value (for example the
label-form ``"Strong (s)"``) raises ``KeyError`` from the sidebar header, DOCX
export, annotation propagation and the remembered-annotations dialog. The
repair in D6 fixes known rows; this keeps values that no tier can resolve from
breaking those callers.

Consequences
============

- Adding a field is one catalog edit plus the model column and migration.
- Some labels and the preset verb order change visibly. Tests that match on
  them are updated.
- Presets can no longer hold values outside the maps, and the database now
  enforces that.
- Help and documentation that mention the old labels (for example "Verb
  Class") must be audited and updated in three places: the Sphinx docs under
  ``doc/source/`` (``overview/annotation.rst``, ``overview/translation.rst``),
  the in-app help sources ``oeapp/help/topics/*.md`` (at least
  ``annotation-guide.md`` and ``morphological-reference.md``), and the tracked
  rendered copies in ``oeapp/help/assets/*.html`` and the macOS help book, which
  must be regenerated from the topics rather than edited by hand. Most hits for
  "verb class" are ordinary prose; only the UI label needs to change. The
  ``export-formatting.md`` mentions need a separate look, since they may be
  export column names, not form labels.
- Screenshots in ``doc/source/_static/`` to retake: ``screenshot-annotation-sidebar.png``
  and ``screenshot-full-translation.png`` (sidebar "Verb Class:" becomes
  "Class:"), ``screenshot-save-as-preset-button.png`` (preset dialog: Direct
  Object Case moves above Form, and Class becomes a normal combo), and
  ``screenshot-pos-presets-dialog.png`` (Declension is no longer an editable
  combo). The annotation modal, light/dark/themes, preset-dropdown and
  remembered-annotations screenshots show only unchanged Noun fields or modal
  labels and stay as they are.
- Ordering: the revision and the removal of ``editable`` land together, before
  the remaining parts of speech move to the catalog.
- Guard tests tie the catalog to the models (D7).
- A value that matches no tier is never deleted or guessed: it stays, is
  logged, and the ``annotation_presets`` ``CHECK`` is skipped on that database.
  The one real database inspected has no such value.
- Missing or stale ``CHECK`` constraints on ``annotations`` (and any stale ones
  on ``remembered_annotations``) are not repaired here; a separate backlog card
  covers it.

Alternatives considered
=======================

- *Schema on the ``Annotation`` model.* Rejected: it would pull labels and
  widget concerns into the ORM, and the ORM already owns the codes.
- *Migrate only Noun and Verb.* Rejected: it leaves two systems and keeps the
  problem for the remaining parts of speech.
- *Keep ``editable`` as a per-surface flag.* Rejected: one field would store
  different formats on different surfaces.
- *Fuzzy matching of unrecognised labels* (``difflib``). Rejected: near-identical
  labels make a wrong silent match likelier than a useful one.
- *Setting unmatched values to ``NULL``.* Rejected: it destroys user text.
- *Third-party form library.* Rejected: the audit advisor found no match and
  the widgets are plain Qt combos.

Related
=======

- Trello card 102 (F2) and the audit finding F2.
- ``AnnotationLookupsMixin`` in ``oeapp/ui/mixins.py``.
- Backlog card: audit and repair stale ``CHECK`` constraints.

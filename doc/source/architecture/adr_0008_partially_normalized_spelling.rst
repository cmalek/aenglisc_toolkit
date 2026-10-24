.. _adr_0008_partially_normalized_spelling:

============================================================
ADR 0008: Match annotations by Partially Normalized Spelling
============================================================

:Status: Accepted
:Date: 2026-10-24

Context
=======

Apply Remembered Annotations matched a token's exact surface to the saved
``token_text``. ``Hē`` did not receive a remembered ``hē``, and a line-initial
``Hī`` did not receive a remembered ``hī``. Eth and thorn, internal hyphens,
and consonant dots were likewise different spellings.

Annotation Propagation and Meaning Propagation already matched on Normalized
Form (``surface_normalized`` and ``root_normalized``). That key strips every
diacritic, including length marks, so ``Sē`` was copied onto ``Se`` and a
meaning for ``gōd`` would overwrite ``god``. Those are different words.

The unique indexes on remembered annotations are exact ``token_text`` within a
scope. ``ðæt`` and ``þæt`` can both be stored. A looser match therefore has to
say what happens when two saved rows collapse to one spelling. Choosing one
of them would be translating.

Normalized Form is also the key for search and for glossary grouping, and it
is stored on the token and the annotation. Changing it, or adding a column
for a second key, would move those features and would need a migration.
Apply reported only on the status bar, which is easy to miss after a batch
change.

``CONTEXT.md`` is the glossary for the terms used below.

Decision
========

D1 — Partially Normalized Spelling
----------------------------------

Matching uses Partially Normalized Spelling: Normalized Form that keeps length
marks (U+0304 COMBINING MACRON). The key is lowercase, folds eth to thorn,
removes internal hyphens and dashes the same way Normalized Form does, and
strips every other combining mark, including the dots on ``ċ`` and ``ġ``.

``gē`` and ``ge`` differ. ``gōd`` and ``god`` differ. ``Hē`` and ``hē`` do
not, nor do ``ðæt`` and ``þæt``, nor ``ġe-wāt`` and ``gewāt``. The key is
computed in Python. It is not stored.

D2 — Three actions use that key
-------------------------------

- **Apply Remembered Annotations** matches each token surface to a remembered
  entry's ``token_text``. It still fills only tokens whose annotation is safe
  to auto-fill.
- **Annotation Propagation** matches other tokens in the project by the
  Partially Normalized Spelling of the source surface, not by
  ``surface_normalized``. It still does not consult a Remembered Annotation,
  and it still copies onto safe-to-auto-fill targets only.
- **Meaning Propagation** matches other annotations by the Partially
  Normalized Spelling of the Root, not by ``root_normalized``. It still
  overwrites only Meaning, only where an annotation already exists, and it
  still skips the source token.

D3 — Normalized Form is unchanged
---------------------------------

``normalize_old_english``, the stored ``surface_normalized`` and
``root_normalized`` columns, search, and glossary grouping keep today's
Normalized Form, which strips length marks. There is no new column and no
Alembic migration.

D4 — One entry per spelling in a scope
--------------------------------------

A scope holds one remembered entry for a Partially Normalized Spelling.
Remembering a spelling that matches that one entry updates its analysis and
keeps the ``token_text`` already saved, so remembering ``hē`` leaves the row
labelled ``Hē``. **New** in the management dialog opens that row instead of
creating a second one.

When the scope already has two entries for that spelling, Remember and
**New** refuse and name both saved spellings. They do not update either row.
Saving the exact row already open in the editor is still allowed, so one of
the two rows can be corrected.

D5 — An ambiguous group is not applied
--------------------------------------

Two remembered annotations in one scope with the same Partially Normalized
Spelling are an Ambiguous Remembered Annotation, whether or not the rest of
the annotation agrees. Apply uses neither. It does not delete a row and it
does not prefer the newer one.

A project entry and a global entry for the same spelling are not ambiguous.
The project entry wins. If the project group is itself ambiguous, it still
blocks the global entry and nothing is applied for that spelling. If only the
global group is ambiguous and the project has no entry, nothing is applied
for that spelling. A single clean project entry ignores a conflicting global
pair.

D6 — Apply always ends in a dialog
----------------------------------

Apply Remembered Annotations always finishes in a dialog, including when
nothing matched. The dialog reports how many tokens were updated, and how
many were skipped because they already had an annotation when that count is
not zero. When any group is ambiguous, it lists each pair and its scope.
When nothing matched and nothing is ambiguous, it says that no remembered
annotations matched. This action does not use the status bar.

Consequences
============

- Capitalization, eth and thorn, internal hyphens, and consonant dots now
  share one remembered entry and one propagation target. Length marks still
  keep words apart.
- A propagation that used to copy ``Sē`` onto ``Se``, or a meaning for
  ``gōd`` onto ``god``, no longer does.
- Rows saved under the old exact-text rule can form an ambiguous group.
  They stay in the database and stop applying until the user deletes or
  edits one. The app does not merge them.
- The list label can differ from the surface just remembered, because the
  saved ``token_text`` is kept.
- Apply is modal even when the text is unchanged, so a no-match or an
  ambiguous group is visible.
- The database can still store an ambiguous pair, because uniqueness remains
  exact ``token_text``. Detection stays in Python.
- Search and glossary output still collapse length marks.
- In-app help must describe this match, not exact surface match.
- Right-click selection of a line-initial token is a hit-test defect. It is
  not part of this decision.

Alternatives considered
=======================

- **Keep exact surface match for Apply.** Rejected: ``Hē`` and ``hē`` are
  the same spelling for these actions, as are eth and thorn.
- **Use Normalized Form for all three actions.** Rejected: it treats ``gē``
  and ``ge``, and ``gōd`` and ``god``, as the same word. Propagation already
  did this, and that collapse was not intended.
- **Store the partial key and enforce one row in the database.** Rejected:
  it needs a migration and a forced choice among rows that already collide.
- **Auto-merge an ambiguous pair, or keep the newer row.** Rejected: that
  chooses an analysis.
- **Report Apply on the status bar.** Rejected: the summary is easy to miss.

Related
=======

- ``CONTEXT.md`` terms **Partially Normalized Spelling**, **Remembered
  Annotation**, **Ambiguous Remembered Annotation**, **Annotation
  Propagation**, and **Meaning Propagation**.
- Trello cards 109 and 111. Card 110 is the line-initial hit-test defect
  excluded above.
- Normalized Form stays the key described for search and glossary grouping.
  This decision does not supersede that use.

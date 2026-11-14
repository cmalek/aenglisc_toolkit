.. _adr_0013_pdf_glossary_aggregation:

=============================================================
ADR 0013: PDF glossary aggregation keeps its current grouping
=============================================================

:Status: Accepted
:Date: 2026-11-14

Context
=======

``FullTranslationPDFExporter`` built the Full Translation PDF in one
class: Tectonic invocation, LaTeX for the side-by-side text, and the
Glossary inventory. The Full Translation window and the PDF already
share ``oeapp.models.text_flow`` for titles, sentence separators, verse
line numbers, and ``[...]`` when Modern English is empty. The window
paints that reading in Qt. The PDF emits paracol columns, footnotes, and
a Glossary the window does not show.

``CONTEXT.md`` defines **Glossary** as the reading inventory of one
project in the exported Full Translation: one entry per Root under its
Normalized Form and part of speech, and for a preposition also per case
it governs. **Meaning Conflict** is a different comparison. It matches
Root, part of speech, and noun gender, and compares the whole Meaning
text.

A backlog card asked the extraction to add noun gender to the key and to
serve a future Glossary window. Another backlog card already tracks
running Tectonic off the UI thread. ``pdf_engine.py`` already isolates
the Tectonic binary. Replacing Tectonic was out of scope.

Decision
========

D1 — The window and the PDF stay separate renderers
---------------------------------------------------

Visual parity is not a product requirement. Both readings keep the
shared ``text_flow`` rules. Qt keeps selection and superscript notes.
LaTeX keeps columns, footnotes, and the Glossary. There is no shared
renderer.

D2 — Glossary grouping does not change
--------------------------------------

``Glossary.entries`` groups one project's annotations by normalized
root, part of speech, and, for a preposition, the case it governs.
Nouns that differ only in gender share an entry. Meanings split on
``;`` or ``,`` are collected onto that entry. This is not Meaning
Conflict detection, and it is not a live Glossary window.

D3 — Aggregation leaves the exporter
------------------------------------

``oeapp.services.glossary.Glossary`` returns
``oeapp.models.glossary.GlossaryEntry`` values. ``FullTranslationPDFExporter``
calls ``Glossary.entries`` and still renders the legend, the entry
lines, and the rest of the document. It still runs Tectonic on the UI
thread from ``FullTranslationWindow._export_pdf``. The unused
``_group_sentences_by_paragraph`` method is deleted.

Consequences
============

- PDF output is unchanged. A later change to the grouping key is a
  change inside ``Glossary``, not a second extraction from the exporter.
- The exporter still blocks the window until Tectonic finishes.
- The Glossary window stays blocked on the card that adds noun gender
  to the key. That card is the behavior change; this decision is not.
- ``Glossary.entries`` and ``_accumulate_glossary_entry`` are still
  longer than the project's usual method limit. They were moved as they
  stood.

Alternatives considered
=======================

- **One renderer for the window and the PDF.** Rejected. The window is
  interactive Qt. The PDF is paracol LaTeX plus a Glossary. Shared
  ``text_flow`` rules are the common part.
- **Add noun gender to the key in this change.** Rejected. That splits
  entries such as *hild* masculine and *hild* feminine and changes the
  PDF. It stays on the backlog card below.
- **Move Tectonic onto ``QProcess`` in this change.** Rejected. The
  backlog already has that card. This decision leaves the export call
  blocking.
- **Replace Tectonic.** Rejected. The PDF depends on paracol and the
  glossary macros the current document emits.

Related
=======

- ``CONTEXT.md``, **Glossary** and **Meaning Conflict**
- F9: https://trello.com/c/0WY0LLm5
- Tectonic off the UI thread: https://trello.com/c/yDN152tV
- Noun gender in the Glossary key: https://trello.com/c/JGha53LS
- Glossary window: https://trello.com/c/RmFk0UJY

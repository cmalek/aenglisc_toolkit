.. _adr_0014_heading_sentences:

==========================================
ADR 0014: Heading sentences replace titles
==========================================

:Status: Proposed
:Date: 2026-11-14

Context
=======

Full Translation, the PDF, the DOCX export, and the plain-text exports
print an official ``Chapter.title`` or ``Section.title`` as its own line,
then print the sentence that follows. Translators often copy that title
out of the text, so the reading shows it twice. The stored title is one
string, so an Old English or Latin title also appears on the Modern
English side.

``visible_titles`` already skips auto-generated titles. Official titles
still print. Wyrdcraeft ingest stores an official chapter title on the
chapter and does not copy it into a sentence. Verse sections are named
``Lines N-M`` in the section menu. That label is auto-generated and is
not printed in the reading.

Decision
========

D1. A heading is a sentence
---------------------------

A heading sentence is still a sentence. It has one role: chapter heading,
section heading, or subsection heading.

- A chapter has one chapter heading: the first sentence of its first section.
  A verse project is one in which every sentence is verse. A chapter heading
  at the start of a section does not count as prose, because that sentence
  may have no verse lines. A text that mixes prose and verse, such as
  Cædmon's Hymn, is a prose project. In a verse project the chapters are
  named from the start of the text. The opening sentence of a later chapter
  may be a chapter heading only when every earlier chapter already has one
  on the first sentence of its first section. A prose project may name a
  later chapter first.
- A section has one section heading. It is the first sentence of the
  section. In the section that opens a chapter, it may be the second
  sentence, and only while the first sentence is the chapter heading. It
  may be absent. Without a chapter heading, that opening section has no
  section heading. A verse project has no section heading. A mixed text is
  a prose project, so its prose sections may have section headings. A verse
  section still has none.
- A section may have several subsection headings. One cannot be the first
  sentence of a section, and in the section that opens a chapter it cannot
  be the second sentence either. Verse uses these same slots and may still
  have subsection headings.
- A verse section's menu name stays ``Lines N-M``. A chapter heading does
  not replace that label.

The **Mark as ...** menu offers the role that the sentence's slot allows,
including on the first sentence of the project. **Not a heading** clears
whatever role that sentence has.

D2. The stored title is the heading's Old English
--------------------------------------------------

Marking a chapter or section heading stores that sentence's Old English
text as the division's title and sets ``title_auto`` false. Later edits to
that Old English update the stored title. A subsection heading does not
write a title.

Clearing a chapter heading stores ``Chapter N`` with ``title_auto`` true.
Clearing a section heading stores ``Section N`` with ``title_auto`` true.
Those generated names are not official titles. Clearing a chapter heading
also clears a section heading on the second sentence, because that slot
is legal only while the chapter heading is present. A dialog tells the
translator that this happened. Subsection headings that are still in a
legal slot stay.

D3. The reading prints the sentence once
-----------------------------------------

Full Translation, the PDF, the DOCX export, the Old English text export,
and the Translation export do not print a separate title line. The
heading sentence is printed in place.

- Old English column and Old English export: the sentence's Old English.
- Full Translation, the PDF, and the DOCX, on the Modern English side: the
  sentence's Modern English. If that is empty, those three views show the
  Old English again.
- Translation export: the Modern English only. An empty translation stays
  empty. This supersedes ADR 0003 where that ADR includes official title
  lines in either ``.txt`` export, and where an empty translation would
  otherwise be filled.
- The sentence card keeps the stored casing.

Chapter headings are bold and in capitals in Full Translation, the PDF,
and the DOCX. On a PDF or DOCX page the heading has little space above
and more below, because the page edge already separates it. In Full
Translation a chapter heading that is the first sentence of the text has
that same small gap above. A later chapter heading has a larger gap
above, so it does not sit against the previous sentence. The PDF and the
DOCX start a new page before a chapter heading unless that heading is the
first sentence of the text. The PDF break is one break for both columns.
The current exporter writes the whole Old English stream, then switches
column, then writes the whole Modern English stream, so a break inside
one stream does not meet the other column. Full Translation does not
insert a page break.

In the DOCX, a heading sentence is the heading text only. It does not get
the sentence number or the annotation glosses that body sentences get.

Section headings are bold, in their own case, with equal space above and
below, in those three views. Subsection headings are italic, in their own
case, with equal space above and below, tighter than a section heading,
in those three views. Plain-text exports do not apply this styling.

D4. Moves and deletion
----------------------

A change that would leave a heading outside its legal slot is refused,
including merging a heading sentence with a neighbor. The warning tells
the translator to clear the heading first.

Deleting a chapter or section heading removes that sentence and reverts
the division title as in D2. Every heading whose index inside its own
section changed is checked again. One that now sits in an illegal slot is
cleared. The check stops at that section: the next chapter's headings are
left alone. The same dialog names each heading that was cleared. Ordinary
text that slides up is left alone.

D5. Import and existing projects
--------------------------------

The heading role is stored on the sentence and written in the project
file (``heading_role`` on the sentence: ``chapter``, ``section``,
``subsection``, or absent). ``SentenceJson`` currently forbids unknown
fields, so the schema has to grow with the export. Import restores the
role. It does not invent a heading from the title when the role is
already present.

On Wyrdcraeft ingest, on import of a file that has no ``heading_role``,
and in one data migration for projects already stored: if ``title_auto``
is false and the chapter title is not character-for-character equal to
the first sentence's Old English, insert a new first sentence with that
Old English and mark it the chapter heading. If the strings are equal,
mark the first sentence and do not insert another. No case folding and
no whitespace normalization. Generated names (``title_auto`` true),
including ``Lines N-M`` and a stored ``Chapter N``, are not turned into
sentences. Section and subsection headings are not reconstructed from
titles. They survive only through ``heading_role``.

Consequences
============

- The migration inserts sentences and renumbers the following sentences.
  Undo history does not cover it. A pre-migration backup already runs
  before migrations.
- Heading marks are ordinary undoable commands, like the other **Mark as
  ...** actions.
- ``visible_titles`` stops supplying a separate line. Callers in Full
  Translation, the PDF, the DOCX, and the reading-text export drop that
  line together.
- The in-app Headings topic and :doc:`/overview/headings` describe the
  rules. Screenshots for that overview page are still placeholders.
- In a verse project **Mark as ...** never lists **Section heading**.
  **Chapter heading** on a later chapter stays off that menu until every
  earlier chapter has a chapter heading.

Alternatives considered
=======================

Printing the stored title and also styling the sentence keeps the
duplicate this change removes. Leaving an untranslated heading blank
makes the empty side look like a gap. Putting that Old English fallback
into the Translation export would publish source text in a file ADR 0003
keeps in Modern English. Replacing a verse section's ``Lines N-M`` label
with ``Section N`` throws away the line range translators use to
navigate. Skipping the migration keeps official titles in the chapter
menu and drops them from the reading. Forbidding subsection headings in
verse was not required. The slot rules already keep them off the first
lines. Offering a section heading inside a verse project was rejected
because those sections are already named by their line range. Letting a
translator name a later verse chapter before the earlier ones was
rejected so the chapters are named from the start of the text.

Related
=======

Supersedes the official-title lines in :doc:`adr_0003_project_export_reading_text`.
The rest of ADR 0003 stands.

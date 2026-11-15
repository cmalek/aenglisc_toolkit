========
Headings
========

A heading is a sentence you mark. The reading prints that sentence once:
Old English on the Old English side, Modern English on the Modern English
side. The chapter and section names in the toolbar are not printed again
above it.

Where a heading can sit
=======================

**Chapter heading.** One per chapter. It is the first sentence of that
chapter's first section. A verse project is one in which every sentence
is verse. A text that mixes prose and verse, such as Cædmon's Hymn, is a
prose project. In a verse project the chapters are named from the start of
the text: a later chapter offers a chapter heading only after every earlier
chapter has one on the first sentence of its first section. A prose project
may name a later chapter first. On the sentence card the text keeps the
casing you imported or typed. In the PDF and the DOCX it is capitals and
bold, with a small gap above and a larger gap below, and it starts a new
page unless it is the first sentence of the text. Both PDF columns start
that page together. In the DOCX the heading is the heading text alone: no
sentence number and no annotation glosses. In Full Translation the first
heading of the text has that small gap above. A later chapter heading has
a larger gap above, so it does not sit against the previous sentence.

.. TODO: screenshot shot-heading-chapter-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-heading-chapter-menu.png
   :alt: Mark as ... open on the first sentence of the first chapter,
         offering Chapter heading. The sentence text on the card is in its
         original case.

**Section heading.** One per section, in a prose project. It is the first
sentence of the section. In the section that opens a chapter, it can be
the second sentence only while the first sentence is the chapter heading,
and you can leave that sentence unmarked. It is bold, in its own case,
with the same amount of space above and below. A verse project does not
offer a section heading. A text that mixes prose and verse is a prose
project, so its prose sections may.

.. TODO: screenshot shot-heading-section-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-heading-section-menu.png
   :alt: Mark as ... open on the second sentence of a prose chapter's first
         section, offering Section heading.

**Subsection heading.** A section can have more than one. Use it for a
rubric inside a section, such as the parts of Wulfstan's *Be ðēodwitan*.
It cannot be the first sentence of a section. In the section that opens
a chapter, it cannot be the first or second sentence either. It is
italic, in its own case, with a smaller equal gap above and below.

.. TODO: screenshot shot-heading-subsection-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-heading-subsection-menu.png
   :alt: Mark as ... open on a later sentence in a section, offering
         Subsection heading.

A verse project has no section heading. **Mark as ...** does not list one
on the second sentence of the opening section, or on the first sentence of
a later section. A later sentence can still be a subsection heading, in
the same slots as prose. The section menu keeps the line range,
``Lines N-M``. A chapter heading leaves that name in place. On the first
sentence of a later chapter, **Chapter heading** waits until every earlier
chapter already has one. A mixed text such as Cædmon's Hymn offers it
immediately.

.. TODO: screenshot shot-verse-section-menu, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-verse-section-menu.png
   :alt: The section dropdown, not Mark as, on a verse section, showing a
         Lines N-M name.

.. TODO: screenshot shot-verse-no-section-heading, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-verse-no-section-heading.png
   :alt: Mark as ... open on verse lines 101-105, the first sentence of a
         later section. The menu lists Not Paragraph Start, Not Section
         Start, and Chapter Start, and has no Section heading.

Marking and clearing
====================

Open **Mark as ...** on the sentence card. The menu lists the heading
that this slot allows, together with the usual paragraph, section, and
chapter start commands. The first sentence of a project can be marked as
a chapter heading.

**Not a heading** clears the role on that sentence. The chapter menu then
shows ``Chapter N``, or the section menu shows ``Section N``. Those
generated names are not treated as titles of the text. Clearing a chapter
heading also clears a section heading on the second sentence, because
that place is legal only while the chapter heading is there. A dialog
names that sentence and the new section name. A subsection heading that
is still in a legal slot stays.

.. TODO: screenshot shot-heading-cleared-dialog, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-heading-cleared-dialog.png
   :alt: The dialog shown after clearing a chapter heading that also
         cleared the section heading on the next sentence.

These actions are undoable with **Ctrl+Z**, like the other **Mark as ...**
commands.

The chapter or section name in the toolbar is the heading sentence's Old
English. Editing that Old English updates the name. Capitals in the
reading views are display only. The sentence card and the stored text
keep the case you typed.

If the heading has no Modern English yet, the Full Translation window,
the PDF, and the DOCX show the Old English on the Modern English side as
well. Other sentences still show ``[...]`` when the translation is empty.

How the reading looks
=====================

.. TODO: screenshot shot-heading-full-translation, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-heading-full-translation.png
   :alt: The Full Translation window with a chapter heading in capitals,
         a section heading in bold, a subsection heading in italics, and
         an untranslated heading showing Old English on the right.

The PDF and the DOCX use the same weight and case. A chapter heading
starts a new page in those two exports, unless it is the first sentence
of the text, and both PDF columns start that page together. The Full
Translation window scrolls, so it does not insert a page break. A later
chapter heading there has a larger gap above it.

.. TODO: screenshot shot-heading-pdf, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-heading-pdf.png
   :alt: A PDF page whose top line is a later chapter's heading, in
         capitals, with Old English on the left and Modern English on
         the right.

The Word export uses those same styles. Its heading paragraph is the
heading text alone. Sentence numbers and annotation glosses stay on the
body sentences.

The plain-text exports print the heading sentence with the rest of the
text and do not add a title line. They do not change case or weight. The
Translation export leaves an untranslated heading empty.

Deleting a heading, and moves that would break one
===================================================

Deleting the sentence removes it. The toolbar name goes back to
``Chapter N`` or ``Section N``. Every heading in that same section whose
place changed is checked. One that no longer sits in a legal slot is
cleared, and the dialog names each of them. Headings in the next chapter
stay. Ordinary text that slides up is left as it is.

Adding a sentence in front of a heading, merging it with a neighbor, or
merging the chapter or section out from under it, is refused while the
heading would no longer sit in a legal slot. Clear it with **Not a
heading** first.

.. TODO: screenshot shot-heading-refused, see doc/screenshot_shotlist.md
.. thumbnail:: /_static/screenshot-heading-refused.png
   :alt: The warning shown when a move would leave a chapter heading
         outside the first sentence of its chapter.

Imported titles
===============

When a text is imported, an official chapter title is compared character
for character with the first sentence's Old English. If they differ, that
title is inserted as a new first sentence and marked as the chapter
heading. If they are the same, that sentence is marked and nothing is
inserted. A generated name, including ``Chapter N`` and a verse section's
``Lines N-M`` label, is not inserted as a sentence. The heading role is
saved in the project file. An older file with no role still gets a
chapter heading from an official chapter title. Section and subsection
headings are kept only when the file records them. Projects already in
the database are updated the same way once, when the database migrates.

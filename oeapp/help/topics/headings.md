# Headings

A heading is a sentence you mark from **Mark as ...**. Full Translation, the PDF, the DOCX export, and the plain-text exports print that sentence once. They do not print the chapter or section name again on a line of its own.

The Old English side uses the sentence's Old English. The Modern English side uses the translation. If you have not translated the heading yet, the Full Translation window, the PDF, and the DOCX show the Old English on the Modern English side too, so the heading is still visible. Other empty translations still show `[...]`.

The sentence card always shows the text in the case you imported or typed.

## Where Each Heading Goes

A sentence has one heading role at most.

### Chapter Heading

One per chapter. It has to be the first sentence of that chapter's first section. The first sentence of a project can be one. The menu is available there.

In a verse project the chapters are named from the start of the text. A verse project is one in which every sentence is verse. A text that mixes prose and verse, such as Cædmon's Hymn, is a prose project and may name a later chapter first. In a verse project, a later chapter offers a chapter heading only after every earlier chapter has one on the first sentence of its first section.

In the PDF and the DOCX it is bold and in capitals. A new page starts before it, unless it is the first sentence of the text, and both PDF columns start that page together. On that new page the gap above is small and the gap below is larger. In the DOCX the heading is the heading text alone: no sentence number and no annotation glosses. Full Translation does not start a new page. The first heading of the text has a small gap above. A later chapter heading has a larger gap above, so it does not sit against the previous sentence.

### Section Heading

One per section, in a prose project. It is the first sentence of the section. In the section that opens a chapter, it can be the second sentence only while the first sentence is the chapter heading. You can leave that second sentence unmarked.

It is bold, in its own case, with the same space above and below. A verse project does not offer a section heading. A text that mixes prose and verse, such as Cædmon's Hymn, is a prose project, so its prose sections may. A verse section can still have subsection headings, and it keeps its `Lines N-M` name in the section menu. A chapter heading does not replace that name.

### Subsection Heading

A section can have several. Use one for a rubric inside a section, such as the parts of Wulfstan's *Be ðēodwitan*. It cannot be the first sentence of a section. In the section that opens a chapter, it cannot be the first or second sentence either. Verse uses the same slots.

It is italic, in its own case, with a smaller equal gap above and below.

## The Toolbar Name

Marking a chapter heading stores that sentence's Old English as the chapter name. Marking a section heading does the same for the section. Editing the Old English later updates the name. A subsection heading does not change the section name.

**Not a heading** clears the role. The chapter name becomes `Chapter N`, or the section name becomes `Section N`, using that division's number. Those generated names are not titles of the text, and they are not inserted as sentences later.

If you clear a chapter heading, a section heading on the second sentence is cleared too, because that place is legal only while the chapter heading is there. A dialog names the sentence and the new section name. A subsection heading that is still in a legal slot stays.

## Deleting and Moving

Deleting a chapter or section heading removes the sentence and resets that division's name the same way. Every heading in that same section whose place changed is checked. One that no longer sits in a legal slot is cleared, and the dialog names each of them. Headings in the next chapter stay. Ordinary sentences that slide up are unchanged.

The app refuses a change that would leave a heading in the wrong slot. That includes **Add Sentence → Before** on a heading, merging a heading with the sentence before or after it, and **Not Chapter Start** or **Not Section Start** when the heading would no longer be first in its division. Clear the heading, then make the change.

Heading marks undo with **Ctrl+Z**, like the other **Mark as ...** actions.

## Import

An official chapter title is compared character for character with the first sentence's Old English. If they differ, the title is inserted as a new first sentence and marked as the chapter heading. If they are the same, that sentence is marked and nothing is inserted. A generated name, including `Chapter N` and `Lines N-M`, is not turned into a sentence. The heading role is saved in the project file. An older file with no role still gets a chapter heading from an official chapter title. Section and subsection headings are kept only when the file records them. Projects you already have are updated once, when the database migrates.

Plain-text export prints the heading sentence with the other sentences. It does not add a title line, and it does not change case or weight. The Translation export leaves an untranslated heading empty.

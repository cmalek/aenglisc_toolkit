.. _adr_0010_typed_run_undo:

=====================================================
ADR 0010: A Typed Run is one Modern English Undo Step
=====================================================

:Status: Accepted
:Date: 2026-10-24

Context
=======

Each change in a sentence's Modern English editor pushes its own
``EditSentenceCommand``. Typing a sentence of translation can fill the
50-step cap and drop earlier Undo Steps. The editor is a ``QTextEdit``, so
it also has Qt's document undo. Ctrl+Z inside the box undoes one character
there, and the following ``textChanged`` records that undo as a new
application command.

``EditSentenceCommand`` asks for a full project reload on undo and redo,
for Old English and Modern English alike. A translation change does not
add, remove, or retokenize sentences. A reload throws away the translator's
place in the project.

Old English is different: the translator edits, then saves once. That save
is one command. A note is one command when it is saved. ``CONTEXT.md``
defines **Typed Run** and **Modern English Translation**.

Decision
========

D1 — A Typed Run is one Undo Step
---------------------------------

A Typed Run is the Modern English changes on one sentence while the
translator is still working on that sentence. Typing, deleting, and
pasting in that work are the same run. A pause keeps the run open. Focus
leaving the Modern English editor does not end it by itself.

One Undo reverts the whole run. Redo restores it. If that sentence's card
is on screen, the translator stays there. If it is not, Undo and Redo
bring it back, as D2 says.

Document undo on that editor is off. That alone does not deliver the key.
On PySide 6.12.0, a ``QTextEdit`` with document undo disabled still accepts
the Undo and Redo key sequences, and a window action bound to those
standard keys does not run. An event filter that consumes
``ShortcutOverride`` for those two keys, so the editor never accepts them,
does let the window action run. The Modern English editor has that filter.
The offscreen probe's Undo binding was Ctrl+Z. The filter matches
``QKeySequence.StandardKey``, so it follows whatever binding the platform
reports.

The run stays open while the translator is still working on that sentence:
a look at it, and a menu dismissed with no choice. It ends when that work
stops.

A menu does not end the run. That includes the menu bar, a ``QMenu``, and
the Add Sentence and Mark as menus on the card. Opening one, reading it,
and dismissing it without a choice leaves the run open. Choosing an action
from Add Sentence or Mark as ends the run, because a sentence action has
happened. Merge with next, Delete, Edit OE, and Add Note end it for the
same reason.

The highlighting combo on that same card does not end the run. Changing the
highlight is how the translator looks at the sentence while writing. Qt
gives that popup the same focus reason as a menu. The exception is this
combo, not the focus reason. Show Token Table and Hide Token Table do not
end the run either. That button only shows or hides the table.

Selecting an Old English token on that same card does not end the run,
whether the click is in the token table or a single click in the Old
English text. A single click is how the annotation is shown. Focus may
move to the Old English text or the token table, and the run stays open.
A single click on a note on that card does not end the run. It highlights
the note. A token on a different sentence ends the run.

Opening the annotation modal ends the run. Three gestures open it: a
double-click on a token or an idiom in the Old English text
(``annotate_token``), a double-click on a token in the token table, and
the A key on that table (``annotation_requested``). Each reaches
``_open_annotation_modal``. Dismissing the modal without saving does not
reopen the run.

A double-click on an existing note ends the run. It opens the note editor.
Add Note ends the run when it is clicked. Edit OE ends the run when it is
clicked. Cancel Edit, and dismissing Add Note without saving, do not
reopen the run.

Choosing a chapter or a section ends the run. The previous and next buttons
do too, because they make the same choice. The section now on screen gives
focus to its first sentence, on that sentence's Old English text, as
Shift+Up already does. Choosing a chapter shows that chapter's first
section, then does the same. Today ``load_section`` rebuilds the cards and
does not move focus. This decision says it must.

A menu item that then moves focus off the sentence ends the run. Find
focuses the search box, so Find ends the run. A dialog opened from a menu
ends the run. Changing the search scope ends the run. Opening that selector
and dismissing it without a change does not.

Destroying the editor ends the run. Switching chapter or section rebuilds
the cards, so the run ends. Undo History stays, as
:ref:`ADR 0009 <adr_0009_project_scoped_qundostack>` says, because the
project did not change.

Coming back after the run has ended starts another one, even when no other
Undo Step happened in between. Returning from the highlighting control,
Show Token Table, a token on the same sentence, or a single click in its
Old English text or on one of its notes does not, because that run is still
open. Undo and Redo close the run. Typing afterward is a new run and does
not merge into the step Undo revealed. Consecutive changes in the open run
merge on the
``QUndoStack``. ``push()`` calls ``redo()`` on the new command and then
``mergeWith()``. The merged command stores the text from the start of the
run and the latest text, both absolute. ``redo()`` writes that latest
text. ``mergeWith()`` keeps the original text as what Undo restores. A
change after the run has closed does not merge into it.

Writing the editor from Undo or Redo is not a focus action and does not
start a new run.

D2 — Undo returns to that sentence
----------------------------------

Undo and redo of a Typed Run update that sentence's translation and leave
the translator on that sentence. They do not rebuild the project when the
card is already on screen. The update writes the translation into that
sentence's editor. ``refresh()`` reloads tokens and theme and does not
write the translation. ``reload_project()`` rebuilds every card and drops
the translator's place. Neither is how a Typed Run is undone while its
card is visible.

When the sentence is not on screen, Undo and Redo load the section that
contains it, scroll to that sentence's card, and then apply the step.
The translation text blinks after that step, and only in this case, so
the change is visible on a card that was not being watched. The stack
entry stores the sentence's database id, and that id is what is loaded.
The card widget is not the identity. ``load_section`` today rebuilds the
cards and does not move focus. A chapter or section choice still focuses
the first sentence of the section now on screen, as D1 says. This
off-screen Undo path is the other time focus moves to a sentence. That
load is part of the Undo Step. It does not start a new run, and the write
into the editor does not either. The section loaded is the one that
contains the sentence now.

An Old English save, a saved note, and any edit that changes structure
still rebuild when they already do.

D3 — Old English and notes are not a Typed Run
----------------------------------------------

An Old English edit becomes one Undo Step when the translator saves it. A
note becomes one Undo Step when the translator saves it. While the Old
English text is read-only, and while the token table has focus, Undo and
Redo keys perform the application step. After Edit OE the Old English text
takes those keys, one character at a time, until Save or Cancel. The note
dialog takes them the same way until it closes. The Edit menu still
performs the application step in every case. The read-only full-translation
view has no undo of its own.

D4 — Stack entries follow the sentence and the token
----------------------------------------------------

A stack entry stores the database id of the sentence it changes, and, for
an annotation, the database id of the token or idiom. The number shown on
the card is the sentence's display order. Adding, removing, or reordering
sentences changes display order. A sentence that still exists keeps its
database id. The card widget is thrown away and built again by
``load_section``. That rebuild is not a new sentence.

After sentences are added, removed, or reordered, the stack is walked.
An Old English edit walks the annotation entries even when no sentence
was added or removed.

- An entry whose sentence no longer exists is dropped, except the entry
  that removed it. Undo of that removal can still restore the sentence.
  Older steps for the removed sentence are gone, including its annotation
  steps. The removal command already stores the annotations it restores,
  so dropping those older steps does not drop that capture. Undo of the
  removal restores the sentence as the removal command captured it, under
  whatever new database id the restore assigns, and the removal command
  records that id.
- An entry whose sentence still exists keeps that database id. Any display
  order stored on the entry is updated to the sentence's current display
  order, so the entry still names that sentence. Database ids are not
  renumbered onto a different row.

Annotation entries are walked with the same rules.

- A token moved onto another sentence, as a merge does, keeps its token
  id. The annotation entry is updated to that token's new sentence id.
- An Old English edit re-tokenizes through ``Token.update_from_sentence``.
  A token whose surface still matches keeps its id. An annotation entry
  for that token stays, and its sentence id is updated if the token's
  sentence changed. A token that no longer matches is deleted. Annotation
  entries for that token, and for an idiom that edit removed, are dropped.

Consequences
============

- One Undo after typing a sentence of Modern English reverts that run,
  including after a menu, the highlighting control, Show Token Table, a
  single click in the Old English text, a token on that sentence, or a
  single click on one of its notes. Earlier history is no longer evicted
  by the keystrokes.
- Choosing a chapter or section, opening the annotation modal, running
  Add Sentence or Mark as, double-clicking a note, or leaving the sentence
  starts the next run. A second run is a second Undo Step.
- A chapter or section choice puts focus on the Old English text of the
  first sentence now on screen.
- Undo of a translation writes the earlier text into the editor when that
  card is on screen. When it is not, Undo loads that sentence's section,
  scrolls to the card, applies the step, and blinks the text it wrote.
- While the Old English text is read-only, or the token table has focus,
  Undo and Redo keys are the application step. After Edit OE, and in the
  note dialog, the keys undo characters and the menu still performs the
  application step. Save records one step.
- The menu text for a Typed Run is "Edit translation", from ADR 0009.
- Until this is implemented, each Modern English change is still its own
  command and undo still reloads the project.

Alternatives considered
=======================

- **One command per keystroke.** Rejected: it is today's behavior. A
  sentence of typing fills the 50-step cap, and one Undo reverts one
  character.
- **Commit one command when the editor loses focus.** Rejected: Undo while
  the translator is still typing would not revert the run.
- **Use the editor's document undo as the run.** Rejected: it undoes one
  character, then the application records that as a new command. It is a
  second history.
- **Rebuild the project on Undo of a Typed Run.** Rejected: the sentence
  is still there. A rebuild drops the translator's place for a change that
  does not affect structure.
- **End the run on every focus change, including a menu.** Rejected:
  opening Undo and dismissing it would split the sentence the translator
  is still typing.
- **Treat every popup as a menu.** Rejected: a chapter or section choice
  navigates away from the sentence being translated. The highlighting
  combo shares the popup focus reason and stays inside the run, because
  it does not navigate.
- **Opening the annotation modal is only another look.** Rejected: a
  double-click in the Old English text, a double-click in the token table,
  and the A key all open that modal, and each ends the run. Edit OE, Add
  Note, and a double-click on a note are actions in the same way. A single
  click stays inside the run.
- **Opening Add Sentence or Mark as ends the run.** Rejected: no sentence
  action has happened until a choice is made.

Related
=======

- ``CONTEXT.md`` terms **Typed Run** and **Modern English Translation**.
- :ref:`ADR 0009 <adr_0009_project_scoped_qundostack>` — the stack those
  steps are pushed on, and the menu text "Edit translation".
- Trello card 121. Cards 120 and 129 are ADR 0009.

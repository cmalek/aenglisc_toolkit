.. _adr_0009_project_scoped_qundostack:

===========================================================
ADR 0009: Application undo is one project-scoped QUndoStack
===========================================================

:Status: Accepted
:Date: 2026-10-24

Context
=======

Undo is a hand-built ``Command`` and ``CommandManager``: an undo list, a
redo list, and a cap of 50. A command that does not apply is left off the
list. There is no merge, no macro, and no clean-state mark. One
``CommandManager`` lives on the app context for the whole session.
``CommandManager.clear()`` is never called. A new manager is created only
when the app context resets, so opening another project leaves the old
steps in place. Undo can still change a sentence in a project the
translator is not looking at.

There is no Edit menu. Undo, Redo, and Find are window shortcuts:
Ctrl+Z, Ctrl+R, Ctrl+Shift+R, and Ctrl+F. Help text documents those keys.
Qt's standard keys differ by platform. On macOS, Redo is Command+Shift+Z,
not Ctrl+R.

``QAction.MenuRole`` can move About, Preferences, and Quit into the macOS
application menu. It has no Undo, Redo, or Find role. The default role,
``TextHeuristicRole``, guesses from the action's text.

Each ``QTextEdit`` also keeps Qt's document undo. The Modern English box,
the Old English editor, and the note dialog all have it. Ctrl+Z inside one
of those undoes in the widget. The application history sees a command only
when one is saved.

``QUndoStack`` owns each command after ``push()``, deletes a command that
was undone once a new command is pushed, and can expose Undo and Redo as
actions. ``CONTEXT.md`` defines **Undo History**.

Decision
========

D1 — One QUndoStack replaces CommandManager
-------------------------------------------

``QUndoStack`` replaces ``CommandManager``. Existing commands stay
responsible for their database changes and are wrapped as ``QUndoCommand``
objects. The stack's undo limit stays 50. A command that does not apply
does not remain on the stack.

The stack owns the commands it is given. One stack lives on the app
context, shared by every sentence card.

D2 — Undo History belongs to the open project
---------------------------------------------

Undo History clears when the open project changes. The current project id
changing, including to none when the project is closed or deleted, is that
change. Setting the id to the value it already has does not clear.
``load()`` of the project that is already open takes that path and keeps
the history.

Appending Old English text clears the history even though the project id
stays the same. Append changes sentences and is not an Undo Step, so a
later Undo of a merge or a deleted sentence would replay display-order
edits against sentences the append added. Edit Project changes metadata
and does not clear the history.

Moving among chapters or sections keeps the history. The history is not
saved with the project. Restoring a backup already quits the application,
so that path drops the in-memory history with the process.

D3 — Edit menu: Undo, Redo, and Find
------------------------------------

An Edit menu holds Undo, Redo, and Find. Undo and Redo come from
``QUndoStack.createUndoAction()`` and ``createRedoAction()``. Find still
focuses the search box. All three use ``QKeySequence.StandardKey``, so each
platform gets its own keys. Their menu role is ``NoRole``, so macOS leaves
them on the Edit menu.

The window shortcuts Ctrl+Z, Ctrl+R, Ctrl+Shift+R, and Ctrl+F go away.
N, Shift+N, Escape, and the scroll shortcuts stay window shortcuts.

In the Modern English editor, the Undo and Redo keys and the menu items
are the same operation. They stay the same while the translator is looking
at that sentence's read-only Old English text or its token table: those
widgets do not take the Undo key, so the application step still runs.
After Edit OE the Old English text is editable and takes the keys, one
character at a time. The note dialog takes them the same way. The menu
items still perform the application Undo Step. :ref:`ADR 0010 <adr_0010_typed_run_undo>`
says when that step is a Typed Run. Stack entries are kept aligned with
the sentences and tokens they name, as ADR 0010 decides.

``oeapp/help/assets/keybindings.html`` and the macOS help bundle's
``keybindings.html`` both change. Each lists every Undo, Redo, and Find
binding ``QKeySequence.StandardKey`` reports for the platform that copy
is for. One chord is not the whole set.

Undo and Redo name the action in plain language, with no database ids. The
command texts are:

- Edit translation
- Edit Old English
- Merge sentences
- Add sentence
- Delete sentence
- Split paragraph
- Merge paragraphs
- Split section
- Merge sections
- Split chapter
- Merge chapters
- Annotate
- Apply remembered annotations
- Propagate annotation
- Add note
- Update note
- Delete note

D4 — Left unchanged
-------------------

No command macros. No current gesture pushes more than one command, and
:ref:`ADR 0002 <adr_0002_idiom_creation_undo>` already kept idiom creation
as one command. There is no clean-state tracking. The Old English editor
and the note dialog keep per-character undo until the translator saves.
The full menu bar, and making annotation paste undoable, are separate work.

Consequences
============

- ``CommandManager`` and its two lists go away. Call sites and tests that
  build a ``CommandManager`` follow the stack.
- The oldest step still disappears after 50. A Typed Run, decided in
  :ref:`ADR 0010 <adr_0010_typed_run_undo>`, is what stops keystrokes from
  filling that budget.
- A different project, closing, deleting, or appending Old English text
  forgets Undo and Redo. Work already saved stays saved. Opening the
  project that is already open does not forget them.
- Redo is no longer Ctrl+R or Ctrl+Shift+R. Help that still says so is
  wrong, in both help copies.
- On PySide 6.12.0, ``QUndoStack.push()`` keeps the Python command alive
  after the caller's reference is dropped and garbage collection runs.
  ``undo()`` and ``redo()`` still called the Python methods. The
  implementation does not keep a second list of commands. A later PySide
  that stops holding the wrapper has to be checked again, because Undo
  would then call a destroyed object.
- Until that implementation lands, the running code is still
  ``CommandManager``.

Alternatives considered
=======================

- **Keep CommandManager and teach it to merge.** Rejected: Undo and Redo
  would still be custom lists beside Qt's action and shortcut machinery.
- **Keep every step for the session.** Rejected: 50 stays. The cap was
  harmful because each keystroke was its own step, which ADR 0010 removes.
- **Keep one history across projects.** Rejected: Undo could change a
  project that is not on screen. A Typed Run undo would not even refresh
  that screen.
- **Shortcuts only, with no Edit menu.** Rejected: the stack's Undo and
  Redo actions need a menu, and Find belongs with them.
- **A macOS menu role for Undo, Redo, or Find.** Rejected: Qt 6.8 has no
  such role.
- **Clear history on every ``load()``.** Rejected: reloading the open
  project is not a change of project. Append is the in-place sentence
  change that clears history, because it is not an Undo Step.

Related
=======

- ``CONTEXT.md`` term **Undo History**.
- :ref:`ADR 0002 <adr_0002_idiom_creation_undo>` — idiom creation stays one
  command, and undo deletes the idiom row.
- :ref:`ADR 0010 <adr_0010_typed_run_undo>` — a Typed Run is one Undo Step,
  and stack entries follow the sentence and token they name.
- Trello cards 120 and 129. Card 121 is ADR 0010.

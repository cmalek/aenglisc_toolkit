.. _adr_0002_idiom_creation_undo:

===============================================================
ADR 0002: Idiom-creation undo deletes the idiom row
===============================================================

:Status: Accepted
:Date: 2026-09-04

Context
=======

As part of the F4 audit fix (folding the direct ``idiom.save()`` ORM write
in ``SentenceCard._on_idiom_annotation_applied`` into a command), idiom
creation is combined with ``AnnotateTokenCommand`` so "create idiom +
annotate it" is a single undoable action, rather than two separate
undo-stack entries or a macro/composite command.

``AnnotateTokenCommand``'s existing ``undo()`` for a brand-new token
annotation only blanks the annotation's fields via ``from_json(before)``; it
never deletes the row. Idiom creation deliberately diverges from that
precedent.

Decision
========

Undoing an idiom-annotation creation deletes the newly created ``Idiom``
row, whose ``Annotation`` cascade-deletes with it (``Idiom.annotation`` uses
``cascade="all, delete-orphan"``, the same ``session.delete(idiom)`` pattern
already used in ``Token._update_idioms_for_token_changes``) — rather than
leaving an orphaned, un-annotated idiom span behind.

We chose this because an orphaned blank annotation on an existing token is
invisible and harmless, but an orphaned ``Idiom`` is a structural object — a
visible span grouping in the text — that would look like a lingering
artifact of an action the translator believes they undid. Consistency with
the token-annotation code path was judged less important than undo actually
looking undone.

Redo
----

``CommandManager.redo()`` re-invokes ``execute()``. Since ``undo()`` deletes
the idiom row, a naive re-``execute()`` would try to re-insert the same
Python ``Idiom`` instance with its now-stale (deleted) primary key still
set. ``AnnotateTokenCommand.execute()`` resets ``self.new_idiom.id = None``
immediately before every insert, so redo always gets a genuinely new row —
the old id is never reused.

Alternatives considered
========================

- **Two separate** ``command_manager.execute()`` **pushes**
  (``CreateIdiomCommand`` then ``AnnotateTokenCommand``). Rejected: the user
  experiences "annotate this new idiom" as one action; two stack entries
  would let a single undo press clear the annotation while leaving the
  now-orphaned idiom in place.
- **A macro/composite command** wrapping both steps as one undo-stack
  entry. Rejected for now: no such pattern exists anywhere in
  ``oeapp/commands/abstract.py``'s ``Command``/``CommandManager``;
  introducing one for this single call site is more infrastructure than the
  problem needs.

Consequences
============

- Idiom creation and its annotation share one undo-stack entry; undoing it
  removes the idiom span entirely rather than leaving a blank annotation
  behind.
- Redo always produces a genuinely new ``Idiom`` row (id reset before every
  insert), so redo after undo cannot collide with the deleted row's old
  primary key.
- This diverges from the plain-token-annotation undo precedent
  (blank-in-place rather than delete-row); future readers of
  ``oeapp/commands/`` should not assume all annotation undo behaves
  identically.

Related
=======

- Implementation plan:
  ``docs/superpowers/plans/2026-09-04-f4-sentence-card-controller-split.md``
  (Task 1), including its redo-specific test.

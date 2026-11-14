.. _adr_0012_explicit_runtime_session:

==========================================================
ADR 0012: Pass the runtime session into model classmethods
==========================================================

:Status: Accepted
:Date: 2026-11-02
:Accepted: 2026-11-03

Context
=======

:ref:`adr_0011_runtime_session_freeze` keeps one SQLAlchemy session for
the desktop process. ``get_runtime_session`` returns it.
``SessionMixin._get_session`` was how model classmethods reached it.
``save``, ``delete``, commands, and some services used the same mixin
method.

A classmethod that calls ``cls._get_session()`` hides which session it
reads and writes. A caller that already holds the runtime session cannot
pass that object in. A test cannot ask the method to use a different
session than the one registered on ``_RUNTIME_STATE``. The freeze census
counts the lookup inside the classmethod, so a UI call into that
classmethod does not show up as a new lookup.

The F8 follow-up card asks callers to pass the one desktop runtime
session into the model classmethods that call ``cls._get_session()``.
``SessionMixin._get_session`` stays for call sites that migration does
not cover. ADR 0011 D5 allows the freeze allowlist to gain a lookup only
where a caller has to obtain the runtime session in order to pass it on,
and only in the same change that removes the classmethod lookup. The
test cannot see that pairing.

The working tree already follows the decision below. This ADR is the
record that should have been accepted before that edit.

Decision
========

D1 — One runtime session
------------------------

The process still has one registered runtime session. This decision does
not add a second writer, change the engine pool, or replace SQLAlchemy.
``get_runtime_session`` remains the only product ``SessionLocal()`` call.

D2 — Keyword-only ``session`` on the classmethods that look it up
-----------------------------------------------------------------

Each model classmethod that called ``cls._get_session()`` takes a
keyword-only ``session`` argument and uses that object. The
``cls._get_session()`` call inside that method is deleted. There is no
default. A call that omits ``session`` fails immediately.

The argument is keyword-only so existing positional arguments keep their
places. ``Token._create_new_token`` already takes ``session`` as a
positional parameter and is left that way. It passes that object into
``Annotation.exists``.

D3 — Forwarding classmethods take the same argument
---------------------------------------------------

These remembered-annotation classmethods do not call ``_get_session``
themselves. They only forward to methods that now require ``session``,
so they take the same keyword-only argument and pass it on:

- ``RememberedAnnotation.matches_in_scope``
- ``RememberedAnnotation.ambiguous_groups_for_scope``
- ``RememberedAnnotation.resolve_for_project``
- ``RememberedAnnotation.upsert_fields``
- ``RememberedAnnotation.upsert_from_token_annotation``

A classmethod that calls one of the migrated methods and is not in that
list obtains the runtime session once and passes it.
``Annotation.from_json`` and ``RememberedAnnotation.from_json`` do that
with ``get_runtime_session()``.

D4 — Callers pass the session they hold
---------------------------------------

A caller that already holds the runtime session passes that object.
That includes a local from ``self._get_session()``, and ``self.session``
on the importer, the ingest service, and the DOCX exporter.

A caller that does not hold one calls ``get_runtime_session()`` once in
that function and passes the result. It does not call ``_get_session``
inside the classmethod it is migrating. Tests are outside the freeze
scan. A test passes ``get_runtime_session()``, which is the session
``db_session`` registered.

D5 — ``_get_session`` stays where this migration stops
------------------------------------------------------

``SessionMixin._get_session`` remains the lookup for ``save``,
``delete``, command instance methods, and service methods this decision
does not convert. ``AnnotationPropagationService._meaning_targets`` and
``_project_tokens`` still call ``Annotation._get_session``.

D6 — The allowlist records the move
-----------------------------------

The same change updates ``ALLOWLIST`` in
``tests/test_runtime_session_freeze.py``. It drops each removed
classmethod ``_get_session`` count. It adds a ``get_runtime_session``
count only on a caller that had to obtain the session in order to pass
it. The test still checks that the dict matches the tree. It still
cannot see why a count moved.

Consequences
============

- A model classmethod no longer decides which session it uses. The
  caller does.
- Omitting ``session`` is a ``TypeError`` at the call, rather than a
  silent read of the process session.
- Callers that already held the session do not add a freeze lookup.
  Callers that did not add one ``get_runtime_session`` count, and the
  classmethod loses its ``_get_session`` count.
- ``save`` and ``delete`` still look the session up. An instance that
  was loaded on one session and saved after the runtime session changed
  still follows ``_get_session``, not the session that loaded it.
- ``Annotation.from_json`` and ``RememberedAnnotation.from_json`` still
  obtain the runtime session themselves. A caller of those two methods
  cannot pass a different session until they gain the same argument.
- The stale identity map after commands is unchanged. Every caller still
  passes the one runtime session.
- No help text changes. The runtime session is not a term in
  ``CONTEXT.md``.

Alternatives considered
=======================

- **Default ``session`` to ``cls._get_session()``.** Rejected: the
  hidden lookup would remain, and callers could keep ignoring the
  argument.
- **Put ``session`` first positionally.** Rejected: every existing
  positional call would shift, and a forgotten update would pass an id
  where a session belongs.
- **Thread ``session`` through ``save``, ``delete``, and every command
  in this change.** Rejected for this card. Those methods already call
  ``_get_session`` on the instance. The follow-up card stops at
  classmethods.
- **Give every service and command a constructor session now.** ADR 0011
  D4 already rejected that until classmethods use the session they are
  given. This decision is that classmethod step, not that injection.

Related
=======

- :ref:`adr_0011_runtime_session_freeze`, D5, which defers this migration
  and states what the freeze allowlist may record.
- F8 follow-up: https://trello.com/c/dNaoAIwU
- F8 freeze: https://trello.com/c/RqmuEu67

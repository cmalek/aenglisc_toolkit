.. _adr_0011_runtime_session_freeze:

==============================================================
ADR 0011: Freeze runtime-session lookups at today's call sites
==============================================================

:Status: Accepted
:Date: 2026-10-26
:Revised: 2026-11-01

Context
=======

Audit finding F8 (resolve order 10 of 12 in the 2026-09-13 architecture and
capability audit) is that one process-global SQLAlchemy session couples the
UI, the models, and the tests.

``oeapp/db.py`` keeps that session on ``_RUNTIME_STATE``.
``get_runtime_session`` returns it, and creates it with ``SessionLocal()``
when nothing is registered. ``set_runtime_session`` replaces it.
``clear_runtime_session`` clears it. ``AppContext`` in ``oeapp/state.py``
is the only product code that calls ``set_runtime_session`` or
``clear_runtime_session``. After a clear, the next ``get_runtime_session``
creates the session itself. ``get_session`` in the same module also calls
``SessionLocal()`` and yields that other session. Nothing calls
``get_session``. D7 deletes it. The 2026-11-01 revision does not.

``create_engine_with_path`` passes no ``poolclass``. For a file SQLite URL
the dialect's default pool is ``QueuePool``. The finding rejects adding a
pool as the remedy for the shared session. The engine already has the
dialect default.

Model classmethods, ``save`` and ``delete``, and commands reach the runtime
session through ``SessionMixin._get_session``.
``AnnotationPropagationService._meaning_targets`` and
``AnnotationPropagationService._project_tokens`` call
``Annotation._get_session``, which is that mixin method, so the count sits
on those two service methods. ``oeapp/commands/note.py``,
``oeapp/ui/sentence_card_controller.py``, and ``oeapp/ui/oe_text_edit.py``
call ``get_runtime_session`` directly. ``oeapp/ui/project_workspace.py``,
``oeapp/ui/notes_panel.py``, ``oeapp/ui/main_window.py``, and
``oeapp/ui/dialogs/note_dialog.py`` read ``app_context.session``, the
``AppContext`` property that calls ``get_runtime_session``. Services that
already looked the session up keep it on ``self.session`` and flush, add,
and commit through that attribute. ``note_dialog`` already takes an
optional session and falls back to ``app_context.session``. On 2026-10-28
the calls were bare names or attributes. The scanner does not resolve an
alias, ``getattr``, or a local other than ``app_context``.

Tests install and clear the session in ``tests/conftest.py`` (the
``db_session`` fixture) and in ``tests/test_state.py``.
``tests/test_commands.py`` calls ``get_runtime_session`` to roll back.
``tests/test_db.py`` calls ``SessionLocal()`` directly.

Fat ORM stays. SQLAlchemy stays. A second writer is outside the finding.
Passing an explicit session through every model classmethod is a larger
migration. F1 (resolve order 8) landed on 2026-11-01 in ``fd4e11e``. That
change left the export reads on ``MainWindowActions`` as
``app_context.session`` and added no lookup kind. F7 (resolve order 9) is
unfinished. F8's audit note said collaborators from those cards should take
an injected session. D4 does not require that injection. F7 forbids new
``_get_session`` call sites in the UI. A call from the UI into a model
classmethod is not one of those call sites: ``Annotation.get_by_idiom``
keeps its ``_get_session`` inside ``Annotation.get_by_idiom``.

Decision
========

D1 — One runtime session
------------------------

The desktop process keeps a single registered SQLAlchemy session, the
runtime session, on ``_RUNTIME_STATE``. ``set_runtime_session`` installs a
session it is given. ``get_runtime_session`` returns that session, and is
the only product function that creates the registered runtime session when
none is registered. ``clear_runtime_session`` clears it.

``get_session`` remains until D7. It calls ``SessionLocal()``, yields that
other session, and does not register it. It has no callers.

``create_engine_with_path`` keeps the dialect default pool, ``QueuePool``,
for the file database. This decision does not switch the pool and does not
add a second registered session.

D2 — Today's lookups stay
-------------------------

Existing lookups stay where they are, including ``_get_session``,
``get_runtime_session``, and the ``app_context.session`` reads listed
above. ``SessionMixin._get_session`` remains the lookup model classmethods
and commands use. This decision adds no session parameter. ``note_dialog``
keeps the optional session it already has.

D3 — A pytest allowlist freezes each function's lookup counts
-------------------------------------------------------------

``tests/test_runtime_session_freeze.py`` walks every Python file under
``oeapp/`` and counts, per file, per enclosing function, per kind:

- Calls whose function is ``get_runtime_session``, ``set_runtime_session``,
  ``clear_runtime_session``, ``_get_session``, ``get_session``, or
  ``SessionLocal``. A bare name and an attribute call both count.
- Loads of attribute ``session`` whose value is the name ``app_context``
  or an attribute named ``app_context`` (``app_context.session`` and
  ``self.app_context.session``). Stores do not count, so
  ``self.session = ...`` and ``_RUNTIME_STATE.session = ...`` are not
  lookups.

Imports, function definitions, and docstrings do not count. The two
``SessionLocal()`` calls inside ``oeapp/db.py`` are the grandfathered
creations, one in ``get_runtime_session`` and one in ``get_session``.
``get_session`` has no calls, so that kind is absent until one appears.
D7 removes the ``get_session`` creation from the allowlist in the change
that deletes the function.

The enclosing function is the dotted names of the surrounding classes and
functions, outermost first. Only the body is inside that function.
Decorators, base classes, default arguments, and annotations belong to
the scope that contains the definition. A property setter or deleter
appends ``.setter`` or ``.deleter``, so ``AppContext.session`` and
``AppContext.session.setter`` stay distinct. Code in no function uses
``<module>``.

The allowlist is a dict in that test. Each repo-relative path maps to the
functions that contain lookups, and each function maps to the counts of
the kinds it actually has. The test fails when the dict and the tree
disagree. A removal updates that function's count in the same change.
Removing its last lookup drops the function from the allowlist. The test
cannot see why a count changed. It goes green when the dict matches,
including a dict edited to permit a new lookup, to move one into another
function, or to raise a count. D5 is the later exception, and only for a
caller that must obtain the runtime session in order to pass it on. The
test cannot see that the classmethod lookup was removed in that same
change.

On 2026-10-28 every allowlisted function had one call of each kind it
listed. The test does not cap a count at 1. A second call of a kind in
one function passes once the dict records 2.

The scan does not enter ``tests/``. The scanner does not resolve
``import ... as``, ``getattr``, or a local other than ``app_context``
(``ctx = self.app_context`` then ``ctx.session``). A later use of those
spellings is invisible. The test stays green without an allowlist edit.

A call from UI code into a model classmethod is not a counted lookup.
The ``_get_session`` call stays inside the classmethod, at that
classmethod's existing count. Moving ``Annotation.get_by_idiom`` from
``SentenceCard`` onto ``SentenceCardController`` does not change the
allowlist. A session already stored on ``self.session`` is not a lookup
either.

D4 — Pass a session already in hand; do not pretend the models use it
---------------------------------------------------------------------

A new collaborator that must refresh or roll back receives the runtime
session from a holder that already read it. The new code does not add a
counted lookup. The read stays in the grandfathered function, at that
function's current count for that kind.

The F8 card asked new and changed services and commands to take an
injected session. This decision does not require a constructor session on
the next edit of a command or service. A session parameter added before
D5 does not change model classmethods. They still call ``_get_session``.
An edit that leaves every function's kind counts unchanged passes.

D5 — Model classmethods are a later migration
---------------------------------------------

Explicit session arguments on existing model classmethods are a separate
change, tracked as the F8 follow-up card. Callers will pass the runtime
session. ``SessionMixin._get_session`` stays for the call sites that
migration does not cover. Until that migration, D4 is how new code obtains
the session object for refresh and rollback. That migration may raise a
count only where a caller has to obtain the runtime session in order to
pass it, and it removes the classmethod lookups in the same change. This
freeze does not grant that raise. The allowlist test accepts the raise
once the dict matches, whether or not the classmethod lookup was removed.

D6 — This freeze lands before F1 and F7
---------------------------------------

The freeze was implemented before F1 and F7. The audit order listed F1 at
8, F7 at 9, and F8 at 10. This decision reverses that order so a counted
lookup in code those cards add fails the allowlist test until the dict
matches. The test does not reject the matching edit. After this freeze,
the order is F1, then F7. F1 has landed under that order and added no
lookup kind. F7 is still ahead. A lookup moved from one function to
another changes the allowlist, including a move into a new function in
``main_window.py`` and a move into a new file. The new collaborator
receives the session from the function that already read it, which keeps
the read.

D7 — Delete ``get_session`` when its sprint is planned
------------------------------------------------------

``get_session`` in ``oeapp/db.py`` has no callers and calls
``SessionLocal()``. Deleting it is part of this decision. The 2026-11-01
revision does not delete it. The deletion waits until the sprint that
includes this work has been planned. Until the function is gone, it
remains a second ``SessionLocal()`` that does not register its session.
The same change drops ``get_session`` from the ``oeapp/db.py`` allowlist
entry. The scanner keeps ``get_session`` as a kind name, so a later call
still counts.

Consequences
============

- The test fails when the allowlist and the tree disagree. It goes green
  when the dict is edited to match, including a new lookup, a moved
  lookup, or a higher count. It cannot see why the dict changed. Refresh
  and rollback in a new collaborator use the session object a
  grandfathered holder already read.
- Deleting a lookup fails the test until the allowlist drops that
  function's count. That update records a removal. A new lookup is a
  separate dict edit, which the test also accepts.
- Counts are per function and per kind. Swapping ``_get_session`` for
  ``get_runtime_session``, or hiding ``set_runtime_session`` behind a
  deleted ``_get_session``, changes the dict. On 2026-10-28 no enclosing
  function had two calls of one kind. The test does not cap a count at 1.
  ``Sentence.from_json`` calls ``_get_session`` once and uses that
  session to commit or flush. ``ProjectUI._on_annotation_applied`` loads
  ``app_context.session`` once and refreshes with that object. A second
  call of a kind in a function raises that function's count, and passes
  once the dict records the new count.
- Later uses of a session already stored on ``self.session`` are not
  lookups. ``import_export`` and ``wyrdcraeft_ingest`` can keep flushing
  the session they already fetched.
- An alias, ``getattr``, or ``ctx.session`` after ``ctx = self.app_context``
  is not counted. Adding one leaves the test green.
- A UI call to a model classmethod is not counted. The classmethod's
  existing ``_get_session`` stays the counted call.
- Tests stay outside the scan. A new test may call ``get_runtime_session``,
  ``set_runtime_session``, or ``SessionLocal``. The test half of finding
  F8 is not frozen. ``db_session`` remains how a test installs the runtime
  session.
- Stale identity-map behavior after commands, which the audit named as the
  likely symptom, is unchanged. The census stops unnoticed drift in the
  spellings it counts. Each command still uses the one runtime session,
  because model classmethods still look it up.
- F1 landed under the freeze and added no lookup kind. F7 proceeds under
  the freeze. A new ``app_context.session`` read in code it adds fails
  the test until the dict matches, including a read moved into another
  function or out of ``main_window.py``. Moving ``Annotation.get_by_idiom``
  onto ``SentenceCardController`` does not.
- No help text changes. The runtime session is not a term in ``CONTEXT.md``.
- ``get_session`` stays until the sprint in D7 is planned. This revision
  does not delete it.
- D5 is the later exception for a raised count, and only where a caller
  has to obtain the runtime session in order to pass it on and the same
  change removes the classmethod lookup. The test does not check that
  pairing.

Alternatives considered
=======================

- **One integer per file, summing every kind.** Rejected: deleting a
  ``_get_session`` call could hide a new ``set_runtime_session`` in the
  same file. Registration would not be frozen.
- **One count per file per kind.** This was the 2026-10-26 decision.
  Rejected on 2026-10-28: a file could drop one call of a kind and add
  another of that kind with no allowlist change. ``main_window.py`` held
  six ``app_context.session`` loads in six functions, so a new function
  could take a lookup by deleting one elsewhere.
- **Count every attribute named** ``session``. Rejected: services store
  the session they already looked up and then flush it. Those uses are
  not new lookups. ``_RUNTIME_STATE.session`` is the storage of the
  runtime session, not a UI read.
- **Give every edited command and service a session parameter now.**
  Rejected: model classmethods would keep calling ``_get_session``. The
  parameter would not be the session those methods use. That injection
  waits for D5.
- **Pass a session into every model classmethod now.** Rejected: that is
  the follow-up card.
- **Finish F1 and F7 before the freeze.** Rejected: lookups those cards
  added, including further ``app_context.session`` reads, would be
  grandfathered.
- **A Ruff banned-API rule.** Rejected: tidy-imports (``TID``) is disabled
  in ``pyproject.toml``. The UI read is an attribute load, which a
  banned-API list does not see.
- **A line-numbered baseline.** Rejected: the napoleon gate's line-keyed
  baseline drifts. The freeze keys on the file, the enclosing function,
  the kind, and the count.
- **Scan tests as well.** Rejected: tests install the runtime session on
  purpose, and ``test_commands`` already looks it up to roll back. The
  gap is accepted and named above. Product code is the freeze.
- **A second registered session.** Rejected: the finding keeps one
  runtime session for the desktop process.
- **Switch the engine to** ``NullPool`` **so the text can say there is no
  pool.** Rejected on 2026-11-01: ``QueuePool`` is the dialect default for
  this file database. Changing it would change connection behavior and
  would not separate the UI from the runtime session.
- **Treat an allowlist edit as something the test rejects.** The
  2026-10-28 text said review rejects that edit. Revised on 2026-11-01:
  the test accepts a dict that matches the tree. The revision states that
  limit in D3.
- **Cap every count at 1 in the test.** Rejected for this revision. The
  2026-10-28 tree has those counts. Making the cap a rule is a further
  decision.
- **Delete** ``get_session`` **in the 2026-11-01 revision.** Rejected for
  this date. D7 records the deletion and waits until the sprint that
  includes it has been planned.

Related
=======

- Trello card 97, finding F8: https://trello.com/c/RqmuEu67
- F8 follow-up, explicit session arguments on model classmethods:
  https://trello.com/c/dNaoAIwU
- F1 landed under this freeze. The audit had listed it earlier, at
  resolve order 8: https://trello.com/c/TavvhWiE
- F7 follows this freeze. The audit had listed it earlier, at resolve
  order 9, and it already forbids new UI ``_get_session`` call sites:
  https://trello.com/c/rdFyWWxq
- D7, delete ``get_session``, waits until the sprint that includes that
  deletion has been planned.

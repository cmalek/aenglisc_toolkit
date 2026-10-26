.. _adr_0011_runtime_session_freeze:

==============================================================
ADR 0011: Freeze runtime-session lookups at today's call sites
==============================================================

:Status: Accepted
:Date: 2026-10-26

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
``get_session``.

Model classmethods, ``save`` and ``delete``, commands, and
``Annotation._get_session`` reach the runtime session through
``SessionMixin._get_session``. ``oeapp/commands/note.py``,
``oeapp/ui/sentence_card_controller.py``, and ``oeapp/ui/oe_text_edit.py``
call ``get_runtime_session`` directly. ``oeapp/ui/project_workspace.py``,
``oeapp/ui/notes_panel.py``, ``oeapp/ui/main_window.py``, and
``oeapp/ui/dialogs/note_dialog.py`` read ``app_context.session``, the
``AppContext`` property that calls ``get_runtime_session``. Services that
already looked the session up keep it on ``self.session`` and flush, add,
and commit through that attribute. ``note_dialog`` already takes an
optional session and falls back to ``app_context.session``. The calls are
bare names or attributes. Nothing aliases the functions.

Tests install and clear the session in ``tests/conftest.py`` (the
``db_session`` fixture) and in ``tests/test_state.py``.
``tests/test_commands.py`` calls ``get_runtime_session`` to roll back.
``tests/test_db.py`` calls ``SessionLocal()`` directly.

Fat ORM stays. SQLAlchemy stays. A second writer, and a connection pool,
are outside the finding. Passing an explicit session through every model
classmethod is a larger migration. F1 (resolve order 8) and F7 (resolve
order 9) are unfinished. F8's audit note said collaborators from those
cards should take an injected session. Those collaborators do not exist
yet. F7 already forbids new ``_get_session`` call sites in the UI.

Decision
========

D1 — One runtime session
------------------------

The desktop process keeps a single SQLAlchemy session, the runtime
session, on ``_RUNTIME_STATE``. ``set_runtime_session`` installs a session
it is given. ``get_runtime_session`` returns that session, and is the only
product path that may create one when none is registered.
``clear_runtime_session`` clears it. ``get_session`` stays without
callers. There is no connection pool.

D2 — Today's lookups stay
-------------------------

Existing lookups stay where they are, including ``_get_session``,
``get_runtime_session``, and the ``app_context.session`` reads listed
above. ``SessionMixin._get_session`` remains the lookup model classmethods
and commands use. This decision adds no session parameter. ``note_dialog``
keeps the optional session it already has.

D3 — A pytest allowlist freezes each kind of lookup
---------------------------------------------------

Add ``tests/test_runtime_session_freeze.py``. It walks every Python file
under ``oeapp/`` and counts, per file, per kind:

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
creations. ``get_session`` has no calls, so it is absent until one appears.

The allowlist is a dict in that test. Each repo-relative path maps to the
counts of the kinds that file actually has. The test fails when the dict
and the tree disagree. A removal updates that kind's count in the same
change. The test cannot see why a count changed. It goes green when the
dict matches, including a dict someone raised to permit a new lookup.
Review rejects that raise. D5 is the later exception, and only for a
caller that must obtain the runtime session in order to pass it on.

The scan does not enter ``tests/``. These spellings are not resolved, and
none of them appear under ``oeapp/`` today: ``import ... as``,
``getattr``, and a local other than ``app_context``
(``ctx = self.app_context`` then ``ctx.session``).

D4 — Pass a session already in hand; do not pretend the models use it
---------------------------------------------------------------------

A new collaborator that must refresh or roll back receives the runtime
session from a holder that already read it. The new code does not add a
counted lookup. The read stays in the grandfathered file, at that file's
current count for that kind.

A session parameter added before D5 does not change model classmethods.
They still call ``_get_session``. This decision does not require a
constructor session on the next edit of a command or service. An edit that
leaves every kind's count unchanged passes.

D5 — Model classmethods are a later migration
---------------------------------------------

Explicit session arguments on existing model classmethods are a separate
change, tracked as the F8 follow-up card. Callers will pass the runtime
session. ``SessionMixin._get_session`` stays for the call sites that
migration does not cover. Until that migration, D4 is how new code obtains
the session object for refresh and rollback. That migration may raise a
count only where a caller has to obtain the runtime session in order to
pass it, and it removes the classmethod lookups in the same change. This
freeze does not grant that raise.

D6 — This freeze lands before F1 and F7
---------------------------------------

The freeze is implemented before F1 and F7. The audit order listed F1 at
8, F7 at 9, and F8 at 10. This decision reverses that order so a counted
lookup in code those cards add fails review under D3. After this freeze,
the order is F1, then F7. A lookup moved out of ``main_window.py`` into a
new file is a new count in that file. The new collaborator receives the
session from ``main_window.py``, which keeps the read.

Consequences
============

- The test fails when the allowlist and the tree disagree. Review fails
  a diff that raises a count. The test alone does not, once the dict is
  edited to match. Refresh and rollback in a new collaborator use the
  session object a grandfathered holder already read.
- Deleting a lookup fails the test until the allowlist drops that kind's
  count. That update records a removal. It does not authorize a new
  lookup of any kind, in that file or another.
- Counts are per kind. A file cannot trade ``_get_session`` for
  ``get_runtime_session``, or hide ``set_runtime_session`` behind a
  deleted ``_get_session``. The same kind may still lose one call and
  gain another inside one file without a failure.
- Later uses of a session already stored on ``self.session`` are not
  lookups. ``import_export`` and ``wyrdcraeft_ingest`` can keep flushing
  the session they already fetched.
- An alias, ``getattr``, or ``ctx.session`` after ``ctx = self.app_context``
  is not counted.
- Tests stay outside the scan. A new test may call ``get_runtime_session``,
  ``set_runtime_session``, or ``SessionLocal``. The test half of finding
  F8 is not frozen. ``db_session`` remains how a test installs the runtime
  session.
- Stale identity-map behavior after commands, which the audit named as the
  likely symptom, is unchanged. New lookups stop. Each command still uses
  the one runtime session, because model classmethods still look it up.
- F1 and F7 proceed under the freeze. A new ``app_context.session`` read
  in code they add fails D3, including a read moved out of
  ``main_window.py``.
- No help text changes. The runtime session is not a term in ``CONTEXT.md``.
- ``tests/test_runtime_session_freeze.py`` enforces D3. It fails when the
  allowlist and the tree disagree. A diff that raises a count and edits
  the allowlist to match stays green. Review rejects that raise. D5 is
  the only later exception, and only where a caller has to obtain the
  runtime session in order to pass it on.

Alternatives considered
=======================

- **One integer per file, summing every kind.** Rejected: deleting a
  ``_get_session`` call could hide a new ``set_runtime_session`` in the
  same file. Registration would not be frozen.
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
  baseline drifts. The freeze keys on the file, the kind, and the count.
- **Scan tests as well.** Rejected: tests install the runtime session on
  purpose, and ``test_commands`` already looks it up to roll back. The
  gap is accepted and named above. Product code is the freeze.
- **A second session, or a connection pool.** Rejected: the finding keeps
  one runtime session for the desktop process.

Related
=======

- Trello card 97, finding F8: https://trello.com/c/RqmuEu67
- F8 follow-up, explicit session arguments on model classmethods:
  https://trello.com/c/dNaoAIwU
- F1 follows this freeze. The audit had listed it earlier, at resolve
  order 8: https://trello.com/c/TavvhWiE
- F7 follows this freeze. The audit had listed it earlier, at resolve
  order 9, and it already forbids new UI ``_get_session`` call sites:
  https://trello.com/c/rdFyWWxq

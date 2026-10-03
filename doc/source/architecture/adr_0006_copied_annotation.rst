.. _adr_0006_copied_annotation:

==============================================================
ADR 0006: Copied Annotation is a validated ``AnnotationJson``
==============================================================

:Status: Accepted
:Date: 2026-10-02

Context
=======

Audit finding F12 (resolve order 6 of 12 in the 2026-09-13 architecture and
capability audit): the Copied Annotation is an untyped ``dict[str, Any]``.

- ``AppContext._copied_annotation`` (``oeapp/state.py``) stores whatever dict
  ``Annotation.to_json()`` returned at copy time, and
  ``copied_annotation_changed`` emits it as-is.
- ``AnnotationJson`` (``oeapp/services/import_export_schema.py``,
  ``extra="forbid"``) already describes the same payload for project
  import/export, but the copy/paste path bypasses it. Tests inject raw dicts
  such as ``{"pos": "N"}`` and assert on dict keys.
- ``AnnotateTokenCommand`` applies the pasted payload through
  ``Annotation.from_json``, which also applies ``updated_at`` from the payload.
  A paste therefore stamps the *source* annotation's ``updated_at`` onto the
  target token.
- ``AnnotationJson`` lives in ``oeapp.services.import_export_schema``, where
  ``TokenJson`` and ``IdiomJson`` embed it, although ``AGENTS.md`` puts data
  models in ``oeapp.models``. ``state.py`` imports only ``commands`` and
  ``db`` today.
- The payload can only be produced in-process by ``to_json()``, so a payload
  that fails the schema indicates a bug, not bad user input. The schema only
  catches unknown keys and wrong value types (its fields are ``str | None``,
  ``int`` and ``bool``); it does not check that a value is a legal code.
- ``RememberedAnnotation.annotation_payload`` is a similar untyped dict. It is
  out of scope for this decision.
- The application log is the artifact users send when they hit trouble.

Decision
========

D1 — Hold a validated ``AnnotationJson`` in state
-------------------------------------------------

``AppContext.copied_annotation`` is typed ``AnnotationJson | None``. The full
model is kept, timestamps included, so the schema is reused unchanged.

D2 — Validate once, at the setter boundary
------------------------------------------

``copy_annotation`` builds the value with
``AnnotationJson.model_validate(annotation.to_json())``. Because the setter
only accepts ``AnnotationJson``, paste reads an already-checked payload and does
not validate again. On ``ValidationError`` the copy is refused: the status bar
shows "Cannot copy annotation: invalid data" and the previous Copied Annotation
is left untouched.

D3 — Log the payload on refusal
-------------------------------

A refused copy logs at ``error`` level through ``get_logger`` with the token and
annotation ids, the full ``to_json()`` payload and
``ValidationError.errors()``. The payload holds the translator's field values,
including free text (``sense``, ``modern_english_meaning``, ``root``) that may
come from an unpublished project. That is accepted: the log is the user's own
file and they choose to send it, and having the payload in it lets them hand
over a reproduction. Entries are not rate limited, so repeated copies of the
same bad annotation log repeatedly.

D4 — Paste strips timestamps
----------------------------

Paste builds the command's ``after`` state from
``model_dump(exclude={"created_at", "updated_at"})``. Timestamps describe the
source annotation, so the target keeps a fresh ``updated_at``.

D5 — The signal emits a plain dict
----------------------------------

``copied_annotation_changed`` emits ``model_dump(mode="json")``, so listeners
stay independent of the pydantic class. No production code listens to it today.

D6 — ``AnnotationJson`` moves to ``oeapp.models``
-------------------------------------------------

Only ``AnnotationJson`` moves, out of ``oeapp.services.import_export_schema``
into ``oeapp.models``; ``import_export_schema`` imports it from there for
``TokenJson`` and ``IdiomJson``. The rest of that schema stays in services
deliberately, so it remains split from the ``AGENTS.md`` rule until a separate
refactor moves it. This edits a module the F12 card lists as out of scope
("do not change project import/export schema except to reuse it"); the edit is
limited to relocating one class, and this ADR overrides that line. It lands in
its own commit ahead of the clipboard change.

Consequences
============

- Key or type drift between ``to_json()`` and the schema now surfaces as a
  refused copy with a logged payload instead of a silently malformed paste.
  Value drift (an illegal code) is not detected.
- Pasting no longer overwrites the target's ``updated_at`` with the source's.
- ``copy_annotation`` gains a failure path that needs a status message and a
  test; existing tests that set raw dicts must construct ``AnnotationJson``.
- Paste no longer double-checks. The setter's type is not enforced at runtime
  and the stored model is mutable, so a caller that passes a wrong type or
  mutates the stored model is not caught.
- ``CONTEXT.md`` records the term **Copied Annotation**; "clipboard annotation"
  is avoided because it conflates with the system clipboard, which the
  copy/paste shortcuts still use when no token is selected.

Alternatives considered
=======================

- **Coerce and drop unknown keys.** Rejected: it would silently apply partial
  data and hide drift, unlike project import (``extra="forbid"``).
- **Strip timestamps at copy time.** Rejected: the stored value would no longer
  be a faithful ``AnnotationJson``.
- **Validate again at paste.** Rejected: dead code, since only validated values
  can be stored.
- **Emit the model from the signal.** Rejected: it would leak the pydantic type
  into the signal contract.
- **Leave ``AnnotationJson`` in ``oeapp.services``.** Rejected: it breaks the
  ``AGENTS.md`` models-in-``oeapp.models`` rule and adds a ``state`` to
  ``services`` dependency.

Related
=======

- Audit finding F12 (Trello card 6); depends only weakly on
  :ref:`adr_0005_pos_field_catalog` (F2).

.. _adr_0001_usability_overhaul:

==============================================================
ADR 0001: Usability overhaul for non-programmer distribution
==============================================================

:Status: Proposed (D2 implemented and verified; D3/D3a/D4/D5 not yet implemented)
:Date: 2026-08-31

Context
=======

The app is used daily by its sole maintainer, and needs to become installable
and usable by non-programmers:

1. ``make dev`` rebuilt QtHelp ``.qch``/``.qhc`` unconditionally on every
   launch (``Makefile`` ``help-assets``/``dev`` had no file prerequisites —
   always-run rules).
2. The PyInstaller installer is reported at ~20GB. Root cause was
   **assumed** to be the vendored TeXLive bundle; that assumption turned out
   to be mostly wrong (see D3).
3. Overall UI design needs a pass.

Verification standard for this ADR
-----------------------------------

Claims here are marked with their evidence level, because an earlier
revision of this document recorded unverified subagent findings as fact:

- **Measured** — observed directly in this repo by running something.
- **Read** — confirmed by reading the cited source line.
- **Assumed** — plausible but untested; must not be acted on without
  measuring first.

Decision
========

D1 — Long-lived integration branch
-----------------------------------

Branch ``usability-overhaul`` off ``master``. Each slice lands as its own
commit into this branch; ``master`` is merged back to only when a slice is
proven.

Sole developer, and all of this work happens on the branch — so
branch/``master`` divergence and merge-conflict debt are explicitly **not**
a concern, and no sync cadence is needed.

One real coupling does remain: **``.venv`` is shared across branches** (one
venv per repo, not per branch). Any dependency change made on this branch
breaks the daily driver on ``master`` too, until re-synced. Dependency
experiments must therefore be restored before ending a session. (This bit
us once already — see D3a.)

D2 — Help asset rebuild becomes a real Make file target — IMPLEMENTED
------------------------------------------------------------------------

``oeapp/help/assets/aenglisc_toolkit_help.qch`` is now a real Make target
with prerequisites on ``oeapp/help/topics/*.md``, ``scripts/build_help.py``,
and ``oeapp/help/topics.py``. ``help-assets`` and ``dev`` depend on that
file instead of running the build script unconditionally. Make's mtime
comparison skips the rebuild when nothing changed — no new tooling.

**Measured:** ``make help-assets`` with unchanged sources reports "Nothing
to be done"; touching a topic file triggers a real rebuild.

**Scope correction — this fixed the dev loop, not a user-facing problem.**
``help-assets`` hangs off ``make dev``/``make build``. End users install
the ``.app`` and never run ``make``, so they never experienced a help
*recompile*. What users *do* pay on every single launch is
``ensure_runtime_help_assets()`` (``oeapp/help/help_paths.py:51``), which
SHA-256-hashes both help artifacts on each startup to decide whether to
re-copy them into app data (**Read**). If the original complaint was about
per-launch cost visible to users, that hashing — not the Make rule — is the
thing to address. Left open deliberately; needs a measurement of actual
startup cost before optimizing.

**Known defects in the current D2 implementation (accepted for now, both
cheap to hit):**

- The rule tracks only ``.qch``, but ``build_help.py`` also emits ``.qhc``,
  ``.qhp``, ``.qhcp`` and HTML. Delete ``.qhc`` alone and Make sees a fresh
  ``.qch``, refuses to rebuild, and the app then raises ``HelpEngineError``
  telling the user to rebuild — which ``make`` declines to do. Fix: make
  the rule's target list cover ``.qhc`` too.
- ``$(wildcard oeapp/help/topics/*.md)`` cannot detect a **deleted** topic:
  the wildcard shrinks, ``.qch`` stays newer than everything remaining, no
  rebuild fires, and stale help ships a topic that no longer exists.
- Only ``make help-assets`` was exercised; ``make dev`` end-to-end was not.

D3 — Installer size: root cause was misdiagnosed
--------------------------------------------------

**The original claim in this ADR — that the 2.9GB TeXLive bundle was "the
main driver of the ~20GB installer" — does not survive arithmetic.** The
entire ``assets/tectonic`` tree is 3.0GB (**Measured**). Removing it leaves
roughly 17GB unexplained. No one has ever measured a built ``.app``;
``dist/`` is currently absent, so even the "20GB" figure is recollection,
not measurement.

What was actually found by measuring (**Measured**): ``.venv`` is 2.9GB,
and ``aenglisc_toolkit.spec:28`` sets ``excludes=[]`` — nothing is pruned
from the PyInstaller dependency closure. Site-packages contained PySide6
1.2G, torch 368M, pypandoc 128M, cv2 120M, llvmlite 113M, scipy 72M,
onnxruntime 68M, onnx 63M, pandas 48M, transformers 46M, sympy 41M — an
entire ML/CV/OCR stack in a text-annotation app. See D3a for where it comes
from.

**Decision: D3 is blocked on a real size audit of a built ``.app`` before
any spec edit.** Shipping the tectonic change first would book a 3GB win
against a 20GB problem and burn the slice.

Once that audit exists, the tectonic changes below still stand on their own
merits (they are correct, just not the headline):

- Stop bundling ``assets/tectonic/bundle`` in ``aenglisc_toolkit.spec``.
- Bundle only the Tectonic binary for the platform/arch being built, not
  all three (``assets/tectonic/binaries/<platform>/<arch>/``).
- Add real ``excludes=[...]`` to the spec for whatever the audit shows is
  unused.

**Read:** ``oeapp/services/pdf_engine.py:132-143`` — when
``assets/tectonic/bundle/default`` does not exist, ``bundle_path`` becomes
``None`` and ``compile_latex_with_tectonic`` omits
``--bundle``/``--only-cached``, falling back to Tectonic's normal
fetch-and-cache behavior. The ``PDFEngineError`` raise at ``:137`` only
triggers when the bundle directory *exists but lacks* ``SHA256SUM``, so
deleting it outright is safe. This has **not** been verified against an
actual frozen build — it must be, since the frozen path is the one that
raises.

Tradeoff (user-confirmed): require internet on first PDF export rather than
shipping the bundle. **Unrecorded risk now recorded:** this makes new
installs depend on ``relay.fullyjustified.net`` (the bundle URL in
``Makefile:7``) remaining available; if that relay disappears, PDF export
never works for a fresh install. An offline-capable alternative — shipping
a trimmed bundle of only the packages actually used — was considered and
rejected as more work for a smaller win, but is the fallback if the relay
proves unreliable.

D3a — Dependency bloat traced to ``wyrdcraeft`` → ``unstructured[all-docs]``
--------------------------------------------------------------------------------

**Measured/Read.** None of torch/transformers/onnx/cv2/scipy/pandas/llvmlite
are direct dependencies. All arrive transitively: ``wyrdcraeft`` (the
maintainer's own package, ``cmalek/oe_json_extractor``) declares
``Requires-Dist: unstructured[all-docs]>=0.15``. That single extra pulls
torch, torchvision, timm, openai-whisper, transformers, onnx, onnxruntime,
opencv, scipy, sympy, pypandoc, llvmlite (via numba) and pandas (via
langextract).

This app's import dialog only accepts ``.txt .xml .tei .md``
(``oeapp/ui/dialogs/mixins.py:128``, **Read**). The entire OCR/inference/audio
stack is dead weight. Per the maintainer, the code branch that motivated
those packages never panned out.

**Attempted and reverted (Measured):** adding
``override-dependencies = ["unstructured>=0.15"]`` to ``[tool.uv]`` shrinks
``.venv`` from 2.9GB to 1.6GB and removes torch, torchvision, timm, whisper,
transformers, onnx, onnxruntime, cv2, scipy, sympy and pypandoc. But it
**breaks imports**: ``wyrdcraeft/ingest/loaders.py:15`` imports
``partition_pdf`` unconditionally, and
``unstructured/partition/pdf_image/pdfminer_processing.py:11`` imports
``unstructured_inference`` at module level, which requires torch. Installing
only the light pdf deps (``pi-heif``, ``pdf2image``, ``pdfminer-six``,
``pypdf``, ``pikepdf``, ``unstructured-pytesseract``) is **not** sufficient,
and ``unstructured[pdf]`` is no help because that extra includes
``unstructured-inference`` itself. The override was reverted; the finding is
documented in ``pyproject.toml`` at ``[tool.uv]``.

**Decision: fix upstream in** ``wyrdcraeft`` — make the PDF loader import
lazy, or drop it — then re-apply the override here. Expected saving ~1.3GB
of ``.venv``, and considerably more in the expanded PyInstaller output.
Owned by the maintainer, tracked separately from this branch.

**Note (Measured):** ``uv sync`` without an explicit ``--python 3.13``
recreates the venv on Python 3.14 and then fails (``spacy`` has no cp314
wheel). Always use ``uv sync --python 3.13`` in this repo.

D4 — App design pass
----------------------

Deferred from full implementation until D2/D3 land, but scope is now pinned
down by a UI survey + affordance review (Norman: signifiers, feedback,
mapping, constraints, discoverability — not decoration). Findings,
evidence-based, ``oeapp/ui/`` (~17,500 lines across 40 files):

**Bugs masquerading as design issues (cheap, fix first) — both Read and
confirmed first-hand:**

- ``Messages.show_error`` (``oeapp/ui/main_window.py:1437``) calls
  ``QMessageBox.warning()`` instead of ``.critical()`` — errors and
  warnings render with the same icon, user can't tell severity apart.
- ``main_window.py:411`` — CSS typo ``pallete(text-muted)`` (missing "t")
  silently no-ops the empty-state label's color rule. Fails quiet, nobody
  notices.

**Missing signifiers:**

- Chapter/section nav buttons (``main_window.py:279-308``, glyph-only
  ``<``/``>``) have no tooltip or accessible name. Only 2 ``setToolTip()``
  calls exist in the entire ``oeapp/ui/`` tree, despite many icon-only
  controls.

**Constraints with no user-facing justification:**

- Sidebar is fixed at ``SIDEBAR_WIDTH = 350`` (``main_window.py:76``, laid
  out at ``452-469``) with no ``QSplitter`` anywhere in the main window.
  User has no way to trade space between the sentence view and the
  annotation sidebar.

**Broken/misleading mapping:**

- ``build_toolbar``/``build_navigation_toolbar``
  (``main_window.py:186-239``, ``259-314``) are plain
  ``QWidget``+``QHBoxLayout``, not ``QToolBar`` — no native overflow when
  the window narrows, no right-click customize, doesn't register as a
  toolbar to accessibility tooling or match user expectations from other
  apps.

**Styling incoherence (root cause of "needs a design pass" feeling):**

- Three uncoordinated styling mechanisms stacked: app-wide ``qt_themes``
  (nord/modern_light, ``application.py:29-33``), ~60 scattered inline
  ``setStyleSheet()`` calls using ``palette(...)`` CSS strings across
  ``main_window.py``, ``token_details_sidebar.py``, ``sentence_card.py``,
  ``notes_panel.py``, ``search_controller.py``, ``project_workspace.py``,
  ``full_translation_window.py``, ``widgets.py``, and a
  ``themes/default.qss`` (9 lines) that is loaded nowhere — dead file. See
  also D5 (theme-switch bug) below, which stems from the same root cause.

**Inconsistent modality:**

- Most dialogs block via ``.exec()``; ``HelpCenterDialog`` is deliberately
  non-modal (``main_window.py:610-630``), a good call. But
  ``LogViewerDialog`` and ``BackupsView`` also block, even though both are
  reference-while-you-work tools — forces the user to close them to keep
  annotating.

**Lower priority, note for later:** ``dialogs/annotation_modal.py`` (930
lines, 28 layout constructions) — deep nesting will slow any future
redesign of the annotation flow.

All findings above other than the two confirmed bugs are **Read**-level at
best — they come from a survey pass, not from running the app. Anything in
the list is a candidate, not a commitment.

**Decision (this is what D4 actually commits to), in priority order:**

1. **Ship now, independently:** the two confirmed one-line bugs
   (``QMessageBox.critical``, ``pallete`` typo). No dependencies, no risk.
2. **Ship next:** tooltips + accessible names on icon-only controls
   (``main_window.py:279-308``); ``QSplitter`` between sentence column and
   sidebar. Check ``SIDEBAR_WIDTH`` blast radius first — not yet done.
3. **Ship after that:** delete the dead ``themes/default.qss``, and make
   ``LogViewerDialog``/``BackupsView`` non-modal following the
   ``HelpCenterDialog`` pattern (``main_window.py:610-630``).
4. **Explicitly deferred, needs a safety net first:** migrating the ~60
   inline ``setStyleSheet()`` calls onto ``qt_themes`` as single source of
   truth. This touches 8 files across an app the maintainer depends on
   daily, and **there is currently no visual regression test of any kind**
   to catch what it breaks. Doing it bare contradicts D1's whole purpose.
   Prerequisite: some form of before/after screenshot comparison, even a
   manual checklist of the main screens. Do not start this one on a whim.
5. **Not scheduled:** ``dialogs/annotation_modal.py`` (930 lines, 28 layout
   constructions) — deep nesting will slow any future redesign of the
   annotation flow. Noted, not acted on.

**Acceptance criteria:** items 1–3 are done when the app launches, the
affected screens render correctly in both ``nord`` and ``modern_light``,
and ``pytest`` is no worse than the pre-change baseline (currently 315
passed, 1 pre-existing failure in ``tests/test_export_pdf.py`` caused by
the deleted ``texts/The_Seafarer.json`` fixture, unrelated to this work).

**Rollback:** each item is a self-contained commit on this branch; revert
the commit.

D5 — Live theme switching (no restart required)
---------------------------------------------------

**Root cause confirmed, not a Qt/qt_themes limitation.**
``qt_themes.set_theme(theme, style='fusion')``
(``.venv/lib/python3.13/site-packages/qt_themes/_theme.py:182-204``) just
calls ``QApplication.setPalette(palette)`` +
``QApplication.setStyle(style)`` — fully callable at runtime, Qt
auto-repolishes existing widgets via ``QEvent.PaletteChange``. It is only
ever invoked once, at boot (``oeapp/ui/application.py:29-33``).
``_on_theme_changed`` (``oeapp/ui/dialogs/settings.py:176-197``) never
calls it again — it just pops a ``QMessageBox`` telling the user to quit
and restart. The restart requirement is a manufactured limitation (someone
punted), not an unavoidable constraint. ``qt_themes`` has no
``themeChanged`` signal, so the caller drives re-apply itself.

The ~60 inline ``setStyleSheet()`` calls using ``palette(role)`` CSS
functions read the widget's live ``QPalette`` on each Qt stylesheet
evaluation, not a construction-time snapshot — they ride along for free
once ``set_theme()`` is called again. ``ThemeMixin.theme_base_color``/
``is_dark_theme`` (``oeapp/ui/mixins.py:39-50``) also read
``QApplication.instance().palette()`` fresh per call — fine, unless some
widget caches their *result* once at ``__init__`` (needs a smoke-test
sweep, not a rewrite).

**Fix scope (small):**

- ``settings.py::_on_theme_changed`` — call
  ``qt_themes.set_theme(new_theme_key)`` directly; drop or repurpose the
  "restart required" dialog.
- ``HelpCenterDialog._theme_override_css`` (``help_center_dialog.py:298``)
  is applied explicitly at construction (``:171``), not reactive — needs
  an explicit re-apply if the help center is open during a live switch.
- Smoke-test for any widget caching a
  ``theme_base_color``/``is_dark_theme`` result once instead of reading it
  live.

**Confidence: this is a hypothesis, not a verified outcome.** The claim
that palette-driven CSS "rides along for free" comes from reading source,
not from running a live switch. Two specific risks are unaddressed:

- ``set_theme()`` also calls ``QApplication.setStyle('fusion')`` at
  runtime. Restyling a live Qt app is historically janky for some widget
  classes, and ``HelpCenterDialog``'s ``QTextBrowser`` content is exactly
  the kind that does not repolish cleanly.
- Any widget that caches a ``ThemeMixin.theme_base_color``/
  ``is_dark_theme`` **result** once at ``__init__`` (rather than reading
  the property live) will go stale. ``ThemeMixin`` has 2 known call sites
  (``full_translation_window.py``, ``search_controller.py``) and no test
  coverage.

**Acceptance criteria:** switching theme in Settings visibly restyles the
main window, an open annotation modal, and an open Help Center, in both
directions, with no restart and no visibly stale panel.

No mixin rewrite or 60-site edit needed *if the hypothesis holds*.
Independent of D4 item 4 — can land before it, and should, since it is
small and high-value to the maintainer daily.

Alternatives considered
========================

- **D2:** commit the built ``.qch``/``.qhc`` to git and never build them in
  the dev loop at all. Rejected: generated binary artifacts in git, and the
  build step is cheap once it's correctly conditional. Reconsider if the
  Make rule's known defects prove annoying.
- **D3:** ship the TeXLive bundle as a separate optional download (a "PDF
  export support pack") rather than all-or-nothing. Rejected as more
  moving parts than fetch-on-first-use, but it is the natural answer if the
  upstream relay proves unreliable.
- **D3a:** vendor a patched ``wyrdcraeft``, or add the light pdf deps
  locally. Both rejected — measured as insufficient
  (``unstructured_inference`` is a module-level import). Upstream fix is
  the only clean path.
- **D5:** keep the restart requirement and simply make the dialog honest
  about it. Rejected — the live path is a few lines and the restart is a
  manufactured limitation.

Consequences
============

- Daily dev workflow (``make dev``) no longer pays a help-rebuild tax on
  every launch (D2, done).
- Installer size is **not yet improved**, and will not be until the D3
  build audit happens. The expected wins, in likely order of size: D3a's
  ~1.3GB of ML dependencies (blocked on an upstream ``wyrdcraeft`` fix),
  spec ``excludes`` for whatever the audit finds, then ~3GB from the
  tectonic bundle and redundant platform binaries.
- Once D3 lands, first PDF export after install will require network
  access once, and new installs become dependent on
  ``relay.fullyjustified.net`` remaining available.
- ``master`` remains stable for the maintainer's daily use, **except** via
  the shared ``.venv`` — dependency experiments on this branch affect
  ``master`` too and must be restored before ending a session.
- This ADR now covers five decisions with different lifecycles. If it
  grows further, split it: one file per decision, so superseding one
  doesn't mean editing a document that records the others.

# PySide6 Maintainability Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the maintainability, readability, testability, and PySide6 idiom fit of the desktop application without rewriting the app or changing behavior.

**Architecture:** Preserve fat ORM models as the preferred home for model-specific queries and composable database operations. Extract UI workflow, presentation state, and Qt model/view structure away from large widgets while keeping database interaction discoverable on ORM model classes. Evolve global app state toward a narrow Qt-style app context built around explicit ownership, signals/slots, and typed accessors instead of a generic shared dict.

**Tech Stack:** Python 3.13, PySide6/Qt, SQLAlchemy ORM, SQLite, pytest/pytest-qt, ruff, mypy, Napoleon doc gate.

---

## Guiding Constraints

- Preserve existing behavior and public APIs unless a phase explicitly says otherwise.
- Keep database queries on ORM models whenever the query belongs to one model or model aggregate.
- Use services for cross-model workflows, exports/imports, external tools, and UI-independent orchestration.
- Use controllers/presenters for UI workflow only; they should call ORM model methods rather than owning SQL queries.
- Prefer small, composable ORM methods over moving data access into generic repository classes.
- Prefer Qt-native model/view where it reduces duplicated widget item code.
- Prefer Qt-style shared state patterns: a small app-lifetime context for stable services/state, and local controller/workspace ownership for transient view state.
- Make incremental commits after each task or small group of related tasks.
- Run the quality gate after each implementation phase:
  - `.venv/bin/ruff check <touched python files>`
  - `.venv/bin/mypy <touched python files>`
  - `make napoleon-gate`
  - targeted pytest commands listed in each task

## Current Hotspots

- `oeapp/ui/main_window.py`: main shell, search, export/import actions, project loading, reload behavior, messages.
- `oeapp/ui/sentence_card.py`: layout construction, selection coordination, annotation workflow, sentence commands, edit mode.
- `oeapp/ui/oe_text_edit.py`: token/range/idiom selection, rendering, keyboard behavior, context menu action routing.
- `oeapp/ui/token_table.py`: `QTableWidget` item population, duplicated annotation column mapping.
- `oeapp/ui/full_translation_window.py`: full project text rendering and interaction.
- `oeapp/services/export_pdf.py`: duplicated text-flow/title/separator rules also used by full translation UI.
- `oeapp/state.py`: global singleton owns session, settings, command manager, main window, and transient selection state that would fit better in a narrower app context plus local controllers.
- `oeapp/models/project.py`, `oeapp/models/sentence.py`, `oeapp/models/token.py`: intentionally fat ORM models; keep query ownership here but split long methods into smaller composable model methods when useful.

## Target File Structure

Create or modify these files over phases:

- Modify: `oeapp/ui/token_table.py`
  - Responsibility: table widget shell, selection signals, keyboard shortcuts.
- Create: `oeapp/ui/token_table_model.py`
  - Responsibility: optional later `QAbstractTableModel` for token annotation rows.
- Modify: `tests/test_token_table.py`
  - Responsibility: token table behavior and column consistency.
- Create: `oeapp/ui/project_workspace.py`
  - Responsibility: main-window project/chapter/section UI workflow; no raw queries except calls to ORM model methods.
- Modify: `oeapp/ui/main_window.py`
  - Responsibility: main shell only; delegate search/project/reload workflows.
- Create: `oeapp/ui/search_controller.py`
  - Responsibility: search UI state, navigation, focus restore; calls ORM model search helpers.
- Modify: `oeapp/models/project.py`
  - Responsibility: add composable fat-ORM search helpers such as `search_matches`.
- Create: `oeapp/models/search_result.py`
  - Responsibility: dataclass/value objects shared by model search and UI navigation.
- Create: `oeapp/ui/sentence_card_controller.py`
  - Responsibility: sentence-card user actions that execute commands and coordinate dialogs.
- Modify: `oeapp/ui/sentence_card.py`
  - Responsibility: widget construction and signals; delegate command workflows.
- Create: `oeapp/ui/annotation_form_state.py`
  - Responsibility: dataclass for annotation form read/write state.
- Modify: `oeapp/ui/dialogs/annotation_modal.py`
  - Responsibility: dialog display and signal handling; delegate form state extraction.
- Create: `oeapp/models/text_flow.py`
  - Responsibility: fat-domain text-flow helpers for visible titles, paragraph starts, sentence separators.
- Modify: `oeapp/ui/full_translation_window.py`
  - Responsibility: render UI using shared text-flow helpers.
- Modify: `oeapp/services/export_pdf.py`
  - Responsibility: render PDF using shared text-flow helpers.
- Modify: `oeapp/state.py`
  - Responsibility: shrink global mutable UI state gradually; keep compatibility while moving toward a narrow Qt-style app context.

## Phase 0: Guardrail Tests Before Refactoring

### Task 0.1: Lock Token Table Column Behavior

**Files:**
- Modify: `tests/test_token_table.py`
- Modify later: `oeapp/ui/token_table.py`

- [ ] Add a failing test proving `prep_case` appears in the existing `PrepObjCase` column after both `set_tokens()` and `update_annotation()`.
- [ ] Run: `.venv/bin/pytest tests/test_token_table.py -q`
- [ ] Expected: new test exposes current column drift or protects against regression.
- [ ] Commit message: `test: lock token table annotation columns`

### Task 0.2: Lock Search Result Semantics

**Files:**
- Modify: `tests/test_search.py`
- Modify later: `oeapp/models/project.py`
- Modify later: `oeapp/ui/main_window.py`

- [ ] Add tests for project-wide search counts and result order across OE surface, annotation root, ModE text, and notes.
- [ ] Add tests that search navigation still loads target chapter/section and focuses correct widget type.
- [ ] Run: `.venv/bin/pytest tests/test_search.py -q`
- [ ] Expected: pass before extraction.
- [ ] Commit message: `test: lock project search behavior`

### Task 0.3: Lock Project Reload Behavior

**Files:**
- Modify: `tests/test_main_window.py`
- Modify: `tests/test_sentence_card.py`

- [ ] Add focused tests that add, delete, and merge reload visible cards while preserving undo manager identity.
- [ ] Add test that added sentence still receives deferred focus/edit mode.
- [ ] Run: `.venv/bin/pytest tests/test_main_window.py tests/test_sentence_card.py -q`
- [ ] Expected: pass before extraction.
- [ ] Commit message: `test: lock project reload workflows`

## Phase 1: Low-Risk DRY Fixes In Existing Widgets

### Task 1.1: Extract Token Table Column Metadata

**Files:**
- Modify: `oeapp/ui/token_table.py`
- Modify: `tests/test_token_table.py`

- [ ] Add private `_AnnotationColumn` dataclass and `_ANNOTATION_COLUMNS` tuple.
- [ ] Replace repeated `setItem` blocks in `set_tokens()` and `update_annotation()` with one helper.
- [ ] Keep `TokenTable` public API unchanged.
- [ ] Run: `.venv/bin/pytest tests/test_token_table.py -q`
- [ ] Run: `.venv/bin/ruff check oeapp/ui/token_table.py tests/test_token_table.py`
- [ ] Run: `.venv/bin/mypy oeapp/ui/token_table.py tests/test_token_table.py`
- [ ] Run: `make napoleon-gate`
- [ ] Commit message: `refactor: centralize token table columns`

### Task 1.2: Extract Reusable UI Signal-Blocking Helper Only If Worth It

**Files:**
- Modify only if repeated local pattern becomes noisy: `oeapp/ui/dialogs/pos_form_system.py`, `oeapp/ui/highlighting.py`, `oeapp/ui/main_window.py`, `oeapp/ui/dialogs/annotation_modal.py`

- [ ] Audit `blockSignals(True)` / `blockSignals(False)` pairs.
- [ ] If no clear bug-prone cluster emerges, skip this task.
- [ ] If implemented, use a tiny context manager and update only the noisiest local cluster.
- [ ] Run targeted tests for touched files.
- [ ] Commit message: `refactor: simplify signal blocking`

## Phase 2: Move Search Data Discovery To Fat ORM Models

### Task 2.1: Create Shared Search Result Value Object

**Files:**
- Create: `oeapp/models/search_result.py`
- Modify: `oeapp/ui/main_window.py`
- Modify: `tests/test_search.py`

- [ ] Move `SearchResult` dataclass out of `main_window.py`.
- [ ] Keep field names and behavior unchanged.
- [ ] Import from `oeapp.models.search_result`.
- [ ] Run: `.venv/bin/pytest tests/test_search.py tests/test_main_window.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: share search result model`

### Task 2.2: Add Fat-ORM Project Search Helpers

**Files:**
- Modify: `oeapp/models/project.py`
- Modify: `tests/test_search.py`

- [ ] Add small composable model methods:
  - `Project.search_matches(pattern: str, scope: str) -> ProjectSearchMatches`
  - `Project._chapter_search_matches(...)`
  - `Project._section_search_matches(...)`
  - `Project._sentence_search_matches(...)`
- [ ] Keep database traversal and model relationship use inside ORM/model layer.
- [ ] Keep UI focus and highlighting out of the model layer.
- [ ] Add `ProjectSearchMatches` dataclass if useful, with results, total count, token map.
- [ ] Run: `.venv/bin/pytest tests/test_search.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: move search matching to project model`

### Task 2.3: Create Search Controller For UI State

**Files:**
- Create: `oeapp/ui/search_controller.py`
- Modify: `oeapp/ui/main_window.py`
- Modify: `tests/test_search.py`
- Modify: `tests/test_main_window.py`

- [ ] Move search input state, counter updates, clear behavior, navigation, and focus restore into `SearchController`.
- [ ] Make controller call `Project.search_matches(...)`.
- [ ] Keep `MainWindowActions.perform_search`, `next_match`, `prev_match`, and `clear_search` as compatibility delegates.
- [ ] Run: `.venv/bin/pytest tests/test_search.py tests/test_main_window.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: extract search controller`

## Phase 3: Extract Project Workspace UI Workflow

### Task 3.1: Create Project Workspace Controller

**Files:**
- Create: `oeapp/ui/project_workspace.py`
- Modify: `oeapp/ui/main_window.py`
- Modify: `tests/test_main_window.py`

- [ ] Move `ProjectUI` class from `main_window.py` into `project_workspace.py`.
- [ ] Rename only if low risk; otherwise keep class name `ProjectUI` in new module.
- [ ] Keep imports and compatibility attributes stable.
- [ ] Run: `.venv/bin/pytest tests/test_main_window.py tests/test_search.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: move project ui workflow module`

### Task 3.2: Deduplicate Reload After Structural Changes

**Files:**
- Modify: `oeapp/ui/project_workspace.py`
- Modify: `tests/test_main_window.py`
- Modify: `tests/test_sentence_card.py`

- [ ] Add helper like `_reload_after_structure_change(clear_search: bool, message: str)`.
- [ ] Use it for merge/delete.
- [ ] Add focused path for add that calls same helper but preserves new-card focus behavior.
- [ ] Confirm command manager identity remains stable.
- [ ] Run: `.venv/bin/pytest tests/test_main_window.py tests/test_sentence_card.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: unify project reload workflow`

### Task 3.3: Replace Ad Hoc Current IDs With Workspace Accessors

**Files:**
- Modify: `oeapp/ui/project_workspace.py`
- Modify: `oeapp/state.py`
- Modify: `oeapp/ui/main_window.py`
- Modify: `tests/test_state.py`
- Modify: `tests/test_main_window.py`

- [ ] Add explicit methods for current project/chapter/section id get/set.
- [ ] Keep existing `ApplicationState` keys working for compatibility.
- [ ] Replace repeated raw dict access in main UI with accessors where touched.
- [ ] Run: `.venv/bin/pytest tests/test_state.py tests/test_main_window.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: add current workspace accessors`

## Phase 4: Slim SentenceCard Without Moving Model Queries Away From Models

### Task 4.1: Extract Sentence Card Controller

**Files:**
- Create: `oeapp/ui/sentence_card_controller.py`
- Modify: `oeapp/ui/sentence_card.py`
- Modify: `tests/test_sentence_card.py`
- Modify: `tests/test_sentence_commands.py`

- [ ] Move command execution workflows for edit OE, translation edit, merge, add before/after, delete into controller methods.
- [ ] Keep confirmation dialogs parented to the widget.
- [ ] Keep ORM query calls through `Sentence.get_next_sentence(...)` and command objects.
- [ ] Keep `SentenceCard` signals unchanged.
- [ ] Run: `.venv/bin/pytest tests/test_sentence_card.py tests/test_sentence_commands.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: extract sentence card controller`

### Task 4.2: Extract Annotation Modal Routing

**Files:**
- Modify: `oeapp/ui/sentence_card_controller.py`
- Modify: `oeapp/ui/sentence_card.py`
- Modify: `tests/test_sentence_card.py`
- Modify: `tests/test_annotation_modal.py`

- [ ] Move selected token/range/idiom modal-routing logic out of `SentenceCard`.
- [ ] Keep modal construction and parent ownership Qt-native.
- [ ] Preserve `annotation_applied` signal behavior.
- [ ] Run: `.venv/bin/pytest tests/test_sentence_card.py tests/test_annotation_modal.py tests/test_idioms.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: extract annotation routing`

## Phase 5: Make Annotation Form State Explicit

### Task 5.1: Add Annotation Form State

**Files:**
- Create: `oeapp/ui/annotation_form_state.py`
- Modify: `oeapp/ui/dialogs/annotation_modal.py`
- Modify: `tests/test_annotation_modal.py`

- [ ] Add dataclass that represents POS, POS-specific values, confidence, TODO flag, meaning, sense, root.
- [ ] Add conversion helpers from dialog widgets to state and from state to `Annotation`.
- [ ] Keep database save/emit behavior unchanged.
- [ ] Run: `.venv/bin/pytest tests/test_annotation_modal.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: model annotation form state`

### Task 5.2: Remove MainWindow Top-Level Widget Discovery

**Files:**
- Modify: `oeapp/ui/dialogs/annotation_modal.py`
- Modify: call sites in `oeapp/ui/sentence_card.py` or `oeapp/ui/sentence_card_controller.py`
- Modify: `tests/test_annotation_modal.py`

- [ ] Pass required collaborators through constructor or parent/controller instead of scanning `QApplication.topLevelWidgets()`.
- [ ] Preserve dialog behavior and Qt ownership.
- [ ] Run: `.venv/bin/pytest tests/test_annotation_modal.py tests/test_annotation_preset_management_dialog.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: inject annotation modal collaborators`

## Phase 6: Qt-Native Token Table Model

### Task 6.1: Introduce TokenTableModel Beside Existing Widget

**Files:**
- Create: `oeapp/ui/token_table_model.py`
- Modify: `tests/test_token_table.py`

- [ ] Implement `QAbstractTableModel` for tokens and annotation columns.
- [ ] Keep column metadata from Phase 1.
- [ ] Add unit tests for row count, column count, header data, display data.
- [ ] Do not wire into UI yet.
- [ ] Run: `.venv/bin/pytest tests/test_token_table.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: add token table model`

### Task 6.2: Swap TokenTable To QTableView + TokenTableModel

**Files:**
- Modify: `oeapp/ui/token_table.py`
- Modify: `oeapp/ui/token_table_model.py`
- Modify: `tests/test_token_table.py`
- Modify: `tests/test_sentence_card.py`

- [ ] Replace item population with model assignment.
- [ ] Preserve public methods: `set_tokens`, `update_annotation`, `get_selected_token`, `select_token`, `select_token_by_id`, `refresh`.
- [ ] Preserve selection signals and keyboard annotation shortcuts.
- [ ] Run: `.venv/bin/pytest tests/test_token_table.py tests/test_sentence_card.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: use qt model for token table`

## Phase 7: Share Text Flow Domain Rules

### Task 7.1: Create Fat-Domain Text Flow Helpers

**Files:**
- Create: `oeapp/models/text_flow.py`
- Modify: `tests/test_full_translation_window.py`
- Modify: `tests/test_export_pdf.py`

- [ ] Move shared logic for paragraph-start detection, visible titles, and prose/verse separator decisions into domain helpers.
- [ ] Keep output-format decisions separate: plain text separator vs LaTeX separator can be adapter methods.
- [ ] Run: `.venv/bin/pytest tests/test_full_translation_window.py tests/test_export_pdf.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: share text flow rules`

### Task 7.2: Use Text Flow Helpers In Full View And PDF

**Files:**
- Modify: `oeapp/ui/full_translation_window.py`
- Modify: `oeapp/services/export_pdf.py`
- Modify: `tests/test_full_translation_window.py`
- Modify: `tests/test_export_pdf.py`

- [ ] Replace duplicated `_visible_titles`, `_separator`, and `_is_paragraph_start` logic.
- [ ] Preserve exact rendered text/PDF fixture behavior.
- [ ] Run: `.venv/bin/pytest tests/test_full_translation_window.py tests/test_export_pdf.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: reuse text flow rules`

## Phase 8: Gradual ApplicationState Cleanup Toward Qt-Style App Context

### Task 8.1: Add Narrow State Facade

**Files:**
- Modify: `oeapp/state.py`
- Modify: `tests/test_state.py`

- [ ] Add explicit methods/properties for copied annotation, selected sentence card, current ids, command manager, settings, and other stable app-wide state still needed globally.
- [ ] Keep dictionary keys for backward compatibility.
- [ ] Add tests for old dict API and new facade API.
- [ ] Make facade shape clearly suitable for later conversion from dict-like singleton to narrow `QObject` app context without changing callers again.
- [ ] Run: `.venv/bin/pytest tests/test_state.py -q`
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: add state facade methods`

### Task 8.2: Replace Raw State Access Opportunistically

**Files:**
- Modify only files already touched by earlier phases.

- [ ] Replace raw `application_state[...]` access only where local context is already being changed.
- [ ] Do not do a whole-app mechanical churn commit.
- [ ] Prefer moving transient UI/view state out of `ApplicationState` where an owning workspace/controller already exists.
- [ ] Run affected tests.
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: use state facade in ui workflow`

### Task 8.3: Localize Transient UI State And Define App Context Boundary

**Files:**
- Modify: `oeapp/state.py`
- Modify only already-touched UI workflow files if needed.
- Modify: `tests/test_state.py`
- Modify focused UI tests as needed.

- [ ] Classify each `ApplicationState` field/key as one of:
  - stable app-lifetime service/state
  - transient workspace/controller state
  - compatibility-only legacy entry
- [ ] Keep stable app-lifetime items global:
  - SQLAlchemy session
  - command manager
  - `QSettings`
  - current project id
  - current chapter/section ids if still broadly useful
- [ ] Move transient UI state out of global state when low-risk owners already exist:
  - selected sentence card
  - search origin/current match
  - other active selection/focus pointers
- [ ] Add a short docstring/comment block in `oeapp/state.py` describing the intended end-state: narrow Qt-style app context using explicit ownership plus signals/slots, not a generic shared bag.
- [ ] If safe in this phase, introduce a minimal signal-friendly structure or compatibility wrapper that makes a future `QObject`-based `AppContext` straightforward; do not do a full replacement if it would increase risk.
- [ ] Run focused tests for touched UI/workflow files.
- [ ] Run quality gate for touched Python files.
- [ ] Commit message: `refactor: localize transient app state`

## Phase 9: Post-Refactor Stabilization And Architecture Audit

### Task 9.1: Audit Refactored Touchpoints

**Files:**
- Modify only files already touched by Phases 1-8 (see plan hotspots and target file structure).

- [ ] Verify fat ORM ownership, controller/workflow boundaries, and ApplicationState classification remain consistent.
- [ ] Remove only low-risk obsolete shims; keep compatibility delegates that still serve callers.
- [ ] Deduplicate small selection-resolution helpers shared by workspace and search flows.
- [ ] Tighten typing/docstrings only where the refactor left rough edges.

### Task 9.2: Close Targeted Test Gaps

**Files:**
- Modify: `tests/test_text_flow.py` (create if missing)
- Modify focused UI tests only when audit finds a real gap.

- [ ] Add unit tests for shared `oeapp.models.text_flow` rules when not already covered indirectly.
- [ ] Run:
  - `.venv/bin/pytest tests/test_state.py tests/test_search.py tests/test_main_window.py tests/test_sentence_card.py tests/test_token_table.py tests/test_annotation_modal.py tests/test_full_translation_window.py tests/test_export_pdf.py tests/test_text_flow.py -q`
  - `.venv/bin/ruff check oeapp tests`
  - `.venv/bin/mypy oeapp tests`
  - `make napoleon-gate`
- [ ] Commit message: `refactor: phase 9 stabilization cleanup`

## Deferrals

- Do not introduce repository classes; conflicts with fat ORM preference.
- Do not rewrite all dialogs to model/view at once.
- Do not replace `ApplicationState` globally in one pass; evolve it gradually toward a narrow `QObject`-style app context only after callers use typed accessors and transient UI state has been localized.
- Do not thread exports/imports unless UI responsiveness requires it and tests prove no event-loop regression.
- Do not create a new framework or app architecture.

## Risk Register

- Search extraction can break focus restore or cross-section navigation.
  - Mitigation: Phase 0 search tests, keep UI navigation in controller, model owns matching only.
- Project reload extraction can lose undo stack.
  - Mitigation: explicit command manager identity tests.
- Token table model swap can break selection signals.
  - Mitigation: keep public `TokenTable` API and test signal behavior.
- Annotation form extraction can miss remembered-annotation special cases.
  - Mitigation: include remembered annotation tests in Phase 5.
- Text-flow sharing can change whitespace or PDF output.
  - Mitigation: full translation and PDF fixture tests before and after.

## First Recommended Commit

Start with Phase 0.1 and Phase 1.1:

1. Add token table column tests.
2. Centralize token table column metadata.
3. Fix any revealed `PrepObjCase` drift.
4. Run:
   - `.venv/bin/pytest tests/test_token_table.py -q`
   - `.venv/bin/ruff check oeapp/ui/token_table.py tests/test_token_table.py`
   - `.venv/bin/mypy oeapp/ui/token_table.py tests/test_token_table.py`
   - `make napoleon-gate`

This is small, low risk, behavior-preserving, and sets the pattern for later phases.

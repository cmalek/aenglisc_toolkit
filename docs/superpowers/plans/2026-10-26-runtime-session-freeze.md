# Runtime Session Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a pytest that fails when a Python file under `oeapp/` gains or loses a runtime-session lookup of a kind ADR 0011 names.

**Architecture:** One test module parses `oeapp/**/*.py` with the standard-library `ast` module. It counts six call names and loads of `app_context.session`, per file, per kind. A dict in that module is the allowlist. The test does not import `oeapp`, so it needs no database and no Qt. No production lookup changes.

**Tech Stack:** Python 3.13, stdlib `ast`, `.venv/bin/pytest`, `.venv/bin/mypy`.

**Spec:** `doc/source/architecture/adr_0011_runtime_session_freeze.rst` (D1–D6).

**Package decision:** Catalog search (`static analysis of Python source with ast`, role `planning`) returned `no_match`. Use stdlib `ast`. Do not add libcst, astroid, or import-linter.

```json
{"status":"no_match","phase":"planning","capability":null,"profile_id":null,"entry_id":null,"question":null,"system_dependencies":null}
```

## Global Constraints

- Do not edit production lookups. Do not add a session parameter. Do not migrate model classmethods (Trello https://trello.com/c/dNaoAIwU). Do not start F1 or F7.
- Do not scan `tests/`. `tests/conftest.py`, `tests/test_state.py`, `tests/test_commands.py`, and `tests/test_db.py` stay free to touch the session.
- Counts are per file and per kind. Kinds are the call names `get_runtime_session`, `set_runtime_session`, `clear_runtime_session`, `_get_session`, `get_session`, and `SessionLocal`, plus the load kind `app_context.session`.
- Exact set membership. `get_runtime_session` is not a `get_session` call.
- Count calls (bare name or attribute) and `ast.Load` of attribute `session` whose value is the name `app_context` or an attribute named `app_context`. Do not count stores, imports, function definitions, comments, or docstrings.
- Do not count `self.session`, `_RUNTIME_STATE.session`, or `ctx.session` after `ctx = self.app_context`.
- `get_session` has zero calls today, so it is absent from the allowlist. The two `SessionLocal()` calls in `oeapp/db.py` are present.
- The test goes green if someone raises the allowlist to match a new lookup. Review still rejects that raise. D5 of the ADR is the only later exception, and this plan does not grant it.
- No `CONTEXT.md` change. No help change. No Alembic migration.
- `pyproject.toml` sets `[tool.ruff] extend-exclude = ["tests", ...]`. Do not treat a ruff failure on this test file as a gate: an explicit ruff check of `tests/test_db.py` already reports `S101` for every `assert`. Run `.venv/bin/mypy tests/test_runtime_session_freeze.py` and `make napoleon-gate`.
- Run `graphify update .` after the test file exists. Do not `git add graphify-out`. That tree already has unrelated local changes.
- Commands use `.venv/bin/pytest` and `.venv/bin/mypy` from the repo root.

## Review Focus

- A new `self.app_context.session` in `oeapp/ui/main_window.py` must change the scanned count. Task 3.
- `self.session = ...` and `_RUNTIME_STATE.session = ...` must not count. Task 2.
- `ctx = self.app_context` then `ctx.session` must not count. Task 2.
- `oeapp/db.py` contributes `SessionLocal: 2` and does not contribute `get_session`. Task 3.

## File Structure

- Create: `tests/test_runtime_session_freeze.py` — counter, tree scan, and allowlist. Nothing else imports it.
- Modify: `doc/source/architecture/adr_0011_runtime_session_freeze.rst` — the last Consequences bullet, after the test exists.
- Do not create a production module. The ADR puts the allowlist in the test.

---

### Task 1: Count the six call names

**Files:**
- Create: `tests/test_runtime_session_freeze.py`

**Interfaces:**
- Produces: `count_runtime_session_lookups(source: str) -> dict[str, int]`
- This task counts calls only. Task 2 adds `app_context.session` loads.

- [ ] **Step 1: Write the failing test**

Create `tests/test_runtime_session_freeze.py` with this test and no helper yet:

```python
"""Freeze product-code lookups of the runtime SQLAlchemy session."""

from __future__ import annotations


def test_call_names_ignore_imports_defs_comments_and_docstrings() -> None:
    source = '''
from oeapp.db import get_runtime_session, get_session
def get_runtime_session():
    """Call get_runtime_session() in a docstring."""
    # get_runtime_session()
    get_runtime_session()
    SessionLocal = sessionmaker()
    session = SessionLocal()
    Annotation._get_session()
    get_session()
'''
    assert count_runtime_session_lookups(source) == {
        "SessionLocal": 1,
        "_get_session": 1,
        "get_runtime_session": 1,
        "get_session": 1,
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py::test_call_names_ignore_imports_defs_comments_and_docstrings -q`

Expected: FAIL with `NameError: count_runtime_session_lookups`

- [ ] **Step 3: Implement call counting**

Keep `from __future__ import annotations` as the first statement after the module docstring. Put `import ast` on the next line. Put the constant and function below that import and above the test. Do not handle `app_context.session` yet.

```python
import ast

LOOKUP_CALLS = frozenset(
    {
        "SessionLocal",
        "_get_session",
        "clear_runtime_session",
        "get_runtime_session",
        "get_session",
        "set_runtime_session",
    }
)


def count_runtime_session_lookups(source: str) -> dict[str, int]:
    """Count runtime-session lookup kinds in one source string."""
    counts: dict[str, int] = {}
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        kind = None
        if isinstance(func, ast.Name) and func.id in LOOKUP_CALLS:
            kind = func.id
        elif isinstance(func, ast.Attribute) and func.attr in LOOKUP_CALLS:
            kind = func.attr
        if kind is not None:
            counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py::test_call_names_ignore_imports_defs_comments_and_docstrings -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_runtime_session_freeze.py
git commit -m "$(cat <<'EOF'
test: count runtime-session call names

EOF
)"
```

### Task 2: Count app_context.session loads

**Files:**
- Modify: `tests/test_runtime_session_freeze.py`

**Interfaces:**
- Consumes: `count_runtime_session_lookups` from Task 1.
- Produces: the same function, now also returning `"app_context.session"`.

- [ ] **Step 1: Write the failing test**

Append:

```python
def test_app_context_session_loads_skip_stores_and_aliases() -> None:
    source = '''
def f(self, app_context):
    self.session = self.app_context.session
    if app_context.session:
        self.app_context.session.refresh(token)
    _RUNTIME_STATE.session = None
    ctx = self.app_context
    ctx.session.refresh(token)
'''
    assert count_runtime_session_lookups(source) == {
        "app_context.session": 3,
    }
```

The three loads are the assignment value, the `if`, and `.refresh`. `self.session =`, `_RUNTIME_STATE.session =`, and `ctx.session` do not count.

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py::test_app_context_session_loads_skip_stores_and_aliases -q`

Expected: FAIL. The assertion compares `{'app_context.session': 3}` with `{}`.

- [ ] **Step 3: Count those loads**

Replace `count_runtime_session_lookups` with the block below: the `APP_CONTEXT_SESSION` constant and the four functions `_lookup_kind`, `count_runtime_session_lookups`, `_call_kind`, and `_is_app_context_session_load`. Keep `LOOKUP_CALLS` and the Task 1 test. Leave `from __future__ import annotations` first and `import ast` immediately after it.

```python
APP_CONTEXT_SESSION = "app_context.session"


def count_runtime_session_lookups(source: str) -> dict[str, int]:
    """Count runtime-session lookup kinds in one source string."""
    counts: dict[str, int] = {}
    for node in ast.walk(ast.parse(source)):
        kind = _lookup_kind(node)
        if kind is not None:
            counts[kind] = counts.get(kind, 0) + 1
    return dict(sorted(counts.items()))


def _lookup_kind(node: ast.AST) -> str | None:
    """Return the lookup kind of one AST node, if it is a lookup."""
    if isinstance(node, ast.Call):
        return _call_kind(node.func)
    if _is_app_context_session_load(node):
        return APP_CONTEXT_SESSION
    return None


def _call_kind(func: ast.expr) -> str | None:
    """Return the call name when the function is one of the six names."""
    if isinstance(func, ast.Name) and func.id in LOOKUP_CALLS:
        return func.id
    if isinstance(func, ast.Attribute) and func.attr in LOOKUP_CALLS:
        return func.attr
    return None


def _is_app_context_session_load(node: ast.AST) -> bool:
    """Return whether the node loads app_context.session."""
    if not isinstance(node, ast.Attribute):
        return False
    if node.attr != "session" or not isinstance(node.ctx, ast.Load):
        return False
    value = node.value
    if isinstance(value, ast.Name):
        return value.id == "app_context"
    return isinstance(value, ast.Attribute) and value.attr == "app_context"
```

Walking both the `Call` and its `func` attribute does not double-count: the attribute is a lookup only when its name is `session` and its value is `app_context`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py -q`

Expected: PASS (both tests)

- [ ] **Step 5: Commit**

```bash
git add tests/test_runtime_session_freeze.py
git commit -m "$(cat <<'EOF'
test: count app_context.session loads in the runtime-session freeze

EOF
)"
```

### Task 3: Allowlist the oeapp tree

**Files:**
- Modify: `tests/test_runtime_session_freeze.py`

**Interfaces:**
- Consumes: `count_runtime_session_lookups`
- Produces: `scan_runtime_session_lookups(oeapp: Path) -> dict[str, dict[str, int]]` and `ALLOWLIST`

- [ ] **Step 1: Write the failing test**

Add `from pathlib import Path` to the imports. Append the empty allowlist, the scanner, and the test. The empty allowlist is what makes this step fail.

```python
ALLOWLIST: dict[str, dict[str, int]] = {}


def scan_runtime_session_lookups(
    oeapp: Path,
) -> dict[str, dict[str, int]]:
    """Count lookup kinds in every Python file under oeapp."""
    found: dict[str, dict[str, int]] = {}
    for path in sorted(oeapp.rglob("*.py")):
        counts = count_runtime_session_lookups(
            path.read_text(encoding="utf-8")
        )
        if not counts:
            continue
        relative = Path("oeapp") / path.relative_to(oeapp)
        found[relative.as_posix()] = counts
    return found


def test_oeapp_lookups_match_the_allowlist() -> None:
    root = Path(__file__).resolve().parents[1]
    found = scan_runtime_session_lookups(root / "oeapp")
    assert found == ALLOWLIST
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py::test_oeapp_lookups_match_the_allowlist -q`

Expected: FAIL. Pytest's assertion diff shows `oeapp/db.py`, `oeapp/state.py`, `oeapp/ui/main_window.py`, and the other files that have lookups. `ALLOWLIST` on the other side is `{}`.

- [ ] **Step 3: Record today's counts**

Replace `ALLOWLIST: dict[str, dict[str, int]] = {}` with this dict. Keys and inner keys are sorted. These counts were measured with the Task 2 rules against the tree on 2026-10-26. If Step 2's diff disagrees with a line here, the tree changed after the plan: use the diff, do not invent a third number, and do not raise a count to hide a lookup this plan added. This plan adds no production lookup.

```python
ALLOWLIST: dict[str, dict[str, int]] = {
    "oeapp/commands/annotation.py": {"_get_session": 6},
    "oeapp/commands/hierarchy.py": {"_get_session": 8},
    "oeapp/commands/note.py": {"get_runtime_session": 1},
    "oeapp/commands/paragraph.py": {"_get_session": 4},
    "oeapp/commands/sentence.py": {"_get_session": 4},
    "oeapp/db.py": {"SessionLocal": 2},
    "oeapp/models/annotation.py": {"_get_session": 4},
    "oeapp/models/annotation_preset.py": {"_get_session": 5},
    "oeapp/models/chapter.py": {"_get_session": 7},
    "oeapp/models/idiom.py": {"_get_session": 3},
    "oeapp/models/mixins.py": {
        "_get_session": 2,
        "get_runtime_session": 1,
    },
    "oeapp/models/note.py": {"_get_session": 2},
    "oeapp/models/paragraph.py": {"_get_session": 7},
    "oeapp/models/project.py": {"_get_session": 8},
    "oeapp/models/remembered_annotation.py": {"_get_session": 4},
    "oeapp/models/section.py": {"_get_session": 8},
    "oeapp/models/sentence.py": {"_get_session": 12},
    "oeapp/models/token.py": {"_get_session": 7},
    "oeapp/services/annotation_propagation.py": {"_get_session": 2},
    "oeapp/services/export_docx.py": {"_get_session": 1},
    "oeapp/services/import_export.py": {"_get_session": 2},
    "oeapp/services/wyrdcraeft_ingest.py": {"_get_session": 1},
    "oeapp/state.py": {
        "clear_runtime_session": 1,
        "get_runtime_session": 1,
        "set_runtime_session": 2,
    },
    "oeapp/ui/dialogs/annotation_preset_management.py": {
        "_get_session": 1,
    },
    "oeapp/ui/dialogs/note_dialog.py": {"app_context.session": 2},
    "oeapp/ui/main_window.py": {"app_context.session": 6},
    "oeapp/ui/notes_panel.py": {"app_context.session": 2},
    "oeapp/ui/oe_text_edit.py": {"get_runtime_session": 1},
    "oeapp/ui/project_workspace.py": {"app_context.session": 3},
    "oeapp/ui/sentence_card_controller.py": {"get_runtime_session": 1},
}
```

- [ ] **Step 4: Run the tests and the gates**

Run: `.venv/bin/pytest tests/test_runtime_session_freeze.py -q`

Expected: PASS (3 tests)

Run: `.venv/bin/mypy tests/test_runtime_session_freeze.py`

Expected: no issues

Run: `make napoleon-gate`

Expected: no new violations. This test file is under `tests/` and the gate skips that tree.

Run: `graphify update .`

Expected: the command finishes. Leave `graphify-out/` unstaged.

- [ ] **Step 5: Commit**

```bash
git add tests/test_runtime_session_freeze.py
git commit -m "$(cat <<'EOF'
test: freeze oeapp runtime-session lookup counts

EOF
)"
```

### Task 4: Point ADR 0011 at the test

**Files:**
- Modify: `doc/source/architecture/adr_0011_runtime_session_freeze.rst` (the last Consequences bullet)

- [ ] **Step 1: Replace the "not in the tree yet" bullet**

Replace:

```rst
- Until ``tests/test_runtime_session_freeze.py`` is added, nothing enforces
  D3. Acceptance is of this decision. The test is the enforcement, and it
  is not in the tree yet.
```

with:

```rst
- ``tests/test_runtime_session_freeze.py`` enforces D3. It fails when the
  allowlist and the tree disagree. A diff that raises a count and edits
  the allowlist to match stays green. Review rejects that raise. D5 is
  the only later exception, and only where a caller has to obtain the
  runtime session in order to pass it on.
```

Do not otherwise edit the ADR.

- [ ] **Step 2: Check the heading adornments still match**

The bullet change does not touch headings. Confirm the file still has the title overline and underline the same length as `ADR 0011: Freeze runtime-session lookups at today's call sites`.

- [ ] **Step 3: Commit**

```bash
git add doc/source/architecture/adr_0011_runtime_session_freeze.rst
git commit -m "$(cat <<'EOF'
docs: record that the runtime-session freeze test enforces ADR 0011

EOF
)"
```

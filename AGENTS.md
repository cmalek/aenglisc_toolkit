# AGENTS.md

- use .venv/bin/python as python
- use .venv/bin/pytest as pytest
- use .venv/bin/ruff as ruff
- use .venv/bin/mypy as mypy
- use `uv add <package>` to add a core package
- use `uv add --group=test <package>` to add a test package
- use `uv add --group=docs <package>` to add a docs package
- use `uv add --group=dev <package>` to add a dev-only package
- always use `/usr/bin/cd` to change directories; bare `cd` is a bash function and breaks agent shells

## Tooling Preflight (Required)

Before planning or implementation, show concise evidence of:

1. `graphify` for prior context and codebase exploration
2. At least one `code-index` call (search/find/symbol/summary as useful)
3. `context7` and/or `package-registry-mcp` when external library/package behavior, versioning, or package details matter

In an early progress update: tool names used + one line per result. If a tool is not relevant, say so in one line.

During planning, please use `graphify` and `code-index` often to flesh out plans.

## ADRs

Write all ADRs as restructuredtext files in `doc/source/architecture/`, and
add each new one to the `architecture/index.rst` toctree.

Start every new ADR from the schema in `doc/adr_template.md` (Title, Status,
Context, Decision, Consequences, optional Alternatives Considered and
Related). That template file is not published by Sphinx — it is a
copy-paste starting point only, so copy its structure into the new
`doc/source/architecture/adr_NNNN_slug.rst` file rather than editing it
in place.

## Python Environment (Required)

Before any Python work in `wordwending`, activate the repo-local virtual
environment:

```bash
source .venv/bin/activate
```

This applies to:

- running Python commands
- running tests
- running linters or type checks
- running Sphinx docs builds
- validating imports or package availability

Do not assume the global interpreter matches the project environment.

During Planning:

- Use `code-index` and `graphify` to find files and function calls

In an early progress update: tool names used + one line per result. If a tool is not relevant, say so in one line.

## Post-Implementation Quality Gate (Required)

After implementation edits [Important: Python code files only]:

1. `ruff` on touched files (or broader if needed)
2. `.venv/bin/mypy` on touched files (or broader if needed)
3. `make napoleon-gate`
4. Fix all reported problems before finishing

## Implementation Priority (Required)

Implement the correct product code directly. Do not add runtime patching, indirection, monkey-patching, startup hooks, or similar workarounds just to dodge doc-gate noise, baseline drift, or other documentation-tool friction.

1. Prefer 3rd-party open source packages that solve or can greatly assist the ADR/Spec/problem before building it ourselves

   a. Judge the 3rd-party package for code quality: commit cadence (is it abandoned); stars on github, other typical criteria and factor that into your decision.
   b. Use `context7` and `package-registry-mcp` to help you in searching and evaluating

2. Put the change in the correct source file, even when that file has noisy docs or baseline issues
3. Report quality-gate blockers separately, noting pre-existing or unrelated failures
4. Architecture and correctness beat avoiding documentation churn

## Project Structure (Mandatory)

1. All data models (Pydantic, `@dataclass`, `QT` model-like subclasses, SQLAlchemy ORM models) go in `oeapp.models`
2. Business logic → service classes in `oeapp.services`.  Services serve as a bridge between the UI elements and signals and the models and external services.
3. We want FAT ORM models -- put any DB centric operations on the on the appropriate ORM model; don't disperse them througought services.
4. UI: all UI elements and their wiring and connections go in `oeapp.ui`.  This is a PySide6 codebase.
5. Dialogs: UI Dialogs go in `oeapp.ui.dialogs`
6. SQLAlchemy: this app is used by other people on their desktops, so any change to a SQLAlchemy model must be accompanied by an Alembic migration.  Use `bin/create_migration.py` to make the migrations.
7. We strongly enforce clear user-facing in app help.  The help engine and pages are in `oeapp.help`

## Architecture (Required)

Prefer cohesive, human-comprehensible classes over loose function collections, even when mostly stateless.

- Model real workflow boundaries and stable domain concepts, not arbitrary namespaces
- Use constructor injection and explicit collaborators
- Keep methods and function bodies ≤ 60 lines
- **Single responsibility:** one clear job per service class; no god classes mixing many different concerns
- Split multi-concern workflows into named collaborators that map to human-understandable concepts
- Keep the public service a thin facade with a small entry-point API
- Put per-run orchestration and mutable run state in a dedicated execution/orchestrator class
- Prefer stateless collaborators; isolate per-run mutable state in one accumulator/orchestrator

## Documentation Contract (Required)

For all non-test Python code:

**Class docstrings:** describe the contract; include constructor `Args:` when constructor arguments exist.

**Function/method docstrings:** brief description plus only applicable sections:

- `Side Effects:` — real side effects only
- `Args:` — positional args only
- `Keyword Args:` — keyword args only
- `Raises:` — meaningful exceptions only
- `Returns:` or `Yields:` — when applicable

Do not add placeholder sections or empty/`None`-semantic sections.

**Napoleon `#:` comments** on class attributes, `__init__` instance attributes, and module-level globals.

Enforcement: `make napoleon-gate` (no new violations vs baseline); `make napoleon-gate-strict` when explicitly requested.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:

- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

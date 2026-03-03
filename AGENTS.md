# AGENTS.md

## Local Overrides

This repository inherits shared defaults from:
- `../AGENTS.md` (workspace-root shared instructions)

## Repository Bootstrap Requirements

These requirements apply at the start of every new session in this repository.

1. Read `../AGENTS.md` before planning or implementation.
2. Treat the shared file as mandatory for this repository, not optional guidance.
3. Confirm in an early progress update that the shared file was read.

## Tooling Preflight Evidence (Required)

Before planning or implementation, every agent must provide concise evidence of:

1. `memory_search` for relevant prior context.
2. At least one `aidex` call (`aidex_session` plus a query/signature/tree/files/status call as useful).
3. At least one `code-index` call (search/find/symbol/summary as useful).
4. `context7` and/or `package-registry-mcp` when external library/package behavior, versioning, or package details are relevant.

In an early progress update, include the tool names used and one line on what each returned.
If a tool is not relevant for the task, state that explicitly in one line.

## Memory MCP Usage (MUST)

For memory-related preflight and recall work, agents MUST use Memory MCP tools directly.

1. Use `mcp__memory-mcp__memory_search` to satisfy memory preflight/context lookup.
2. Do not use shell/CLI commands (for example, `memory ...`) as a substitute for Memory MCP preflight evidence.
3. If Memory MCP appears unavailable or errors, run `mcp__memory-mcp__memory_health` or `mcp__memory-mcp__memory_stats` and report the exact blocker in the progress update.
4. Only proceed with fallback preflight context (`aidex`/`code-index`) after explicitly documenting the Memory MCP blocker.

## Post-Implementation Quality Gate (Required)

After implementation edits are complete:

1. Run `ruff` on the touched files (or broader target if the task requires it).
2. Run `mypy` on the touched files (or broader target if the task requires it).
3. Fix all problems reported by those runs before finishing the task.

## Migration Creation (MUST)

When a schema migration is required, agents MUST follow this workflow:

1. Always create migrations with `bin/create_migration.py "<message>"` (never hand-create Alembic files).
2. Set `OE_ANNOTATOR_DB_PATH` to a writable local/test DB path before running migration commands, to avoid writing under `~/Library/Application Support/...` in sandboxed sessions.
3. Hard preflight guarantee: before running `bin/create_migration.py`, verify the target DB's `alembic_version` equals Alembic `head`. Do not run migration autogenerate until this is true.
4. If the DB is not at head (or autogenerate reports `Target database is not up to date`), initialize the temporary DB from current models (import `oeapp.models`, run `Base.metadata.create_all(...)`), stamp `alembic_version` to current head, verify again, then run `bin/create_migration.py`.
5. Review the generated migration and ensure it contains only the intended schema changes; do not keep spurious full-schema diffs.

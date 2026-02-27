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

## Post-Implementation Quality Gate (Required)

After implementation edits are complete:

1. Run `ruff` on the touched files (or broader target if the task requires it).
2. Run `mypy` on the touched files (or broader target if the task requires it).
3. Fix all problems reported by those runs before finishing the task.

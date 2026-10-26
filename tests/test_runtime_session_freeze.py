"""Freeze product-code lookups of the runtime SQLAlchemy session."""

from __future__ import annotations

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

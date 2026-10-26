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

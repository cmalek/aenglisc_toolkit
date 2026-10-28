"""Freeze product-code lookups of the runtime SQLAlchemy session."""

from __future__ import annotations

import ast
from pathlib import Path

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
MODULE_SCOPE = "<module>"
_PROPERTY_ACCESSORS = frozenset({"deleter", "setter"})
_SCOPED_DEF = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def count_runtime_session_lookups(source: str) -> dict[str, dict[str, int]]:
    """
    Count lookup kinds for each enclosing function in one source string.

    Args:
        source: Python source to scan.

    Returns:
        Enclosing-function names mapped to kind counts. The module body uses
        ``<module>``. A property setter or deleter is a separate name.

    """
    counts: dict[str, dict[str, int]] = {}
    _accumulate(ast.parse(source), [], counts)
    return {
        scope: dict(sorted(kinds.items()))
        for scope, kinds in sorted(counts.items())
    }


def _accumulate(
    node: ast.AST,
    stack: list[str],
    counts: dict[str, dict[str, int]],
) -> None:
    """
    Record lookups in one node, keeping definitions in their own scope.

    Side Effects:
        Updates ``counts`` with lookups found under this node.

    Args:
        node: AST node to walk.
        stack: Enclosing class and function names, outermost first.
        counts: Scope map updated with any lookup in this node.

    """
    if isinstance(node, _SCOPED_DEF):
        _accumulate_definition(node, stack, counts)
        return
    kind = _lookup_kind(node)
    if kind is not None:
        _record(stack, kind, counts)
    for child in ast.iter_child_nodes(node):
        _accumulate(child, stack, counts)


def _accumulate_definition(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    stack: list[str],
    counts: dict[str, dict[str, int]],
) -> None:
    """
    Walk a class or function, with only its body inside the new scope.

    Side Effects:
        Updates ``counts`` with lookups found in this definition.

    Args:
        node: Class or function definition.
        stack: Enclosing class and function names, outermost first.
        counts: Scope map updated with lookups in this definition.

    """
    body_ids = {id(statement) for statement in node.body}
    for child in ast.iter_child_nodes(node):
        if id(child) not in body_ids:
            _accumulate(child, stack, counts)
    inner = [*stack, _scope_name(node)]
    for statement in node.body:
        _accumulate(statement, inner, counts)


def _scope_name(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
) -> str:
    """
    Return the scope name for a class or function definition.

    Args:
        node: Class or function definition.

    Returns:
        The definition name, with ``.setter`` or ``.deleter`` appended when
        that decorator is present.

    """
    for decorator in getattr(node, "decorator_list", ()):
        if (
            isinstance(decorator, ast.Attribute)
            and decorator.attr in _PROPERTY_ACCESSORS
        ):
            return f"{node.name}.{decorator.attr}"
    return node.name


def _record(
    stack: list[str],
    kind: str,
    counts: dict[str, dict[str, int]],
) -> None:
    """
    Add one lookup to the scope named by the stack.

    Side Effects:
        Updates ``counts`` for the scope named by ``stack``.

    Args:
        stack: Enclosing class and function names, outermost first.
        kind: Lookup kind to record.
        counts: Scope map updated with this lookup.

    """
    scope = ".".join(stack) if stack else MODULE_SCOPE
    bucket = counts.setdefault(scope, {})
    bucket[kind] = bucket.get(kind, 0) + 1


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
        "get_runtime_session": {
            "SessionLocal": 1,
            "_get_session": 1,
            "get_runtime_session": 1,
            "get_session": 1,
        },
    }


def test_app_context_session_loads_skip_stores_and_aliases() -> None:
    source = """
def f(self, app_context):
    self.session = self.app_context.session
    if app_context.session:
        self.app_context.session.refresh(token)
    _RUNTIME_STATE.session = None
    ctx = self.app_context
    ctx.session.refresh(token)
"""
    assert count_runtime_session_lookups(source) == {
        "f": {"app_context.session": 3},
    }


def test_property_setter_is_a_separate_scope() -> None:
    source = """
class App:
    @property
    def session(self):
        return get_runtime_session()

    @session.setter
    def session(self, session):
        set_runtime_session(session)
"""
    assert count_runtime_session_lookups(source) == {
        "App.session": {"get_runtime_session": 1},
        "App.session.setter": {"set_runtime_session": 1},
    }


def test_signature_lookups_stay_outside_the_function_body() -> None:
    source = """
def outer(session=get_runtime_session()):
    def inner():
        return _get_session()
"""
    assert count_runtime_session_lookups(source) == {
        MODULE_SCOPE: {"get_runtime_session": 1},
        "outer.inner": {"_get_session": 1},
    }


ALLOWLIST: dict[str, dict[str, dict[str, int]]] = {
    "oeapp/commands/annotation.py": {
        "AnnotateTokenCommand.execute": {"_get_session": 1},
        "AnnotateTokenCommand.undo": {"_get_session": 1},
        "ApplyAnnotationPropagationCommand.execute": {"_get_session": 1},
        "ApplyAnnotationPropagationCommand.undo": {"_get_session": 1},
        "ApplyRememberedAnnotationsCommand.execute": {"_get_session": 1},
        "ApplyRememberedAnnotationsCommand.undo": {"_get_session": 1},
    },
    "oeapp/commands/hierarchy.py": {
        "MergeChapterCommand.execute": {"_get_session": 1},
        "MergeChapterCommand.undo": {"_get_session": 1},
        "MergeSectionCommand.execute": {"_get_session": 1},
        "MergeSectionCommand.undo": {"_get_session": 1},
        "SplitChapterCommand.execute": {"_get_session": 1},
        "SplitChapterCommand.undo": {"_get_session": 1},
        "SplitSectionCommand.execute": {"_get_session": 1},
        "SplitSectionCommand.undo": {"_get_session": 1},
    },
    "oeapp/commands/note.py": {
        "AddNoteCommand.get_note_number": {"get_runtime_session": 1},
    },
    "oeapp/commands/paragraph.py": {
        "MergeParagraphCommand.execute": {"_get_session": 1},
        "MergeParagraphCommand.undo": {"_get_session": 1},
        "SplitParagraphCommand.execute": {"_get_session": 1},
        "SplitParagraphCommand.undo": {"_get_session": 1},
    },
    "oeapp/commands/sentence.py": {
        "AddSentenceCommand.execute": {"_get_session": 1},
        "DeleteSentenceCommand.undo": {"_get_session": 1},
        "MergeSentenceCommand.execute": {"_get_session": 1},
        "MergeSentenceCommand.undo": {"_get_session": 1},
    },
    "oeapp/db.py": {
        "get_runtime_session": {"SessionLocal": 1},
        "get_session": {"SessionLocal": 1},
    },
    "oeapp/models/annotation.py": {
        "Annotation.exists": {"_get_session": 1},
        "Annotation.get": {"_get_session": 1},
        "Annotation.get_by_idiom": {"_get_session": 1},
        "Annotation.get_by_token": {"_get_session": 1},
    },
    "oeapp/models/annotation_preset.py": {
        "AnnotationPreset.create": {"_get_session": 1},
        "AnnotationPreset.from_json": {"_get_session": 1},
        "AnnotationPreset.get": {"_get_session": 1},
        "AnnotationPreset.get_all_by_pos": {"_get_session": 1},
        "AnnotationPreset.update": {"_get_session": 1},
    },
    "oeapp/models/chapter.py": {
        "Chapter.create": {"_get_session": 1},
        "Chapter.from_json": {"_get_session": 1},
        "Chapter.get": {"_get_session": 1},
        "Chapter.get_chapters_after": {"_get_session": 1},
        "Chapter.last_section_number": {"_get_session": 1},
        "Chapter.list": {"_get_session": 1},
        "Chapter.previous_chapter": {"_get_session": 1},
    },
    "oeapp/models/idiom.py": {
        "Idiom.create": {"_get_session": 1},
        "Idiom.from_json": {"_get_session": 1},
        "Idiom.get": {"_get_session": 1},
    },
    "oeapp/models/mixins.py": {
        "SaveDeleteMixin.delete": {"_get_session": 1},
        "SaveDeleteMixin.save": {"_get_session": 1},
        "SessionMixin._get_session": {"get_runtime_session": 1},
    },
    "oeapp/models/note.py": {
        "Note.create": {"_get_session": 1},
        "Note.get": {"_get_session": 1},
    },
    "oeapp/models/paragraph.py": {
        "Paragraph.create": {"_get_session": 1},
        "Paragraph.from_json": {"_get_session": 1},
        "Paragraph.get": {"_get_session": 1},
        "Paragraph.get_paragraphs_after": {"_get_session": 1},
        "Paragraph.last_sentence_number": {"_get_session": 1},
        "Paragraph.list": {"_get_session": 1},
        "Paragraph.previous_paragraph": {"_get_session": 1},
    },
    "oeapp/models/project.py": {
        "Project.append_oe_text": {"_get_session": 1},
        "Project.create": {"_get_session": 1},
        "Project.exists": {"_get_session": 1},
        "Project.first": {"_get_session": 1},
        "Project.get": {"_get_session": 1},
        "Project.last_chapter_number": {"_get_session": 1},
        "Project.list": {"_get_session": 1},
        "Project.total_token_count": {"_get_session": 1},
    },
    "oeapp/models/remembered_annotation.py": {
        "RememberedAnnotation.get": {"_get_session": 1},
        "RememberedAnnotation.get_for_scope": {"_get_session": 1},
        "RememberedAnnotation.list_for_scope": {"_get_session": 1},
        "RememberedAnnotation.matching_tokens": {"_get_session": 1},
    },
    "oeapp/models/section.py": {
        "Section.create": {"_get_session": 1},
        "Section.from_json": {"_get_session": 1},
        "Section.get": {"_get_session": 1},
        "Section.get_paragraphs_after": {"_get_session": 1},
        "Section.get_sections_after": {"_get_session": 1},
        "Section.last_paragraph_number": {"_get_session": 1},
        "Section.list": {"_get_session": 1},
        "Section.previous_section": {"_get_session": 1},
    },
    "oeapp/models/sentence.py": {
        "Sentence._calculate_paragraph_and_sentence_numbers": {
            "_get_session": 1,
        },
        "Sentence.create": {"_get_session": 1},
        "Sentence.from_json": {"_get_session": 1},
        "Sentence.get": {"_get_session": 1},
        "Sentence.get_next_sentence": {"_get_session": 1},
        "Sentence.list": {"_get_session": 1},
        "Sentence.recalculate_project_structure": {"_get_session": 1},
        "Sentence.renumber_sentences": {"_get_session": 1},
        "Sentence.restore_display_orders": {"_get_session": 1},
        "Sentence.subsequent_sentences": {"_get_session": 1},
        "Sentence.update": {"_get_session": 1},
    },
    "oeapp/models/token.py": {
        "Token._update_idioms_for_token_changes": {"_get_session": 1},
        "Token._update_notes_for_token_changes": {"_get_session": 1},
        "Token.create_from_sentence": {"_get_session": 1},
        "Token.from_json": {"_get_session": 1},
        "Token.get": {"_get_session": 1},
        "Token.list": {"_get_session": 1},
        "Token.update_from_sentence": {"_get_session": 1},
    },
    "oeapp/services/annotation_propagation.py": {
        "AnnotationPropagationService._meaning_targets": {"_get_session": 1},
        "AnnotationPropagationService._project_tokens": {"_get_session": 1},
    },
    "oeapp/services/export_docx.py": {
        "DOCXExporter.__init__": {"_get_session": 1},
    },
    "oeapp/services/import_export.py": {
        "ProjectExporter.__init__": {"_get_session": 1},
        "ProjectImporter.__init__": {"_get_session": 1},
    },
    "oeapp/services/wyrdcraeft_ingest.py": {
        "WyrdcraeftIngestService.__init__": {"_get_session": 1},
    },
    "oeapp/state.py": {
        "AppContext.__init__": {"set_runtime_session": 1},
        "AppContext.close_session": {"clear_runtime_session": 1},
        "AppContext.session": {"get_runtime_session": 1},
        "AppContext.session.setter": {"set_runtime_session": 1},
    },
    "oeapp/ui/dialogs/annotation_preset_management.py": {
        "AnnotationPresetManagementDialog.__init__": {"_get_session": 1},
    },
    "oeapp/ui/dialogs/note_dialog.py": {
        "NoteDialog._on_delete_clicked": {"app_context.session": 1},
        "NoteDialog._on_save_clicked": {"app_context.session": 1},
    },
    "oeapp/ui/main_window.py": {
        "MainWindow._show_startup_dialog": {"app_context.session": 1},
        "MainWindowActions.export_old_english_text": {"app_context.session": 1},
        "MainWindowActions.export_project_docx": {"app_context.session": 1},
        "MainWindowActions.export_project_json": {"app_context.session": 1},
        "MainWindowActions.export_translation_text": {"app_context.session": 1},
        "MainWindowActions.paste_annotation": {"app_context.session": 1},
    },
    "oeapp/ui/notes_panel.py": {
        "NotesPanel._on_note_saved": {"app_context.session": 1},
        "NotesPanel.update_notes": {"app_context.session": 1},
    },
    "oeapp/ui/oe_text_edit.py": {
        "OldEnglishTextEdit.render_readonly_text": {"get_runtime_session": 1},
    },
    "oeapp/ui/project_workspace.py": {
        "ProjectUI._can_reload_current_project": {"app_context.session": 1},
        "ProjectUI._on_annotation_applied": {"app_context.session": 1},
    },
    "oeapp/ui/sentence_card_controller.py": {
        "SentenceCardController.on_save_oe_clicked": {"get_runtime_session": 1},
    },
}


def scan_runtime_session_lookups(
    oeapp: Path,
) -> dict[str, dict[str, dict[str, int]]]:
    """
    Count lookup kinds for every function under oeapp.

    Args:
        oeapp: Package directory to scan.

    Returns:
        Repo-relative paths mapped to enclosing functions and kind counts.

    """
    found: dict[str, dict[str, dict[str, int]]] = {}
    for path in sorted(oeapp.rglob("*.py")):
        counts = count_runtime_session_lookups(path.read_text(encoding="utf-8"))
        if not counts:
            continue
        relative = Path("oeapp") / path.relative_to(oeapp)
        found[relative.as_posix()] = counts
    return found


def test_oeapp_lookups_match_the_allowlist() -> None:
    root = Path(__file__).resolve().parents[1]
    found = scan_runtime_session_lookups(root / "oeapp")
    assert found == ALLOWLIST

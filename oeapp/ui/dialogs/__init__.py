"""Dialog module with lazy imports to avoid import-time side effects."""

import importlib

__all__ = [
    "AnnotationModal",
    "AnnotationPresetManagementDialog",
    "AppendTextDialog",
    "BackupsViewDialog",
    "CaseFilterDialog",
    "DeleteProjectDialog",
    "HelpDialog",
    "ImportProjectDialog",
    "MigrationFailureDialog",
    "NewProjectDialog",
    "NoteDialog",
    "OpenProjectDialog",
    "POSFilterDialog",
    "RestoreDialog",
    "SettingsDialog",
]

# Lazy import mapping: name -> (module_path, class_name)
_LAZY_IMPORTS = {
    "AnnotationModal": (".annotation_modal", "AnnotationModal"),
    "AnnotationPresetManagementDialog": (
        ".annotation_preset_management",
        "AnnotationPresetManagementDialog",
    ),
    "AppendTextDialog": (".append_text", "AppendTextDialog"),
    "BackupsViewDialog": (".backups_view", "BackupsViewDialog"),
    "CaseFilterDialog": (".case_filter", "CaseFilterDialog"),
    "DeleteProjectDialog": (".delete_project", "DeleteProjectDialog"),
    "HelpDialog": (".help_dialog", "HelpDialog"),
    "ImportProjectDialog": (".import_project", "ImportProjectDialog"),
    "MigrationFailureDialog": (".migration_failure", "MigrationFailureDialog"),
    "NewProjectDialog": (".new_project", "NewProjectDialog"),
    "NoteDialog": (".note_dialog", "NoteDialog"),
    "OpenProjectDialog": (".open_project", "OpenProjectDialog"),
    "POSFilterDialog": (".pos_filter", "POSFilterDialog"),
    "RestoreDialog": (".restore", "RestoreDialog"),
    "SettingsDialog": (".settings", "SettingsDialog"),
}


def __getattr__(name: str):
    """Lazy import for dialog classes."""
    if name in _LAZY_IMPORTS:
        module_path, class_name = _LAZY_IMPORTS[name]
        # Convert relative import to absolute
        # module_path is like ".annotation_preset_management"
        # We need "oeapp.ui.dialogs.annotation_preset_management"
        if module_path.startswith("."):
            # Get the current package name
            current_package = __name__
            # Remove the leading dot and construct full path
            relative_name = module_path[1:]  # Remove leading dot
            full_module_path = f"{current_package}.{relative_name}"
        else:
            full_module_path = module_path
        module = importlib.import_module(full_module_path)
        return getattr(module, class_name)
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)

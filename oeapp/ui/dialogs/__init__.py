"""Dialog module with lazy imports to avoid import-time side effects."""

from .annotation_modal import AnnotationModal
from .annotation_preset_management import AnnotationPresetManagementDialog
from .append_text import AppendTextDialog
from .backups_view import BackupsViewDialog
from .delete_project import DeleteProjectDialog
from .edit_project import EditProjectDialog
from .help_dialog import HelpDialog
from .import_project import ImportProjectDialog
from .migration_failure import MigrationFailureDialog
from .new_project import NewProjectDialog
from .note_dialog import NoteDialog
from .open_project import OpenProjectDialog
from .restore import RestoreDialog
from .sentence_filters import (
    CaseFilterDialog,
    NumberFilterDialog,
    PartOfSpeechFilterDialog,
    SentenceFilterDialog,
)
from .settings import SettingsDialog

__all__ = [
    "AnnotationModal",
    "AnnotationPresetManagementDialog",
    "AppendTextDialog",
    "BackupsViewDialog",
    "CaseFilterDialog",
    "DeleteProjectDialog",
    "EditProjectDialog",
    "HelpDialog",
    "ImportProjectDialog",
    "MigrationFailureDialog",
    "NewProjectDialog",
    "NoteDialog",
    "NumberFilterDialog",
    "OpenProjectDialog",
    "PartOfSpeechFilterDialog",
    "RestoreDialog",
    "SentenceFilterDialog",
    "SettingsDialog",
]

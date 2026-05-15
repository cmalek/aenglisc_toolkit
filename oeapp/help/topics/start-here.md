# Start Here

## What This App Is

Ænglisc Toolkit is a desktop applications intended to aid in translation of Old English/Anglo-Saxon text into idiomatic modern English (or your own language if it is not English).  All translation and word annotation is manual, and is done by the translator: Ænglisc Toolkit does not automatically translate or annotate Old English text.  The app is designed to help you keep translation and annotation work organized while you make the linguistic decisions.

Think of it as an efficiency scaffold for the translator: it provides structure, navigation, editing, and organization tools so human translation and annotation work can be done more efficiently.

## What This App Is Not

- It is not an automatic translator.
- It does not automatically assign morphological annotations for you.
- It does not disambiguate grammar or meaning for you.

## Typical Workflow

1. Create a new project or open an existing project.
2. Add or import Old English text and review sentence structure.
3. Annotate tokens and idioms.
4. Add notes and refine paragraph/section/chapter structure.
5. Review highlights, navigation, and translation text.
6. Export to DOCX, PDF or JSON.

## Main Interface Areas

- **Sentence cards**: Work area for OE text, Modern English translation, note actions, and sentence-level structure actions.
- **Token table**: Row-by-row token view for annotation details.
- **Details sidebar**: Focused view of selected token or idiom annotation data.
- **Chapter/Section toolbar**: Navigate project hierarchy at the top of the main window.
- **Menus**: Project lifecycle, import/export, presets, backups, and Help Center.

## Data Safety Model

- Project data is stored locally in SQLite.
- Automatic and manual backups are available.
- JSON export/import is available for transfer and backup workflows.
- DOCX and PDF export are available for presentation and review output.

## Undo Model (Important)

- **Undo available** for sentence edits, annotation changes, note add/edit/delete, sentence add/delete/merge, and paragraph/section/chapter split/merge actions.
- **Undo not available** for project-level destructive actions like deleting a project.
- For operations that are not undoable, use backups and JSON export as safety steps.

## All Topics

- [Settings](settings.html)
- [Keyboard Shortcuts](keybindings.html)
- [Annotation Guide](annotation-guide.html)
- [Remembered Annotations](remembered-annotations.html)
- [Idioms Guide](idioms-guide.html)
- [Incremental Annotation](incremental-annotation.html)
- [Notes Guide](notes-guide.html)
- [Search Guide](search-guide.html)
- [Full Translation Window](full-translation-window.html)
- [Export Formatting](export-formatting.html)
- [Project Export/Import](project-export-import.html)
- [Automatic Backups](automatic-backups.html)
- [Morphological Reference](morphological-reference.html)
- [Troubleshooting](troubleshooting.html)

# Graph Report - aenglisc_toolkit  (2026-10-01)

## Corpus Check
- Large corpus: 279 files · ~847,786 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 5384 nodes · 10229 edges · 308 communities (195 shown, 90 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 510 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Annotation Text Formatting
- Token Occurrence & Migrations
- Annotation Table Widget
- ORM Base & Commands
- Annotation Modal Form
- POS Form Fields
- Note Commands
- Merge Section/Chapter Commands
- DOCX Exporter
- Preset Management Dialog
- Append/Delete Project Dialogs
- Database Engine & Session
- Sentence Add/Delete Operations
- Annotation Preset Model
- Remembered Annotations
- Migration Creation
- Help Center Dialog
- Sentence Card Controller
- Text Ingestion & Sections
- Full Translation Window
- Case Highlighters
- Domain Exceptions
- MainWindow Actions
- Token Diff & Update
- AppContext
- MainWindow UI
- Sentence Filter Dialogs
- Backup & Migration Tests
- Annotation Lookup
- Sentence Splitter
- Note Dialog
- Migration Services
- MainWindow Tests
- Project Model & Edit
- Command Pattern Base
- Napoleon Doc Gate
- Project UI
- Preset JSON & Tests
- Project Model Tests
- Project JSON Exporter
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 139
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151
- Community 152
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198
- Community 199
- Community 200
- Community 222
- Community 223
- Community 224
- Community 225
- Community 226
- Community 227
- Community 228
- Community 229
- Community 230
- Community 231
- Community 232
- Community 233
- Community 234
- Community 235
- Community 236
- Community 237
- Community 238
- Community 239
- Community 240
- Community 241
- Community 242
- Community 243
- Community 244
- Community 245
- Community 246
- Community 247
- Community 248
- Community 249
- Community 250
- Community 251
- Community 252
- Community 253
- Community 254
- Community 255
- Community 256
- Community 257
- Community 258
- Community 259
- Community 260
- Community 261
- Community 262
- Community 263
- Community 264
- Community 265
- Community 266
- Community 267
- Community 268
- Community 269
- Community 270
- Community 271
- Community 272
- Community 273
- Community 274
- Community 275
- Community 276
- Community 277
- Community 278
- Community 279
- Community 280
- Community 281
- Community 282
- Community 283
- Community 284
- Community 285
- Community 286
- Community 287
- Community 288
- Community 289
- Community 290
- Community 291
- Community 292
- Community 293
- Community 294
- Community 295
- Community 296
- Community 297
- Community 298
- Community 299
- Community 300
- Community 301
- Community 302
- Community 303
- Community 306
- Community 307

## God Nodes (most connected - your core abstractions)
1. `create_test_project()` - 291 edges
2. `Project` - 169 edges
3. `SentenceCard` - 160 edges
4. `Token` - 143 edges
5. `Annotation` - 130 edges
6. `create_test_sentence()` - 114 edges
7. `Sentence` - 102 edges
8. `MainWindow` - 93 edges
9. `Chapter` - 84 edges
10. `Section` - 82 edges

## Surprising Connections (you probably didn't know these)
- `Bundled Tectonic Assets README` --semantically_similar_to--> `Bundled Tectonic PDF Engine Assets`  [INFERRED] [semantically similar]
  assets/tectonic/README.md → PACKAGING.md
- `db_session()` --uses--> `Base`  [INFERRED]
  tests/conftest.py → oeapp/db.py
- `TestFreshSchemaIndexes` --uses--> `Base`  [INFERRED]
  tests/test_db_indexes.py → oeapp/db.py
- `TestBase` --uses--> `Base`  [INFERRED]
  tests/test_db.py → oeapp/db.py
- `temp_db_engine()` --uses--> `Base`  [INFERRED]
  tests/test_migration_backup_restore.py → oeapp/db.py

## Import Cycles
- 3-file cycle: `oeapp/ui/main_window.py -> oeapp/ui/sentence_card.py -> oeapp/ui/token_table.py -> oeapp/ui/main_window.py`
- 3-file cycle: `oeapp/state.py -> oeapp/ui/main_window.py -> oeapp/ui/search_controller.py -> oeapp/state.py`
- 3-file cycle: `oeapp/ui/dialogs/annotation_modal.py -> oeapp/ui/main_window.py -> oeapp/ui/shortcuts.py -> oeapp/ui/dialogs/annotation_modal.py`
- 3-file cycle: `oeapp/ui/full_translation_window.py -> oeapp/ui/main_window.py -> oeapp/ui/menus.py -> oeapp/ui/full_translation_window.py`
- 4-file cycle: `oeapp/ui/main_window.py -> oeapp/ui/project_workspace.py -> oeapp/ui/sentence_card.py -> oeapp/ui/token_table.py -> oeapp/ui/main_window.py`
- 4-file cycle: `oeapp/ui/main_window.py -> oeapp/ui/search_controller.py -> oeapp/ui/sentence_card.py -> oeapp/ui/token_table.py -> oeapp/ui/main_window.py`
- 4-file cycle: `oeapp/ui/full_translation_window.py -> oeapp/ui/oe_text_edit.py -> oeapp/ui/main_window.py -> oeapp/ui/menus.py -> oeapp/ui/full_translation_window.py`
- 4-file cycle: `oeapp/ui/full_translation_window.py -> oeapp/ui/highlighting.py -> oeapp/ui/main_window.py -> oeapp/ui/menus.py -> oeapp/ui/full_translation_window.py`
- 5-file cycle: `oeapp/ui/full_translation_window.py -> oeapp/ui/oe_text_edit.py -> oeapp/ui/highlighting.py -> oeapp/ui/main_window.py -> oeapp/ui/menus.py -> oeapp/ui/full_translation_window.py`

## Hyperedges (group relationships)
- **Tectonic asset preparation, verification, and bundling** — packaging_tectonic_assets, packaging_prepare_tectonic_assets, packaging_verify_tectonic_assets, assets_tectonic_readme [EXTRACTED 1.00]
- **Controllers extracted from main window** — plan_pyside6_refactor_main_window, plan_pyside6_refactor_project_workspace, plan_pyside6_refactor_search_controller, plan_pyside6_refactor_sentence_card_controller [INFERRED 0.75]
- **Consumers of shared text_flow helpers** — plan_pyside6_refactor_text_flow, plan_pyside6_refactor_export_pdf, plan_pyside6_refactor_full_translation_window, plan_export_reading_text_exporter [INFERRED 0.85]
- **Annotation workflow help topics** — oeapp_help_topics_annotation_guide, oeapp_help_topics_incremental_annotation, oeapp_help_topics_idioms_guide, oeapp_help_topics_remembered_annotations, oeapp_help_topics_morphological_reference [INFERRED 0.85]
- **Project export formats (DOCX, PDF, JSON)** — oeapp_help_topics_export_formatting_docx_export, oeapp_help_topics_export_formatting_pdf_export, oeapp_help_topics_project_export_import_json_export [EXTRACTED 1.00]
- **Scholar and goblin reading a book in a library** — assets_logo_scholar_figure, assets_logo_goblin_figure, assets_logo_open_book, assets_logo_library_setting [EXTRACTED 1.00]
- **Annotation workflow docs** — oeapp_help_assets_annotation_guide, oeapp_help_assets_idioms_guide, oeapp_help_assets_incremental_annotation, oeapp_help_assets_remembered_annotations [INFERRED 0.85]
- **Export and backup docs** — oeapp_help_assets_export_formatting, oeapp_help_assets_project_export_import, oeapp_help_assets_automatic_backups [INFERRED 0.75]

## Communities (308 total, 90 thin omitted)

### Community 0 - "Annotation Text Formatting"
Cohesion: 0.03
Nodes (94): AnnotationTextualMixin, Format part of speech abbreviation for display. This is the bit that comes as a…, Format gender abbreviation for display. This is the bit that comes as a…, Format context abbreviation for display. This is the bit tha comes as a…, Mixin for annotation textual representation., Get an annotation by ID., Create an annotation from JSON import data. Args: token_id: Token ID ann_data:…, Create a token and annotation from JSON import data. Args: sentence_id:… (+86 more)

### Community 1 - "Token Occurrence & Migrations"
Cohesion: 0.03
Nodes (84): Mixin for finding token occurrences in text., Find the occurrence position of a token's surface text in the sentence. Uses…, TokenOccurrenceMixin, Run migrations in 'offline' mode. This configures the context with just a URL…, Run migrations in 'online' mode. In this scenario we need to create an Engine…, run_migrations_offline(), run_migrations_online(), Annotation (+76 more)

### Community 2 - "Annotation Table Widget"
Cohesion: 0.02
Nodes (76): AnnotationTableWidget, Any, Orientation, QAbstractTableModel, QModelIndex, QPersistentModelIndex, Return number of token rows. Args: parent: Parent model index. Returns: Token…, Return number of display columns. Args: parent: Parent model index. Returns:… (+68 more)

### Community 3 - "ORM Base & Commands"
Cohesion: 0.06
Nodes (69): DeclarativeBase, Hierarchy related commands for Sections and Chapters., Paragraph related commands., Base, Base class for all SQLAlchemy models., Chapter, Represents a chapter within a project., Data models for Ænglisc Toolkit. (+61 more)

### Community 4 - "Annotation Modal Form"
Cohesion: 0.03
Nodes (53): Read the current modal widget values into form state. Args: modal: Annotation…, AnnotationModal, QDialog, QVBoxLayout, Get the title text for the dialog., Set up the UI layout. - Sets the window title adn window flags - Builds the…, Set up the header area with token/idiom info. This is where…, Set up the token header. Args: layout: Layout to add the header to (+45 more)

### Community 5 - "POS Form Fields"
Cohesion: 0.03
Nodes (58): AdjectiveFields, AdverbFields, ArticleFields, ConjunctionFields, InterjectionFields, NoneFields, NounFields, NumberFields (+50 more)

### Community 6 - "Note Commands"
Cohesion: 0.03
Nodes (50): AddNoteCommand, Command for adding a note., Undo note creation. Returns: True if successful, False otherwise, Get command description. Returns: Description string, Undo delete operation. CRITICAL: Uses two-phase approach to handle unique…, Note, Create a note from JSON import data. Args: sentence_id: Sentence ID to attach…, Represents a note attached to tokens, spans, or sentences. (+42 more)

### Community 7 - "Merge Section/Chapter Commands"
Cohesion: 0.04
Nodes (43): MergeChapterCommand, MergeSectionCommand, Undo split section operation. This means: - Move all paragraphs back to the…, Command for merging a section with the previous one., Command for splitting a section at a specific paragraph., Execute merge section operation. This means: - Move all paragraphs from the…, Command for splitting a chapter at a specific section., Execute split section operation. This means: - Create a new section after the… (+35 more)

### Community 8 - "DOCX Exporter"
Cohesion: 0.04
Nodes (38): DOCXExporter, Add a manual endnote entry with a bookmark anchor. Args: doc: The document to…, Add a page number field to a run. Args: run: The run to add the page number to, Return ``True`` when sentence is first in its paragraph. Args: sentence:…, Resolve chapter/section titles that should be rendered at this boundary. Args:…, Export project to DOCX file. Args: project_id: Project ID to export…, Exports annotated Old English text to DOCX format., Export project to DOCX file in side-by-side landscape format. Args: project_id:… (+30 more)

### Community 9 - "Preset Management Dialog"
Cohesion: 0.05
Nodes (40): Get a preset by ID. Args: session: SQLAlchemy session preset_id: Preset ID…, AnnotationPresetManagementDialog, QComboBox, QDialog, QFormLayout, QVBoxLayout, QWidget, Set up save mode (single POS form, no tabs). Side Effects: - Creates the name… (+32 more)

### Community 10 - "Append/Delete Project Dialogs"
Cohesion: 0.05
Nodes (39): Append OE text dialog., DeleteProjectDialog, Filter the project table based on search text. Args: search_text: Text to…, Handle selection change to enable/disable buttons., Get the currently selected project. Returns: Selected Project or None if no…, Export the selected project and then delete it., Delete the selected project. Args: project: Project to delete. If None, gets…, Add the button box to the dialog with three buttons. (+31 more)

### Community 11 - "Database Engine & Session"
Cohesion: 0.04
Nodes (50): create_engine_with_path(), get_project_db_path(), get_session(), _parse_env_choice(), _parse_env_int(), Engine, Path, SQLAlchemy database setup for Ænglisc Toolkit. (+42 more)

### Community 12 - "Sentence Add/Delete Operations"
Cohesion: 0.04
Nodes (34): Execute add sentence operation. CRITICAL: Uses two-phase approach to handle…, Execute delete operation. Returns: True if successful, False otherwise, Get the next sentence by project ID and display order. Args: project_id:…, Import an entire OE text into a project. The text is split into sentences and…, Get the subsequent sentences by project ID and display order. Args: session:…, Update display_order for multiple sentences using two-phase approach. This…, Restore display_order values using two-phase approach. This method safely…, Recalculate paragraph order for all paragraphs in a project. (+26 more)

### Community 13 - "Annotation Preset Model"
Cohesion: 0.05
Nodes (37): AnnotationPreset, Annotation preset model., Create a new preset. Args: name: Preset name pos: Part of speech (N, V, A, R,…, Serialize preset to dictionary with all field values. Returns: Dictionary…, Represents a user-defined preset for annotation fields., AnnotationPresetService, Service for handling annotation presets., Apply preset values to annotation object (only sets non-None values). Args:… (+29 more)

### Community 14 - "Remembered Annotations"
Cohesion: 0.05
Nodes (38): Any, validates, Get a remembered annotation by ID., Get a remembered annotation for one exact token/scope pair., List remembered annotations for one explicit scope., Resolve project-visible remembered entries with project scope winning., Upsert a remembered entry from a live token annotation., Upsert a remembered entry from sanitized field data. (+30 more)

### Community 15 - "Migration Creation"
Cohesion: 0.05
Nodes (38): main(), MigrationCreationFailed, Exception raised when a migration creation fails., Initialize exporter. Args: migration_service: Optional MigrationService…, FieldMappingService, MigrationResult, MigrationService, Config (+30 more)

### Community 16 - "Help Center Dialog"
Cohesion: 0.05
Nodes (36): HelpCenterDialog, HelpTextBrowser, Any, QDialog, QUrl, QWidget, QtHelp-based Help Center dialog., Construct dialog widgets/layout. - Sets the window title, minimum size, and… (+28 more)

### Community 17 - "Sentence Card Controller"
Cohesion: 0.03
Nodes (32): Get the current sentence cards from the main window. Returns: Sentence cards…, Initialize controller for a sentence card. Args: card: Sentence card widget…, QWidget, Event handler for idiom selection., Event handler for range selection. Args: start_order: Start order index of the…, Event handler for single token selection. Args: token: Token that was selected, Handle Save OE button click - save changes and exit edit mode., Handle "Cancel Edit" button click - discard changes and exit edit mode. (+24 more)

### Community 18 - "Text Ingestion & Sections"
Cohesion: 0.06
Nodes (39): Create a new section. Args: chapter_id: The chapter ID number: The section…, CanonicalRun, OldEnglishText, Path, Append ingested content into an existing project. Args: project: Existing…, Build lightweight ingestion metadata. Args: title: Text title. source: Source…, Ingest text into wyrdcraeft canonical models. Args: text: Raw pasted text.…, Map canonical content into app hierarchy models. Args: project: Target project.… (+31 more)

### Community 19 - "Full Translation Window"
Cohesion: 0.05
Nodes (29): FullProjectNoteWidget, FullTranslationWindow, QMainWindow, QWidget, Build the content: OE and ModE columns., Build the modern english edit., Build the notes area., Deselect all notes in the UI and clear highlights. (+21 more)

### Community 20 - "Case Highlighters"
Cohesion: 0.04
Nodes (30): CaseHighlighterCommand, NoneHighlighterCommand, Highlighter for no highlighting. This is the default highlighting mode., Highlighter for highlighting cases in the Old English text edit., Get the value of the case for the token. We only highlight articles (D), nouns…, fixture, Test that filter selections are saved when switching modes., Test that highlight() actually applies extra selections to the text edit. (+22 more)

### Community 21 - "Domain Exceptions"
Cohesion: 0.06
Nodes (35): AlreadyExists, BackupFailed, DoesNotExist, MigrationFailed, MigrationSkipped, Exception, Exception raised when a resource already exists., Exception raised when a migration fails. (+27 more)

### Community 22 - "MainWindow Actions"
Cohesion: 0.04
Nodes (29): MainWindowActions, Remember one token annotation into global or project scope. Args: token: Token…, Apply remembered annotations across the current project., Open the project-scoped remembered annotation management dialog., Delete a project from the database. Creates a backup before deletion and opens…, Export project to DOCX., Create a backup immediately. - Create a backup - Show a message in the status…, Main window actions. We separate the work from the UI to make the code more… (+21 more)

### Community 23 - "Token Diff & Update"
Cohesion: 0.05
Nodes (29): Check if an annotation exists for a token or idiom., Session, Update tokens in the sentence and re-order them. Args: sentence_text: Text of…, Move tokens to temporary negative positions. We do this because we have a…, Process a single difflib opcode., Handle 'replace' opcode. This means: - The number of old tokens is equal to the…, Create a new token and its empty annotation., Delete tokens that were not matched. (+21 more)

### Community 24 - "AppContext"
Cohesion: 0.05
Nodes (27): AppContext, QObject, Stable application-wide Qt context. `AppContext` owns only app-lifetime…, Report whether an active project is set. Returns: ``True`` when an active…, Show an error message. Args: message: Message to show. Keyword Args: title:…, Show a warning message. Args: message: Message to show. Keyword Args: title:…, Show an informational message. Args: message: Message to show. Keyword Args:…, Initialize the app context. Keyword Args: session: Optional SQLAlchemy session… (+19 more)

### Community 25 - "MainWindow UI"
Cohesion: 0.04
Nodes (26): Register the main window with the context. Args: main_window: Main window bound…, MainWindow, QMainWindow, Handle search text change., Handle search scope change., Handle clear search button click., Clear search state without restoring origin focus., Handle previous chapter button click. (+18 more)

### Community 26 - "Sentence Filter Dialogs"
Cohesion: 0.06
Nodes (29): CaseFilterDialog, NumberFilterDialog, PartOfSpeechFilterDialog, QDialog, Handle checkbox state change and emit signal., Select all case checkboxes., Deselect all case checkboxes., Get the currently selected items. Returns: Set of selected item codes (+21 more)

### Community 27 - "Backup & Migration Tests"
Cohesion: 0.04
Nodes (26): fixture, Test get_last_backup_time() returns stored timestamp., Test set_last_backup_time() stores timestamp., Test should_backup() returns True when no previous backup., Test should_backup() returns False when within interval., Test should_backup() returns True when interval has passed., Test get_current_migration_version() returns None when no alembic_version table., Test create_backup() raises BackupFailed when database doesn't exist. (+18 more)

### Community 28 - "Annotation Lookup"
Cohesion: 0.05
Nodes (25): Get the current annotation. IF :attr:`token_id` is not None, get the annotation…, Get an annotation by token ID., Get an annotation by idiom ID., Extract morphological state from an annotation object. Args: annotation:…, Execute the annotate command via command manager. This will handle the actual…, Update local caches and UI after annotation is applied. Args: annotation:…, Save annotation to database. Args: annotation: Annotation to save, Get the current state of an annotation before updates. Args: annotation:… (+17 more)

### Community 29 - "Sentence Splitter"
Cohesion: 0.06
Nodes (25): Split text into sentences and detect paragraph breaks. Args: text: Input Old…, Check if there are blank lines (two or more consecutive newlines) between…, Test quoted text followed by another sentence., Test text with single quotes., Test splitting a simple sentence., Test punctuation followed immediately by uppercase letter., Test punctuation followed by space and uppercase letter., Test that lowercase after punctuation doesn't split. (+17 more)

### Community 30 - "Note Dialog"
Cohesion: 0.06
Nodes (30): NoteDialog, QDialog, QWidget, Note dialog for adding/editing notes., Get the text representation of the selected token range. Returns: String…, Dialog for adding or editing notes. Args: sentence: Sentence the note belongs…, Initialize note dialog., Set up the UI layout. (+22 more)

### Community 31 - "Migration Services"
Cohesion: 0.05
Nodes (31): Initialize processor. Args: migration_service: Optional MigrationService…, Services package initialization., MigrationCreationResult, MigrationMetadataService, Service for handling database migrations., Get the minimum app version required for a given migration version. Args:…, Update migration_versions.json with new migration. Ensures only one migration…, Service for handling migration files. (+23 more)

### Community 32 - "MainWindow Tests"
Cohesion: 0.05
Nodes (30): patch, main_window(), mock_services(), fixture, Unit tests for MainWindow., Test that copy_annotation updates AppContext copied annotation., Test that paste_annotation uses copied app-context state., Fixture to mock MigrationService and BackupService. (+22 more)

### Community 33 - "Project Model & Edit"
Cohesion: 0.05
Nodes (22): Get a project by name. Args: project_id: Project ID Returns: Project or None if…, Sanitize filename. Args: filename: Filename to sanitize Returns: Sanitized…, Append text to the current project., EditProjectDialog, Edit project dialog. This gets opened when the user clicks the "Edit…, Initialize edit project dialog., Build the edit project dialog., Save project changes. This means: - Check if the title is empty - Check if the… (+14 more)

### Community 34 - "Command Pattern Base"
Cohesion: 0.08
Nodes (30): ABC, Command, Command pattern for undo/redo functionality., Base class for undoable commands., Execute a command and add to undo stack. Args: command: Command to execute…, AnnotateTokenCommand, ApplyRememberedAnnotationsCommand, Annotation related commands. (+22 more)

### Community 35 - "Napoleon Doc Gate"
Cohesion: 0.08
Nodes (42): AsyncFunctionDef, _check_file(), _check_function_doc(), _constructor_has_args(), _first_doc_line(), _function_has_args(), _function_has_keyword_args(), _function_uses_return_or_yield() (+34 more)

### Community 36 - "Project UI"
Cohesion: 0.07
Nodes (23): ProjectUI, Update section dropdown for the given chapter. Args: chapter_id: Chapter whose…, Load sentences for the given section. Args: section_id: Section whose sentences…, Store the workspace-local selected sentence card. Args: sentence_card: Sentence…, Clear the workspace-local selected sentence card., Build out the UI for a particular project inside the main window. Important:…, Clear existing content from the layout., Add a paragraph separator to the layout. (+15 more)

### Community 37 - "Preset JSON & Tests"
Cohesion: 0.05
Nodes (22): Update a preset. Args: preset_id: Preset ID Keyword Args: commit: Whether to…, Create preset from JSON import data. Args: preset_data: Preset data dictionary…, Test cases for AnnotationPreset model., Test update() class method., Test update() returns None for nonexistent preset., Test delete() class method., Test model creation with all fields., Test to_dict() method. (+14 more)

### Community 38 - "Project Model Tests"
Cohesion: 0.05
Nodes (20): Test create() raises AlreadyExists for duplicate name., Test create() uses default name when not provided., Test total_token_count() returns total tokens in project., Test total_token_count() returns 0 for project with no sentences., Test deleting project removes it., Test append_oe_text() appends sentences to project., Test cases for Project model., Test append_oe_text() works on project with no sentences. (+12 more)

### Community 39 - "Project JSON Exporter"
Cohesion: 0.07
Nodes (27): ProjectExporter, Exports projects to JSON format., Get project by ID. Args: project_id: Project ID Returns: Project, Export project as JSON to a file. Args: project_id: Project ID to export…, _assert_no_row_ids(), _build_full_project(), _legacy_verbose_export_size(), Test cases for ProjectExporter. (+19 more)

### Community 40 - "Community 40"
Cohesion: 0.07
Nodes (25): BackupsViewDialog, Add the button box to the dialog., Execute the backups view dialog., Dialog to view backup information., Initialize backups view dialog., Build the backups view dialog., Load the list of available backups., Update the project list in the table widget by loading projects from the… (+17 more)

### Community 41 - "Community 41"
Cohesion: 0.09
Nodes (24): MergeParagraphCommand, Command for merging a paragraph with the previous one., Command for splitting a paragraph at a specific sentence., Execute merge paragraph operation., Undo merge paragraph operation., Execute split paragraph operation., Undo split paragraph operation., SplitParagraphCommand (+16 more)

### Community 42 - "Community 42"
Cohesion: 0.07
Nodes (23): BackupService, Any, datetime, Engine, QObject, Get the current migration version from the database. Args: engine: SQLAlchemy…, Extract metadata from the database for backup. Args: session: SQLAlchemy…, Create a backup of the database immediately. Returns: Path to the created… (+15 more)

### Community 43 - "Community 43"
Cohesion: 0.06
Nodes (21): Get all presets for a POS, ordered by name. Args: session: SQLAlchemy session…, _field(), Test form validation checks for duplicate names., Test that empty is first and 'Clear' is second in combo boxes., Test that selecting empty extracts as None and 'Clear' extracts as…, Test cases for AnnotationPresetManagementDialog., Test that setting None value sets combo to empty (index 0), not 'Clear' (index…, Test saving a preset with 'Clear' selected for some fields. (+13 more)

### Community 44 - "Community 44"
Cohesion: 0.08
Nodes (20): Create new tokens for a sentence. Args: sentence_id: Sentence ID sentence_text:…, Test cases for Token.create_from_sentence., Test creating tokens from a simple sentence., Test creating tokens with punctuation., Test creating tokens from an empty sentence., Test creating a single token., Test that tokens are created with sequential order indices., Test that all created tokens have database IDs. (+12 more)

### Community 45 - "Community 45"
Cohesion: 0.07
Nodes (22): FullProjectOldEnglishTextEdit, FullProjectTextSelector, KeyboardModifier, QMouseEvent, QPoint, QTextCursor, Connect signals to the sidebar., Insert text while indenting verse lines by four spaces. Args: cursor: Target… (+14 more)

### Community 46 - "Community 46"
Cohesion: 0.07
Nodes (21): QComboBox, Create a spin box for a settings key that has an integer value. Args: label:…, Add the button box to the dialog. The button box will be used to accept or…, Create a combo box for a settings key that has a string value. Args: label:…, Save settings to QSettings., Handle theme change by opening a confirmation dialog that tells the user that…, Execute the settings dialog., Get the ``qt_themes`` theme name. (+13 more)

### Community 47 - "Community 47"
Cohesion: 0.08
Nodes (19): Initialize main window actions. Args: main_window: Main window instance.…, Navigate to the previous matching search result., Focus the first match in search results., Clear search state, highlights, and optionally restore origin focus. Keyword…, Load current project matches via fat-ORM search helpers. Args: pattern: Raw…, Update search UI elements based on search results. Args: total_matches: Total…, Focus the current search result and update the search counter., Reset in-memory search results and counters. (+11 more)

### Community 48 - "Community 48"
Cohesion: 0.07
Nodes (21): HelpEngine, QUrl, Return the `qthelp://` URL for a named topic (or default home page)., Return the `qthelp://` URL for a relative page path., Return the contents tree widget., Return the keyword index widget., Return the search-query input widget., Return the search results widget. (+13 more)

### Community 49 - "Community 49"
Cohesion: 0.06
Nodes (24): Create a new project. Args: text: Old English text to process and add to the…, full_window(), fixture, Test the window with a project that has no notes., Fixture to create a FullTranslationWindow instance., Test that source/translator metadata appears in the banner, but notes do not., Notes-only projects should not render a body banner., Show notes should open a non-modal dialog with project notes text. (+16 more)

### Community 50 - "Community 50"
Cohesion: 0.10
Nodes (24): Enum, is_paragraph_start(), latex_separator(), plain_text_separator(), Shared domain rules for full-text rendering flow across UI and export., Decide semantic separator between ``previous`` and ``current``. Args: previous:…, Semantic separator between adjacent rendered sentences. Format layers map each…, Map separator kind to plain-text gap for UI rendering. Args: kind: Semantic… (+16 more)

### Community 51 - "Community 51"
Cohesion: 0.06
Nodes (6): fixture, Test cases for PartOfSpeechFormManager., Switching verb class to pp should auto-set requires infinitive., Test cases for PartOfSpeechFieldsBase., TestPartOfSpeechFieldsBase, TestPartOfSpeechFormManager

### Community 52 - "Community 52"
Cohesion: 0.09
Nodes (17): OldEnglishTextSelector, KeyboardModifier, Get the current selected token index., Set the selected token index. - Stop the deselection timer - Set the selected…, Reset the selected token index and range. - Stop the deselection timer - Set…, Handle click on Old English text to select corresponding token. Args: position:…, Handle Cmd/Ctrl+Click for idiom selection. This will start a new idiom…, Handle Shift+Click for range selection for Note creation and management. This… (+9 more)

### Community 53 - "Community 53"
Cohesion: 0.08
Nodes (25): MockMainWindow, _MockProjectUI, QWidget, Mock main window that inherits from QWidget., Minimal workspace selection holder for tests., Return selected sentence card for action tests., Store selected sentence card for action tests., Clear the selected sentence card. (+17 more)

### Community 54 - "Community 54"
Cohesion: 0.07
Nodes (16): Same lowercase form should keep distinct morphology codes for N/A/R., Attested forms should include italicized sense only when present., Conjunction entries omit classification and bracketed attested-form codes., OE rendering should preserve interior spacing and leading indentation., Sentences in the same paragraph should be rendered as one line-block per column., ModE column should use the same fixed wide-gap normalization., Unicode OE diacritics should be emitted as explicit LaTeX accents., Prepositions should be split by ``prep_case`` in glossary entries. (+8 more)

### Community 55 - "Community 55"
Cohesion: 0.10
Nodes (15): NotesPanel, QLabel, QWidget, Set up the UI layout., Show empty state for the notes panel., Show a single note. Args: note_index: Note index (1-based) note: Note to…, Clear the layout and notes., Update notes display. Note: You can't name this method "update" because it… (+7 more)

### Community 56 - "Community 56"
Cohesion: 0.09
Nodes (27): Human-Comprehensible Class Architecture Preference, Documentation Contract (Napoleon docstrings), Fat ORM Typing (builtins.list), Implementation Priority (no workarounds), Post-Implementation Quality Gate (ruff, mypy, napoleon-gate), Tooling Preflight Evidence, Project Export Reading-Text Plan, ADR 0003 Project Export Reading Text (+19 more)

### Community 57 - "Community 57"
Cohesion: 0.07
Nodes (14): Test that pressing Enter key opens the annotation modal when a token is…, Test that Enter key is NOT intercepted by SentenceCard when in edit mode., Test cases for SentenceCard., Test that Enter key does nothing if no token is selected., Test SentenceCard initializes correctly., Test that selecting a token in the table updates the card state., Test that arrow keys move the cursor instead of tokens in edit mode., Test SentenceCard has POS and case color maps. (+6 more)

### Community 58 - "Community 58"
Cohesion: 0.10
Nodes (27): Annotation Guide, Multi-token idiom, Annotation fields by part of speech, Automatic Backups, Backup file and restore, Export Formatting, DOCX export, PDF export (+19 more)

### Community 59 - "Community 59"
Cohesion: 0.13
Nodes (25): _bundle_has_required_index(), compile_latex_with_tectonic(), _normalize_platform(), PDFEngineError, CompletedProcess, Path, RuntimeError, Bundled PDF engine resolution and LaTeX compilation helpers. (+17 more)

### Community 60 - "Community 60"
Cohesion: 0.10
Nodes (15): QHBoxLayout, Display the part of speech field and its associated fields. If the annotation…, Display a horizontal rule., Display the surface form of the token. This is the word plus annotations as…, Display the line label for the given sentence. The line label is displayed on…, Display the root field and its associated dictionary icon button. Args:…, Display the root-word definition field. Args: annotation: Annotation to display, Display the contextual sense field. Args: annotation: Annotation to display (+7 more)

### Community 61 - "Community 61"
Cohesion: 0.08
Nodes (11): BoundLogger, listens_for, Update or create an annotation from an existing annotation. Args: annotation:…, Delete the annotation., Ensure non-null verb metadata defaults are always populated. This protects…, Serialize project to JSON-compatible dictionary (without PKs). Returns:…, Update Project.updated_at whenever a related entity is changed., touch_project_on_change() (+3 more)

### Community 62 - "Community 62"
Cohesion: 0.11
Nodes (16): ExtraSelection, QColor, Create an extra selection for highlighting a range of positions. Args:…, Mixin for selecting tokens in the Old English text edit., Clear all highlights., Refresh token mappings from the live text edit state., Get the token positions in the sentence for the range of tokens. A position in…, Highlighter for a a kind of highlight that can only appear once in the… (+8 more)

### Community 63 - "Community 63"
Cohesion: 0.08
Nodes (14): ProjectImporter, Processes project import data and creates database entities., Build canonical tuple key for paragraph lookup., Build map from paragraph hierarchy coordinates to paragraph IDs. Args:…, Test validation passes when versions match or no version requirement., Test validation raises if version is missing in export., Test validation raises if no revision chain found., Test validation raises with minimum app version message. (+6 more)

### Community 64 - "Community 64"
Cohesion: 0.09
Nodes (14): QComboBox, Highlighter for a sentence for the highlighting combo box., Hide the filter dialog for the active command, if any., Show the filter dialog for the active command, if any., Build the highlighting combo box for :attr:`card`. Returns: Highlighting combo…, Get the live Old English text from our sentence card., Clear all highlights in our associated sentence card's OE text edit., Clear the active command. (+6 more)

### Community 65 - "Community 65"
Cohesion: 0.11
Nodes (15): Sidebar widget displaying detailed token information in the main window., TokenDetailsSidebar, Unit tests for TokenDetailsSidebar., Test cases for TokenDetailsSidebar., Test definition and sense fields render as separate styled labels., Test TokenDetailsSidebar initializes correctly., Test that Verb Direct Object Case renders correctly., Test TokenDetailsSidebar shows empty state initially. (+7 more)

### Community 66 - "Community 66"
Cohesion: 0.11
Nodes (17): _actions(), Test cases for paste_annotation functionality., Test paste_annotation returns False when no token is selected., Test paste_annotation shows message when nothing was copied., Build action service for mock main window., Test paste_annotation applies annotation data and remains undoable., Test paste_annotation can be redone after undo., Create and select a real sentence card for token interaction tests. (+9 more)

### Community 67 - "Community 67"
Cohesion: 0.09
Nodes (16): Highlighter for search results in a QTextEdit., SearchHighlighter, OldEnglishTextEdit, QTextEdit, QWidget, If ``end_index`` is ``None``, find an idiom that covers the given…, QTextEdit that is tailored editing, navigation, and annotating Old English…, The OE text of the sentence associated with this text edit. (+8 more)

### Community 68 - "Community 68"
Cohesion: 0.09
Nodes (13): HighlighterCommandBase, NumberHighlighterCommand, Base class for highlighting tokens in the Old English text edit. This is used…, Show the filter dialog (if any) for the command., Hide the filter dialog for the command., Apply the highlighting for the command., Get the value of the annotation for the command. This is implemented by the…, Unhighlight the tokens for the command. (+5 more)

### Community 69 - "Community 69"
Cohesion: 0.09
Nodes (4): fixture, Unit tests for OldEnglishTextEdit and TokenSelector., TestOldEnglishTextEdit, TestTokenSelector

### Community 70 - "Community 70"
Cohesion: 0.09
Nodes (13): CommandManager, Undo last command. Returns: True if successful, False otherwise, Redo last undone command. Returns: True if successful, False otherwise, Check if undo is possible. Returns: True if undo is available, Check if redo is possible. Returns: True if redo is available, Clear all command stacks., Manages undo/redo command stack., Initialize command manager. Args: session: SQLAlchemy session Keyword Args:… (+5 more)

### Community 71 - "Community 71"
Cohesion: 0.11
Nodes (13): ImportProjectDialog, Dialog shown after importing a project. Args: main_window: Main window instance…, Initialize import project dialog. Args: main_window: Main window instance…, Build the import project dialog., Handle open project button click., Execute the import project dialog. Returns: True if user chose to open project,…, Import project from JSON format., Unit tests for ImportProjectDialog. (+5 more)

### Community 72 - "Community 72"
Cohesion: 0.11
Nodes (13): MigrationFailureDialog, Exception, Save stack trace to file., Copy stack trace to clipboard., Execute the migration failure dialog., Dialog shown when migration fails during startup. Args: main_window: Main…, Build the migration failure dialog., Unit tests for MigrationFailureDialog. (+5 more)

### Community 73 - "Community 73"
Cohesion: 0.13
Nodes (22): build_qhcp(), build_qhp(), first_heading(), keyword_id(), main(), parse_args(), Namespace, Path (+14 more)

### Community 74 - "Community 74"
Cohesion: 0.11
Nodes (16): clear_runtime_session(), get_runtime_session(), Session, Return the process runtime SQLAlchemy session. Keyword Args: create: Whether to…, Register the process runtime SQLAlchemy session. Args: session: Session to…, Clear the process runtime SQLAlchemy session. Keyword Args: close: Whether to…, set_runtime_session(), Session (+8 more)

### Community 75 - "Community 75"
Cohesion: 0.13
Nodes (13): QHBoxLayout, QScrollArea, QVBoxLayout, QWidget, Set up the main window., Build the search toolbar. Returns: QWidget: The search toolbar widget, Build the chapter and section navigation toolbar. Returns: QWidget: The…, Build the QApplication window. (+5 more)

### Community 76 - "Community 76"
Cohesion: 0.13
Nodes (14): FileMenu, PreferencesMenu, A "File" menu to be added to the main menu bar with the following actions: -…, A "Preferences" menu to be added to the main menu bar with the following…, Populate the preferences menu with the following actions: - Preferences... On…, Test cases for PreferencesMenu., Test PreferencesMenu creates menu., macOS preferences action should use PreferencesRole and open settings. (+6 more)

### Community 77 - "Community 77"
Cohesion: 0.13
Nodes (14): MainMenu, Main application menu., Initialize main menu. Args: main_window: Main window instance, _non_separator_action_texts(), QMenu, Test cases for HelpMenu., Test HelpMenu creates menu., Help menu should include topic actions on macOS. (+6 more)

### Community 78 - "Community 78"
Cohesion: 0.13
Nodes (12): LogLevel, LogTableModel, QAbstractTableModel, Format the log message with extra key-value pairs., Set the complete list of log lines and apply filters. Args: logs: The new list…, Add a one log line and apply filters, maintaining 1000 line limit. ``log`` is a…, Add multiple log lines and apply filters, maintaining 1000 line limit. Args:…, Set the display local time flag. This toggles the display of the timestamp from… (+4 more)

### Community 79 - "Community 79"
Cohesion: 0.10
Nodes (11): FullTranslationPDFExporter, Split and dedupe senses on semicolon/comma boundaries. Args: modern_meaning:…, Join non-empty code segments without separators. Args: *parts: The parts to…, Render concise verb tense codes without POS ambiguity. Args: tense: The tense…, Exports the full translation view as a LaTeX-driven PDF document., Score a root form for display preference. Higher values win and favor richer…, Attested forms should use short DB-code annotations., Verb glossary should render impers/intrans markers and (+ inf). (+3 more)

### Community 80 - "Community 80"
Cohesion: 0.13
Nodes (17): get_log_dir(), get_log_file_path(), Logging configuration for Ænglisc Toolkit., Get the path to the log directory. Returns: The path to the log directory., Get the path to the current log file. Returns: The path to the current log file., Log viewer dialog for Ænglisc Toolkit., get_app_data_path(), Path (+9 more)

### Community 81 - "Community 81"
Cohesion: 0.12
Nodes (12): LogViewerDialog, QDialog, Non-modal dialog for viewing application logs. Args: parent: The parent widget., Load the initial logs from the log file. This will load the last 1000 logs from…, Update the logs from the log file. This will only update the logs if the "Live"…, Write a log line to the file. Args: f: The file object. log: The log line., Handle the filter text and level changes. This will update the model with the…, Handle the "Live" toggle. This will start or stop the live update of the logs.… (+4 more)

### Community 82 - "Community 82"
Cohesion: 0.13
Nodes (11): FullProjectModernEnglishTextEdit, QTextEdit, Event handler for :attr:`show_notes_btn.clicked` signal: Open project notes in…, Emit the :attr:`clicked` signal when the note widget is clicked. Args: event:…, Modern English text edit for the full project view with sentence mapping., Render the project's translation text., Handle clicking on sentences. - Get the cursor position - Get the sentence ID…, Select and highlight a sentence. - Toggle off if already selected - Set the… (+3 more)

### Community 83 - "Community 83"
Cohesion: 0.12
Nodes (13): AddSentenceCommand, Command for adding a new sentence before or after an existing sentence., Undo add sentence operation. CRITICAL: Uses two-phase approach to handle unique…, Get command description. Returns: Description string, Add a new empty sentence before the current sentence., Add a new empty sentence after the current sentence., Execute an add-sentence command for the configured position. Keyword Args:…, Verify that adding a sentence after the first sentence of a project now… (+5 more)

### Community 84 - "Community 84"
Cohesion: 0.12
Nodes (19): Automatic Backups, Automatic database backups, Backup interval 12h, keep 5, Export Formatting, DOCX export (File menu), PDF footnotes from notes, PDF export (Full Translation window), Full Translation Window Help (+11 more)

### Community 85 - "Community 85"
Cohesion: 0.13
Nodes (11): Build the main window. - Setup the main window. - Initialize the project UI…, AnnotationModalShortcuts, GlobalShortcuts, Mixin for keyboard shortcuts., Add a keyboard shortcut to the application., Global keyboard shortcuts for the application. The following shortcuts are set…, Initialize the shortcuts., Add all the shortcuts to the main window. (+3 more)

### Community 86 - "Community 86"
Cohesion: 0.13
Nodes (11): QHBoxLayout, QLabel, QTextEdit, Add the paragraph header to the layout and return the sentence number label. -…, Add the sentence actions (menus and buttons) to the layout and return the…, Add the OE text label line to the layout. - Add "Old English:" label - Add Add…, Build the OE text edit widget. Returns: OE text edit widget, Build the translation edit widget. Returns: Tuple with the layout and the… (+3 more)

### Community 87 - "Community 87"
Cohesion: 0.15
Nodes (10): QVBoxLayout, Render the noun. This renders these fields: - Gender - Number - Case -…, Render the verb. This renders these fields: - Verb Class - Verb Tense - Verb…, Render the adjective. This renders these fields: - Degree - Inflection - Gender…, Render the pronoun. This renders these fields: - Pronoun Type - Gender - Number…, Render the article. This renders these fields: - Article Type - Gender - Number…, Render the preposition. This renders these fields: - Governed Case Args:…, Render the adverb. This renders these fields: - Adverb Degree Args:… (+2 more)

### Community 88 - "Community 88"
Cohesion: 0.13
Nodes (11): MockSentenceCard, Test _find_token_at_position with hyphenated words., Mock sentence card for testing selection logic., Test selection with multiple hyphenated words., Find the token index that contains the given character position., Test cases for sentence card selection with hyphenated words., Test clicking prefix selects entire token., Test clicking hyphen selects entire token. (+3 more)

### Community 89 - "Community 89"
Cohesion: 0.14
Nodes (18): Bundled Tectonic Assets README, Tectonic manifest.json hashes, macOS build (build_macos.sh, DMG), Windows build (build_windows.bat), QtHelp and Apple Help Book assets, Native macOS Help-menu search, Packaging Guide, scripts/prepare_tectonic_assets.py (+10 more)

### Community 90 - "Community 90"
Cohesion: 0.18
Nodes (17): BaseModel, AnnotationJson, ChapterJson, IdiomJson, NoteJson, ParagraphJson, ParagraphRefJson, ProjectExportPayload (+9 more)

### Community 91 - "Community 91"
Cohesion: 0.12
Nodes (12): BackupFileMetadataService, Any, setter, Read migration versions metadata from JSON file. Returns: Migration versions…, Write migration versions metadata to JSON file. Args: metadata: Migration…, Read field mappings from JSON file. Returns: Field mappings dictionary, or None…, Write field mappings to JSON file., Service for handling backup file metadata. This handles the metadata JSON file… (+4 more)

### Community 92 - "Community 92"
Cohesion: 0.11
Nodes (9): Build form state from an annotation or remembered annotation. Args: annotation:…, Update status label with current annotation summary. - If the POS is not set,…, Load existing annotation values into the form. If there is a POS set on the…, Signal callback for the ``currentIndexChanged`` signal on the POS combo box.…, Refresh preset dropdown from database., Signal callback for the ``clicked`` signal on the "Apply Preset" button. Apply…, Signal callback for the ``currentIndexChanged`` signal on the POS combo box.…, Signal callback for the ``clicked`` signal on the "Save as Preset" button. Open… (+1 more)

### Community 93 - "Community 93"
Cohesion: 0.11
Nodes (7): QWidget, Initialize annotation modal. Args: token: Token to annotate (exclusive with…, Initialize annotation for a single token. If we've been called, :attr:`token`…, Initialize annotation for an idiom. If we've been called, :attr:`idiom` is…, AnnotationPosFormManager, Manager for annotation-modal POS forms., QLayout

### Community 94 - "Community 94"
Cohesion: 0.14
Nodes (11): AppendTextDialog, Execute the append text dialog., Append OE text dialog. This gets opened when the user clicks the "Append OE…, Initialize append text dialog., Build the append text dialog. This means: - Setting the window title - Setting…, Add the button box to the dialog. The button box will be used to accept or…, Unit tests for AppendTextDialog., Test AppendTextDialog initializes correctly. (+3 more)

### Community 95 - "Community 95"
Cohesion: 0.14
Nodes (11): Add the button box to the dialog., Execute the restore dialog., Restore dialog for selecting a backup to restore., Initialize restore dialog., Build the restore dialog., RestoreDialog, Unit tests for RestoreDialog., Test cases for RestoreDialog. (+3 more)

### Community 96 - "Community 96"
Cohesion: 0.11
Nodes (9): Handle Split Paragraph action., Handle Merge Paragraph action., Handle Split Section action., Handle Merge Section action., Handle Split Chapter action., Handle Merge Chapter action., Execute a hierarchy command and update UI., Build the sentence/verse reference label used in card headers. Returns: The… (+1 more)

### Community 97 - "Community 97"
Cohesion: 0.11
Nodes (18): QApplication, command_setup(), disable_autosave_by_default(), mock_main_window(), mock_migration_services(), project_and_sentence(), fixture, qapp() (+10 more)

### Community 98 - "Community 98"
Cohesion: 0.21
Nodes (15): NoAnnotationAvailable, Exception raised when no annotation is available., AbstractPartOfSpeechRenderer, AdjectiveRenderer, AdverbRenderer, ArticleRenderer, ConjunctionRenderer, InterjectionRenderer (+7 more)

### Community 99 - "Community 99"
Cohesion: 0.13
Nodes (17): Annotation Guide, Annotation modal, Part of Speech annotation, Idioms Guide, Idiom (multi-word annotation unit), Incremental Annotation, Iterative annotation refinement, Help Index (redirect) (+9 more)

### Community 100 - "Community 100"
Cohesion: 0.15
Nodes (13): main(), Main entry point for Ænglisc Toolkit application., Run the Ænglisc Toolkit application., configure_logging(), Configure structlog and standard logging. - JSON logs to file with 3-week…, create_application(), Create the application., get_resource_path() (+5 more)

### Community 101 - "Community 101"
Cohesion: 0.15
Nodes (9): Any, Validate that the export migration version is compatible. Args: export_version:…, Transform data by applying field mappings if needed. Args: data: Project data…, Apply field mappings incrementally through migration chain. Args: data: Data…, Recursively apply field mappings to data structure. Args: obj: Object to…, Create project hierarchy (chapters, sections, paragraphs) from JSON data. Args:…, Create project-scoped remembered annotations from JSON data. Args: project_id:…, Create sentence and all related entities (tokens, annotations, notes). Args:… (+1 more)

### Community 102 - "Community 102"
Cohesion: 0.14
Nodes (9): Event handler for :attr:`search_input.textChanged` signal: Highlight the search…, QTextEdit, Highlight all occurrences of pattern in text_edit. Args: text_edit: QTextEdit…, Highlight token ranges in ``text_edit`` as search matches. Args: text_edit:…, Clear search highlights from ``text_edit``. If the text edit is read-only, do…, Highlight matches in OE text, translation, and notes. Args: pattern: Search…, Highlight OE token matches for search. Args: pattern: Raw search query.…, Return token ids that match normalized surface/root fields. Args:… (+1 more)

### Community 103 - "Community 103"
Cohesion: 0.12
Nodes (11): fixture, Test cases for UpdateNoteCommand., Set up a note for update tests., Test execute() updates note., Test undo() restores original note text., Test cases for DeleteNoteCommand., Set up a note for delete tests., Test execute() deletes note. (+3 more)

### Community 104 - "Community 104"
Cohesion: 0.12
Nodes (9): Show notes button should appear before Show Details in the toolbar., The Full Translation toolbar export button should target PDF., Test that the window initializes with the correct title and components., Export action should call the PDF exporter with selected path., Successful export should warn if the PDF cannot be opened automatically., Failed export should display exporter-provided error details., Test that sentences are rendered in both OE and ModE edits., Official titles render while auto titles are suppressed; verse stays gapless. (+1 more)

### Community 105 - "Community 105"
Cohesion: 0.12
Nodes (10): MergeSentenceCommand, Command for merging a sentence with the next sentence., Execute merge operation. Returns: True if successful, False otherwise, Undo merge operation. CRITICAL: Uses two-phase approach to handle unique…, Get command description. Returns: Description string, Whether the command needs a full reload of the project structure after…, Get an idiom by ID. Args: idiom_id: ID of the idiom Returns: Idiom or None if…, Merge the current sentence with the next sentence after confirmation. (+2 more)

### Community 106 - "Community 106"
Cohesion: 0.25
Nodes (15): _backfill_annotations(), _backfill_tokens(), _check_constraint_exists(), _column_exists(), downgrade(), _normalize_old_english(), annotation verb metadata and normalized fields Revision ID: d6d8b613bc53…, Return whether the target table exists in the current database. (+7 more)

### Community 107 - "Community 107"
Cohesion: 0.13
Nodes (8): Render OE + ModE into real parallel columns using the ``paracol`` LaTeX…, Indent each rendered line by :attr:`_VERSE_INDENT_EM` em width. Args: rendered:…, Map sentence notes by end-token ID to render end-anchored footnotes. Args:…, Render OE sentence text while injecting LaTeX footnotes. Args: sentence: The…, Render OE text while preserving line alignment and half-line spacing. - Line…, Render modern-English sentence text while preserving line indentation. Args:…, Escape text for LaTeX and preserve repeated interior spaces. Args: value: The…, Convert leading spaces to explicit LaTeX horizontal width. Args: count: The…

### Community 108 - "Community 108"
Cohesion: 0.13
Nodes (8): Messages, Helper class for showing messages in the main window., Show a message in the status bar. Args: message: Message to show Keyword Args:…, Show a warning message. Args: message: Message to show Keyword Args: title:…, Show an error message. Args: message: Message to show Keyword Args: title:…, Show an information message. Args: message: Message to show Keyword Args:…, Setup periodic backup checking., Check if backup is needed and create one if so.

### Community 109 - "Community 109"
Cohesion: 0.17
Nodes (9): BaseTokenDetailsSidebar, QWidget, Base sidebar widget displaying detailed token information., Initialize the base token details sidebar., Set up the UI layout., Show empty state with centered 'Word details' text., Clear all content from the sidebar., Initialize the part of speech renderer. Args: annotation: Annotation to render (+1 more)

### Community 110 - "Community 110"
Cohesion: 0.17
Nodes (15): _build_help_index(), _copy_html_pages(), main(), parse_args(), _prepare_output_directory(), Namespace, Copy rendered HTML pages into the Help Book locale directory. Returns: None, Write Help Book metadata plist consumed by Help Viewer. Returns: None (+7 more)

### Community 111 - "Community 111"
Cohesion: 0.13
Nodes (8): Path, Add the button box to the dialog. The button box will be used to accept or…, Create a new project from the text, split into sentences, split sentences into…, Create a new project., Execute the new project dialog., Build the new project dialog. This means: - Setting the window title - Setting…, Add the title edit to the dialog. The title edit will be used to enter the…, Add bibliographic and translator information fields to the dialog.

### Community 112 - "Community 112"
Cohesion: 0.13
Nodes (9): FullProjectNotesArea, QScrollArea, Area displaying all project notes. Args: project_notes: List of tuples…, Set the selected state of a note widget identified by its note number. Args:…, Highlight search matches in note widgets. Args: text: The text to highlight, Test that searching highlights text in notes., Test that selecting a token deselects any active note., Test that selecting a modern English sentence deselects any active note. (+1 more)

### Community 113 - "Community 113"
Cohesion: 0.14
Nodes (9): A "Tools" menu to be added to the main menu bar with the following actions: -…, Create tools menu. This means adding a "Tools" menu to the main menu bar, with…, Event handler for POS presets management menu item: Show the POS presets…, Open the global remembered annotation management dialog., Open the project-scoped remembered annotation management dialog., ToolsMenu, Test cases for ToolsMenu., Test ToolsMenu creates menu. (+1 more)

### Community 114 - "Community 114"
Cohesion: 0.13
Nodes (14): log_file(), fixture, Tests for the log viewer dialog., Test local time toggle and dataChanged signal., Test live update with new log lines., Create a temporary log file for testing., Test the LogTableModel filtering and data retrieval., Test that LogViewerDialog loads initial logs. (+6 more)

### Community 115 - "Community 115"
Cohesion: 0.18
Nodes (14): Path, Packaging smoke tests for bundled Tectonic integration., Read file content as UTF-8 text., PyInstaller spec should bundle Tectonic assets directory., PyInstaller spec should bundle Alembic config + migration scripts., macOS build script should verify bundled assets before packaging., Windows build script should verify bundled assets before packaging., `make dmg` should rely on create-dmg app-drop-link without precreating symlink. (+6 more)

### Community 116 - "Community 116"
Cohesion: 0.20
Nodes (13): _backfill_annotation_roots(), _column_exists(), downgrade(), _normalize_old_english(), backfill annotation root_normalized data Revision ID: 6fcbc2da5f17 Revises:…, Return whether the target table exists in the current database., Return whether the target column exists on the given table., Normalize root text for stable grouping and lookup. Args: text: Raw root text.… (+5 more)

### Community 117 - "Community 117"
Cohesion: 0.18
Nodes (9): Build ordered project-wide search results for the given pattern and scope.…, Collect search results for a chapter. Args: chapter: Chapter to search. needle:…, Collect search results for a section. Args: section: Section to search.…, Collect search results for a sentence. Args: chapter_id: Owning chapter id.…, ProjectSearchMatches, Search result value objects shared by model search and UI navigation., Ordered project-wide search matches and highlight metadata. Attributes:…, Search result descriptor used for project-wide navigation. Attributes:… (+1 more)

### Community 118 - "Community 118"
Cohesion: 0.14
Nodes (8): AutosaveService, QObject, Service for debounced autosave operations. Args: save_callback: Function to…, Trigger autosave (will be debounced)., Execute the save callback. This method is either called manually by the user…, Force immediate save (bypasses debounce), meaning the autosave timer is…, Cancel pending autosave, meaning the autosave timer is cancelled and the save…, Get the autosave service owned by the main window. Returns: Autosave service…

### Community 119 - "Community 119"
Cohesion: 0.18
Nodes (8): GlossaryEntry, Render compact DB-code annotations for attested forms. Args: annotation: The…, Resolve human-readable verb class label from annotation. Args: annotation:…, Aggregated glossary entry for a unique ``(root, pos)`` key., Aggregate and sort glossary entries with Old English collation rules. Args:…, Merge one attestation into an existing glossary entry. Args: entry: Glossary…, Merge a new root spelling into an existing glossary entry. Args: entry:…, Render classification text for glossary entries. Args: annotation: The…

### Community 120 - "Community 120"
Cohesion: 0.19
Nodes (7): Render glossary legend and entries in three columns. Args: entries: The list of…, Render verb classification block with verb metadata flags. Args: entry:…, Render glossary legend including full verb/adjective/adverb codebooks. Args:…, Render explanatory text beneath the legend columns. Returns: The rendered…, Return LaTeX for a full-width horizontal rule. Returns: The LaTeX for a full-…, Escape user text for safe insertion into LaTeX source. Args: value: The text to…, Build complete LaTeX source for a project export. Args: project: The project to…

### Community 121 - "Community 121"
Cohesion: 0.14
Nodes (10): Any, setter, Return the active project id. Returns: Active project id, or ``None`` when no…, Set or clear the active project id. Args: project_id: Active project id, or…, Return the active chapter id. Returns: Active chapter id, or ``None`` when no…, Set or clear the active chapter id. Args: chapter_id: Active chapter id, or…, Return the active section id. Returns: Active section id, or ``None`` when no…, Set or clear the active section id. Args: section_id: Active section id, or… (+2 more)

### Community 122 - "Community 122"
Cohesion: 0.20
Nodes (8): HelpMenu, _is_offscreen_qt_platform(), Initialize file menu., Return True when tests are using Qt's offscreen platform plugin., A "Help" menu to be added to the main menu bar with the following actions: -…, Adding a "Help" menu to the main menu bar, with the following actions: - Help, Add the primary Help Center action. Returns: None, Add per-topic Help actions for macOS native Help menu search. Returns: None

### Community 123 - "Community 123"
Cohesion: 0.23
Nodes (13): build_manifest(), copy_binary(), copy_bundle(), file_sha256(), main(), parse_args(), Namespace, Path (+5 more)

### Community 124 - "Community 124"
Cohesion: 0.14
Nodes (8): Test pre-migration backup methods., Test that pre-migration backup is created., Test that backup creation fails when database doesn't exist., Test that pre-migration backup can be restored., Test that restore fails when backup doesn't exist., Test that pre-migration backup is deleted., Test that delete doesn't fail when backup doesn't exist., TestPreMigrationBackup

### Community 125 - "Community 125"
Cohesion: 0.14
Nodes (8): Test the complete migration flow., Test that migrate() returns early when no pending migrations., Test that migrate() creates backup before applying migrations., Test that migrate() deletes backup after successful migration., Test that migrate() restores backup when migration fails., Test that migrate() logs backup operations., Test that migrate() logs when no pending migrations., TestMigrationFlow

### Community 126 - "Community 126"
Cohesion: 0.23
Nodes (12): ensure_runtime_help_assets(), HelpPaths, Path, Resolve and synchronize QtHelp runtime paths., Bundled and runtime file locations for QtHelp assets., Return canonical bundled/runtime locations for help assets., Ensure runtime QtHelp assets exist in writable storage. Returns: Resolved help…, Copy a file if content differs. (+4 more)

### Community 127 - "Community 127"
Cohesion: 0.18
Nodes (7): PresetPosFormManager, QFormLayout, QVBoxLayout, QWidget, Manager for preset-dialog POS forms., Reset rendered fields., Load values into managed fields.

### Community 128 - "Community 128"
Cohesion: 0.15
Nodes (8): setter, Refresh cached references from the current highlighter state., Get the filter selection., Set the filter selection., Initialize the mixin., Get the Old English text edit for the sentence card., Set the sentence card for the sentence highlighter., Refresh cached token/idiom/annotation references from the text edit.

### Community 129 - "Community 129"
Cohesion: 0.17
Nodes (7): QKeyEvent, Navigate to next token in the sentence and in the token table. - If no token is…, Navigate to previous token in the sentence and in the token table. - If no…, Handle copy annotation request from OE text edit., Handle paste annotation request from OE text edit., Handle key press events. If we are in read-only mode, handle arrow keys and…, Set the selected token index and highlight the token. If ``emit`` is ``True``,…

### Community 130 - "Community 130"
Cohesion: 0.18
Nodes (7): QTextCursor, Get set of all token IDs that are part of an idiom. Returns: Set of all token…, Restore the original text. - Restore the original text to the sentence - Render…, Resize the text edit to fit the text and its superscripts with a 20% margin.…, Render OE text with note superscripts and idiom italics. This is the method we…, Render a single token with its formatting and superscripts. Args: cursor:…, Render note superscripts. Args: cursor: QTextCursor to render the superscripts…

### Community 131 - "Community 131"
Cohesion: 0.21
Nodes (12): _bundle_dir(), Path, resolve_help_paths should compose expected bundled/runtime paths., ensure_runtime_help_assets should fail with clear error if files are missing., Runtime qch and qhc should sync from bundled assets., Search guide markdown topic should exist in source topics., Remembered annotations help topic should exist in source topics., test_ensure_runtime_help_assets_copies_qch_and_qhc() (+4 more)

### Community 132 - "Community 132"
Cohesion: 0.21
Nodes (11): downgrade(), _find_hyphenated_words(), _map_tokens_to_positions(), _merge_tokens_for_hyphenated_word(), Merge hyphenated words Revision ID: merge_hyphenated_words Revises:…, Merge tokens to form a hyphenated word. Args: conn: Database connection…, Upgrade: Merge hyphenated words that were split into separate tokens., Find all hyphenated words in text with their positions. Args: text: The… (+3 more)

### Community 133 - "Community 133"
Cohesion: 0.26
Nodes (11): file_sha256(), main(), parse_args(), Namespace, Path, Parse CLI arguments. Returns: argparse.Namespace: The parsed arguments., Return SHA-256 hash for a file. Args: path: The path to the file. Returns: The…, Verify minimum cross-platform payload requirements. Side Effects: Adds errors… (+3 more)

### Community 134 - "Community 134"
Cohesion: 0.17
Nodes (7): Test save_now() cancels pending timer., Test cases for AutosaveService., Test cancel() does not call save callback., Test trigger() cancels existing timer., Test trigger() calls save_callback after debounce period., Test multiple trigger() calls only result in one save., TestAutosaveService

### Community 135 - "Community 135"
Cohesion: 0.18
Nodes (10): _alembic_config(), _fetch_indexes(), Config, Path, Return Alembic config pointing at project alembic.ini., Fetch explicit index names from sqlite_master., Fresh create_all schema should include performance indexes., Validate index presence for existing DB migration path. (+2 more)

### Community 136 - "Community 136"
Cohesion: 0.17
Nodes (7): Test DeleteProjectDialog initializes correctly., Test DeleteProjectDialog builds correctly., Test DeleteProjectDialog loads projects into table., Test DeleteProjectDialog filters projects by search., Test DeleteProjectDialog handles case with no projects., Test cases for DeleteProjectDialog., TestDeleteProjectDialog

### Community 137 - "Community 137"
Cohesion: 0.17
Nodes (7): Test em-dash (—) in hyphenated words., Test cases for Token.tokenize., Test tokenizing with punctuation attached to words., Test that ġe-wāt becomes a single token., Test that be-ġȳman becomes a single token., Test multiple hyphenated words in one sentence., TestTokenize

### Community 138 - "Community 138"
Cohesion: 0.17
Nodes (7): Test cases for Token.tokenize() static method., Test tokenizing a simple sentence., Test tokenizing an empty string., Test tokenizing whitespace-only string., Test tokenizing Old English characters., Test tokenizing with punctuation., TestTokenize

### Community 139 - "Community 139"
Cohesion: 0.18
Nodes (11): App icon 128x128@2x, App icon 128x128, App icon 16x16@2x, App icon 16x16, App icon 256x256@2x, App icon 256x256, App icon 32x32@2x, App icon 32x32 (+3 more)

### Community 140 - "Community 140"
Cohesion: 0.31
Nodes (10): _create_index_if_missing(), downgrade(), _drop_index_if_exists(), _index_exists(), Return whether the target table exists in the current database., Return whether an index already exists on the target table., Create index only when table exists and index is absent., Drop index only when table exists and index is present. (+2 more)

### Community 141 - "Community 141"
Cohesion: 0.20
Nodes (6): Any, Orientation, Get the log line at the given row. Args: row: The row index. Returns: The log…, Build the UI for the log viewer dialog. This will create the layout and add the…, Get the header data for the given section. This is used to display the column…, QTableView

### Community 142 - "Community 142"
Cohesion: 0.20
Nodes (6): QHBoxLayout, QWidget, Build the rows for the checkboxes. Args: code: Code for the item Returns:…, Get the full filter selection. Returns: Set of all possible filter selections…, Initialize the mixin. Args: parent: Parent widget, Reset the filter selection to all possible values.

### Community 143 - "Community 143"
Cohesion: 0.22
Nodes (7): ProjectMenu, A "Project" menu to be added to the main menu bar with the following actions: -…, Populate the project menu with the following actions: This means adding a…, Test ProjectMenu has Edit Project action., Test cases for ProjectMenu., Test ProjectMenu creates menu., TestProjectMenu

### Community 144 - "Community 144"
Cohesion: 0.20
Nodes (5): Tokenize a sentence. Args: sentence_text: Text of the sentence to tokenize…, Test multiple hyphenated words with punctuation., Test tokenizing a sentence with punctuation., Test tokenizing a complex sentence., Test that be-bode becomes a single token.

### Community 145 - "Community 145"
Cohesion: 0.20
Nodes (5): Add the button box to the dialog. The button box will be used to accept or…, Open an existing project., Open an existing project., Build the open project dialog., Update the project list in the table widget by loading projects from the…

### Community 146 - "Community 146"
Cohesion: 0.22
Nodes (7): _indent_multiline_plain(), Full translation side-by-side window., Prefix each non-empty line with fixed-space indentation. Args: text: Input text…, HorizontalSeparatorWidget, QWidget, A simple horizontal separator widget. Keyword Args: parent: Parent widget…, QFrame

### Community 147 - "Community 147"
Cohesion: 0.20
Nodes (6): QMouseEvent, QPoint, Find the token index that contains the given character position. Uses the…, Annotate the token at the given position. Args: position: Mouse double-click…, Handle mouse press event and emit clicked signal. Args: event: Mouse press event, Handle mouse double-click event and open the annotation modal. Args: event:…

### Community 148 - "Community 148"
Cohesion: 0.20
Nodes (6): FullTranslationSidebar, Sidebar widget displaying detailed token information in the full translation…, Set whether the sidebar is currently open/visible. Args: is_open: Whether the…, Handle token deselection: Close the sidebar, and show the empty state., Handle token selection: Open the sidebar and render the token details. Args:…, Handle idiom selection: Open the sidebar and render the idiom details. Args:…

### Community 149 - "Community 149"
Cohesion: 0.20
Nodes (6): Test that has_pending_migrations returns False when DB is up to date., Test that has_pending_migrations returns True for fresh database with…, Test that has_pending_migrations returns False for fresh DB with no migrations., Test has_pending_migrations() method., Test that has_pending_migrations returns True when DB is behind., TestHasPendingMigrations

### Community 150 - "Community 150"
Cohesion: 0.20
Nodes (6): Test cases for OpenProjectDialog., Test OpenProjectDialog initializes correctly., Test OpenProjectDialog builds correctly., Test OpenProjectDialog loads projects into table., Test OpenProjectDialog filters projects by search., TestOpenProjectDialog

### Community 151 - "Community 151"
Cohesion: 0.20
Nodes (6): Test cases for get_logo_pixmap()., Test returns QPixmap when logo file exists., Test returns None when logo file doesn't exist., Test pixmap is scaled to specified size., Test handles different size parameters., TestGetLogoPixmap

### Community 152 - "Community 152"
Cohesion: 0.20
Nodes (6): Test cases for from_utc_iso()., Test parsing valid ISO format string., Test parsing ISO string with Z timezone indicator., Test parsing naive ISO string (no timezone)., Test returns None when input is None., TestFromUtcIso

### Community 153 - "Community 153"
Cohesion: 0.22
Nodes (7): HelpEngineError, RuntimeError, QtHelp engine wrapper used by the help center UI., Raised when QtHelp cannot initialize or register documentation., HelpTopic, Shared help topic metadata., Metadata for a single help topic.

### Community 154 - "Community 154"
Cohesion: 0.25
Nodes (5): QColor, Darken a color by 40%., Redden a color by 40%., Get the base color for the theme., Get the color map for the given prefix. Args: color_map_name: The name of the…

### Community 155 - "Community 155"
Cohesion: 0.22
Nodes (5): Sentence Card associated with this text edit., Set the sentence card associated with this text edit. Args: value: Sentence card, Disconnect signals from sentence card, token table, and token details sidebar., Connect signals to sentence card, token table, and token details sidebar., Set the tokens for the text edit, and highlight the sentence with the sentence…

### Community 156 - "Community 156"
Cohesion: 0.22
Nodes (5): setter, Whether the text edit is in edit mode (read-only or editable)., Reset the selected token. - Reset the selected token index and range - Clear…, Unhighlight the text edit., Render editable OE text. Args: text: Text to render

### Community 157 - "Community 157"
Cohesion: 0.22
Nodes (5): QComboBox, Find a loaded sentence card by sentence id. Args: sentence_id: Target sentence…, Set combo current index by item data id. Args: combo: Combo box to update.…, Load chapter/section for a sentence and return its sentence card. Args:…, Handle sentence added signal. Reloads the project from the database to refresh…

### Community 158 - "Community 158"
Cohesion: 0.25
Nodes (6): parametrize, Test cases for specific POS field subclasses., Test that all POS fields map to valid Annotation model attributes., Test that fields requiring special maps (like PRONOUN_NUMBER_MAP) use them., TestPartOfSpeechSubclasses, TestPOSFieldModelMapping

### Community 159 - "Community 159"
Cohesion: 0.25
Nodes (4): Undo note deletion. Returns: True if successful, False otherwise, Execute note creation. Returns: True if successful, False otherwise, Get next note number for the sentence. Returns: Next note number, Create a new note. Args: sentence_id: Sentence ID start_token_id: Start token…

### Community 160 - "Community 160"
Cohesion: 0.25
Nodes (4): Create a project from JSON import data. Args: session: SQLAlchemy session…, Resolve project name collision by appending number. Args: name: Original…, Create project entity from data. Args: project_data: Project data dictionary…, Test from_json() creates project from data.

### Community 161 - "Community 161"
Cohesion: 0.25
Nodes (5): Test cases for MainMenu., Test MainMenu initializes correctly., Test MainMenu adds menu to menu bar., Test MainMenu builds all menus., TestMainMenu

### Community 162 - "Community 162"
Cohesion: 0.25
Nodes (5): Test cases for to_utc_iso()., Test converting naive datetime to UTC ISO string., Test converting timezone-aware datetime to UTC ISO string., Test returns None when input is None., TestToUtcIso

### Community 163 - "Community 163"
Cohesion: 0.29
Nodes (6): enable_autosave, Tests for the suite-level autosave policy., Autosave trigger should be disabled unless a test opts in., Opt-in marker should restore real autosave behavior., test_autosave_can_be_enabled_per_test(), test_autosave_disabled_by_default()

### Community 164 - "Community 164"
Cohesion: 0.52
Nodes (6): _column_exists(), downgrade(), Return whether the target table exists in the current database., Return whether the target column exists on the given table., _table_exists(), upgrade()

### Community 165 - "Community 165"
Cohesion: 0.33
Nodes (4): Path, Determine whether input bytes should be treated as gzip. Detection order: 1.…, Load JSON payload from plain or gzip-compressed export file. Args: path: Input…, Load field mappings from JSON file. Returns: Dictionary mapping migration SHA…

### Community 166 - "Community 166"
Cohesion: 0.38
Nodes (4): QModelIndex, QPersistentModelIndex, Get the number of rows in the model. Args: parent: The parent index., Get the number of columns in the model. Args: parent: The parent index.

### Community 167 - "Community 167"
Cohesion: 0.29
Nodes (4): Show a token-aware context menu for remembered annotation actions. Args: event:…, Get the current selected token range., Get a token by its order index., QContextMenuEvent

### Community 168 - "Community 168"
Cohesion: 0.29
Nodes (5): _import_fixture_project(), Path, Import a project fixture from ``texts/`` and return the created project., Seafarer fixture output should include new layout and preserve long ash., Cædmon fixture should split ``in`` prepositions by case and build used-only…

### Community 169 - "Community 169"
Cohesion: 0.33
Nodes (3): Create chapter (and nested sections/paragraphs) from JSON import data. Args:…, Create paragraph from JSON import data. Args: section_id: Section ID…, Create section (and nested paragraphs) from JSON import data. Args: chapter_id:…

### Community 170 - "Community 170"
Cohesion: 0.33
Nodes (3): Get the session from the application state. Returns: SQLAlchemy session, Save the model. Keyword Args: commit: Whether to commit the changes, Delete the model. Keyword Args: commit: Whether to commit the changes Raises:…

### Community 171 - "Community 171"
Cohesion: 0.33
Nodes (3): Serialize note to JSON-compatible dictionary (without PKs). Args: session:…, Get a token by ID. Args: token_id: Token ID Returns: Token or None if not found, Test get() returns None for nonexistent token.

### Community 172 - "Community 172"
Cohesion: 0.40
Nodes (4): CompletedProcess, Path, Export project text as PDF using bundled Tectonic. Args: project_id: The ID of…, Copy ``.tex``/``.log`` artifacts near the destination for debugging. Args:…

### Community 173 - "Community 173"
Cohesion: 0.33
Nodes (3): Show a transient status message. Args: message: Message to show. Keyword Args:…, Undo the most recent command. Side Effects: Refreshes or reloads the main…, Redo the most recently undone command. Side Effects: Refreshes or reloads the…

### Community 174 - "Community 174"
Cohesion: 0.33
Nodes (4): IdiomHighlighterCommand, Highlighter for idiom highlighting in the Old English text edit. An idiom is a…, Highlight the tokens in the sentence based on the active command. Note: Because…, Test idiom highlighting logic.

### Community 175 - "Community 175"
Cohesion: 0.33
Nodes (4): POSHighlighterCommand, Highlighter command for POS highlighting., Get the value of the annotation for the command. Args: annotation: Annotation…, Test POSHighlighterCommand value extraction.

### Community 176 - "Community 176"
Cohesion: 0.33
Nodes (3): A "Window" menu to be added to the main menu bar., Populate the window menu with the following actions: - Full Translation, WindowMenu

### Community 177 - "Community 177"
Cohesion: 0.33
Nodes (4): Test cases for SessionLocal., Test SessionLocal is defined., Test SessionLocal creates a session., TestSessionLocal

### Community 178 - "Community 178"
Cohesion: 0.33
Nodes (4): Test cases for Base declarative base., Test Base has metadata attribute., Test Base has registry for models., TestBase

### Community 179 - "Community 179"
Cohesion: 0.33
Nodes (4): Test cases for MainWindow initialization and basic layout., Test MainWindow initializes with correct basic properties., Test that the empty state is shown on startup., TestMainWindowInitialization

### Community 180 - "Community 180"
Cohesion: 0.60
Nodes (5): Aenglisc Toolkit Logo, Green goblin creature peering at book, Library bookshelf backdrop in circular badge, Open book, Elderly bespectacled scholar reading book

### Community 181 - "Community 181"
Cohesion: 0.40
Nodes (3): Match, Convert runs of spaces into one normal space + explicit width. Args: match: The…, Normalize wide internal gaps to a fixed 4 space visual width. Args: _match: The…

### Community 182 - "Community 182"
Cohesion: 0.40
Nodes (4): downgrade(), Downgrade schema - revert to old constraint definitions., Upgrade schema - update CHECK constraints to match model definitions. SQLite…, upgrade()

### Community 183 - "Community 183"
Cohesion: 0.40
Nodes (3): Get the paragraph with the given order - 1 in the same section. Args:…, Create a new paragraph. Args: section_id: Section ID order: Paragraph order…, test_paragraph_methods_cover_ordering_navigation_and_json()

### Community 184 - "Community 184"
Cohesion: 0.40
Nodes (3): Path, Get text from the input method (either pasted text or selected file). Returns:…, Return text/path suitable for wyrdcraeft ``DocumentIngestor``. Returns: Tuple…

### Community 185 - "Community 185"
Cohesion: 0.40
Nodes (5): qt_no_exception_capture, Test idiom selection in SentenceCard., Test navigation from idiom modal to token modal., test_idiom_modal_navigation(), test_idiom_selection_ui()

### Community 186 - "Community 186"
Cohesion: 0.40
Nodes (4): _cleanup_mock_window(), fixture, Unit tests for Menus., Ensure menu test windows are cleaned up between tests.

### Community 196 - "Community 196"
Cohesion: 0.50
Nodes (3): FieldRenderer, Any, Format a field label based on whether value is set. Args: label: Label to…

### Community 197 - "Community 197"
Cohesion: 0.50
Nodes (4): Render SVG data to a QPixmap at the specified size. Args: svg_data: SVG data to…, render_svg(), QIcon, QPixmap

### Community 198 - "Community 198"
Cohesion: 0.50
Nodes (3): Tests for SQLite index presence on fresh and upgraded schemas., Validate index presence for fresh DB creation path., TestFreshSchemaIndexes

### Community 199 - "Community 199"
Cohesion: 0.50
Nodes (3): Unit tests for NewProjectDialog., Test cases for NewProjectDialog., TestNewProjectDialog

### Community 200 - "Community 200"
Cohesion: 1.00
Nodes (3): Search Guide, Search scopes: OE, ModE, Notes, All, OE normalization rules

### Community 224 - "Community 224"
Cohesion: 0.67
Nodes (3): fixture, Create a SentenceCard for testing., sentence_card()

### Community 225 - "Community 225"
Cohesion: 0.67
Nodes (3): fixture, Update sample sentence for idiom tests., sentence()

### Community 226 - "Community 226"
Cohesion: 0.67
Nodes (3): fixture, Create a MainWindow instance for testing., window()

## Knowledge Gaps
- **50 isolated node(s):** `build_macos.sh script`, `aenglisc_toolkit`, `Tooling Preflight Evidence`, `Contributor Covenant 3.0 Code of Conduct`, `PyInstaller build (oe_annotator.spec)` (+45 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 2589 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **90 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Project` connect `ORM Base & Commands` to `Annotation Text Formatting`, `Token Occurrence & Migrations`, `Note Commands`, `Merge Section/Chapter Commands`, `DOCX Exporter`, `Append/Delete Project Dialogs`, `Database Engine & Session`, `Sentence Add/Delete Operations`, `Remembered Annotations`, `Text Ingestion & Sections`, `Community 146`, `Domain Exceptions`, `MainWindow Actions`, `MainWindow UI`, `Sentence Splitter`, `Community 160`, `Project Model & Edit`, `Project UI`, `Project Model Tests`, `Project JSON Exporter`, `Community 40`, `Community 42`, `Community 44`, `Community 45`, `Community 47`, `Community 176`, `Community 49`, `Community 50`, `Community 54`, `Community 183`, `Community 61`, `Community 63`, `Community 71`, `Community 199`, `Community 74`, `Community 79`, `Community 94`, `Community 97`, `Community 101`, `Community 104`, `Community 107`, `Community 117`, `Community 119`, `Community 120`, `Community 122`?**
  _High betweenness centrality (0.152) - this node is a cross-community bridge._
- **Why does `Token` connect `Token Occurrence & Migrations` to `Annotation Text Formatting`, `Annotation Table Widget`, `ORM Base & Commands`, `Note Commands`, `Merge Section/Chapter Commands`, `DOCX Exporter`, `Community 264`, `Append/Delete Project Dialogs`, `Community 137`, `Community 138`, `Annotation Preset Model`, `Remembered Annotations`, `Community 144`, `Community 146`, `Token Diff & Update`, `Sentence Filter Dialogs`, `Annotation Lookup`, `Command Pattern Base`, `Project UI`, `Community 171`, `Community 44`, `Community 52`, `Community 57`, `Community 61`, `Community 62`, `Community 64`, `Community 67`, `Community 70`, `Community 79`, `Community 97`, `Community 98`, `Community 105`, `Community 109`, `Community 119`, `Community 255`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `MainWindow` connect `MainWindow UI` to `Token Occurrence & Migrations`, `ORM Base & Commands`, `Note Commands`, `Append/Delete Project Dialogs`, `Annotation Preset Model`, `Help Center Dialog`, `Sentence Card Controller`, `Community 146`, `Domain Exceptions`, `AppContext`, `Community 153`, `Sentence Filter Dialogs`, `MainWindow Tests`, `Project Model & Edit`, `Project UI`, `Community 40`, `Community 42`, `Community 47`, `Community 62`, `Community 65`, `Community 67`, `Community 71`, `Community 72`, `Community 74`, `Community 75`, `Community 77`, `Community 85`, `Community 226`, `Community 100`, `Community 108`, `Community 122`?**
  _High betweenness centrality (0.097) - this node is a cross-community bridge._
- **Are the 47 inferred relationships involving `Project` (e.g. with `Chapter` and `AlreadyExists`) actually correct?**
  _`Project` has 47 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `SentenceCard` (e.g. with `WholeSentenceHighlighter` and `MainWindow`) actually correct?**
  _`SentenceCard` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 36 inferred relationships involving `Token` (e.g. with `MergeSentenceCommand` and `Note`) actually correct?**
  _`Token` has 36 INFERRED edges - model-reasoned connections that need verification._
- **What connects `build_macos.sh script`, `aenglisc_toolkit`, `Tooling Preflight Evidence` to the rest of the system?**
  _50 weakly-connected nodes found - possible documentation gaps or missing edges._
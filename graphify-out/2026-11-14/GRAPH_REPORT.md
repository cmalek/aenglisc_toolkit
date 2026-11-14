# Graph Report - aenglisc_toolkit  (2026-11-02)

## Corpus Check
- 288 files · ~1,470,369 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 30 file(s) not represented in the graph (top: (none) 9, .ttf 5, .cfg 1)

## Summary
- 7116 nodes · 16572 edges · 307 communities (137 shown, 170 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1978 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `9818c8eb`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- db.py
- WyrdcraeftIngestService
- TestMainWindowActions
- .get
- AnnotationModal
- sentence_separator_kind
- Annotation
- PosFieldCatalog
- test_typed_run.py
- Project
- get_runtime_session
- OpenProjectDialog
- AnnotationPreset
- Command
- test_remembered_annotations.py
- test_edit_menu.py
- NewProjectDialog
- TestAnnotationPresetManagementDialog
- Start Here
- TestAutosaveService
- test_runtime_session_freeze.py
- .create
- ProjectExporter
- Task 3: Migrate the three writers to layers (atomic)
- TestBackupService
- DeleteProjectDialog
- .split_sentences
- TestTokenize
- MigrationMetadataService
- TestSentenceCard
- TestSingleInstanceHighlighter
- SearchController
- check_napoleon_gate.py
- TokenTable
- AnnotationJson
- test_migration_flow.py
- OldEnglishTextEdit
- AnnotationPresetManagementDialog
- Paragraph
- import_export_schema.py
- .from_annotation
- LogTableModel
- UnknownDatabaseRevision
- LogViewerDialog
- MigrationService
- RememberedAnnotationsDialog
- AbstractPartOfSpeechRenderer
- HelpCenterDialog
- FullProjectModernEnglishTextEdit
- MigrationFailureDialog
- DOCXExporter
- CommandLocators
- HelpEngine
- ProjectImporter
- TestMainWindowInitialization
- HighlightLayers
- BackupService
- annotation_modal.py
- .__init__
- ProjectMenu
- UndoCommand
- HelpMenu
- FullProjectTextSelector
- RestoreDialog
- .get_by_token
- main_window
- TestFullTranslationPDFExporter
- MainWindowActions
- pdf_engine.py
- ProjectUI
- ToolsMenu
- .build
- ImportProjectDialog
- test_translation_undo_keys.py
- TestPartOfSpeechFieldsBase
- HelpTextBrowser
- Section
- _actions
- fixture
- build_help.py
- TestOldEnglishTextEdit
- 7cd945e38aff_repair_declension_and_verb_class_codes.py
- EditProjectDialog
- Token
- AnnotateTokenCommand
- apply_theme
- AppContext
- AnnotationTableWidget
- .test_line_initial_token_can_be_remembered_from_context_menu
- test_migration_pos_codes.py
- TypedRun
- d6d8b613bc53_annotation_verb_metadata_and_normalized_.py
- ensure_runtime_help_assets
- TokenDetailsSidebar
- _check_function_doc
- TestEditModeAndRerender
- EditMenu
- ADR NNNN: <short, decision-oriented title>
- TestAnnotationEmptinessPredicates
- ThemeMixin
- test_undo_navigation.py
- Sentence
- TestAppContext
- TestFromUtcIso
- .export_side_by_side_pdf
- AnnotationPropagationService
- FullTranslationPDFExporter
- EditSentenceCommand
- MainMenu
- PresetPartOfSpeechFieldsBase
- read_text
- test_state.py
- ._add_topic_actions
- .render_idiom
- TextInputMixin
- AutosaveService
- SentenceCardController
- prepare_tectonic_assets.py
- MockSentenceCard
- Sentence Notes
- _OkCommand
- Messages
- get_resource_path
- .build
- test_search.py
- Start Here
- Morphological Annotation
- sqlalchemy
- table_to_model_name
- verify_tectonic_assets.py
- TestTokenize
- Annotation
- ._latex_escape
- 71b9d6456d8b_add_sqlite_performance_indexes.py
- _Signal
- File Structure
- _apply_message
- AnnotationLookupsMixin
- .clear_sidebar
- Bundled Tectonic PDF Payload
- create_engine_with_path
- MainWindow
- MockMainWindow
- TestToUtcIso
- test_migration_backup_restore.py
- DoesNotExist
- NotesPanel
- Annotation Modal
- Ænglisc Toolkit
- get_logo_pixmap
- ._reload_after_structure_change
- SingleInstanceHighlighter
- _accumulate_definition
- apply_theme Helper
- test_log_table_model
- Scheduled Project Database Backup
- DOCX Export
- schema_1_0_0.sql
- visible_titles
- SearchResult
- read_alembic_revision
- Elderly Scholar (Tolkien-like)
- Circular App Logo Icon
- Circular App Icon
- Aenglisc Toolkit 512px icon
- Circular Library Reading Logo
- Aenglisc Toolkit circular logo
- .build_toolbar
- _actions
- JSON Project Export
- Aenglisc Toolkit
- OldEnglishTextSelector
- TestAnnotationModalLifecycle
- TestMainWindowOptimizeHooks
- test_pos_code_repair.py
- load_projects_into_table
- _sqlite_pragma_settings
- build_macos_helpbook.py
- TestMainMenu
- Circular App Icon
- Circular Earth-Tone Emblem
- Circular Logo Illustration
- Circular App Logo Icon 32x32@2x
- 32x32 Circular App Icon
- Elderly Scholar in Glasses and Suit
- Sentence Word-Range Notes
- DOCX Export
- Start Here
- Annotation Metadata Fields
- FullProjectNoteWidget
- TranslationUndoFilter
- TestResolveThemeName
- BackupFailed
- FullTranslationWindow
- SettingsDialog
- AppendTextDialog
- ._on_theme_changed
- ReadingTextExporter
- Morphological Annotation
- Reusable Token Annotation Template
- .root
- FailCommand
- Bespectacled Reader
- AnnotationPosFormManager
- PDF Export
- TestModalBuildsFromCatalog
- .update_logs
- patch
- File Structure
- TestSessionLocal
- TestBase
- TestSettingsDialog
- TestNavigationButtonAffordances
- TestThemeRefreshReachesStaleSites
- TestSidebarResizing
- AddSentenceCommand
- test_token_details_sidebar.py
- _iter_module_globals
- POS Field Catalog (F2) Implementation Plan
- sentence
- get_logger
- token_details_sidebar.py
- sentence_card
- log_file
- check_help_rebuild.sh
- _cleanup_mock_window
- Chris Malek
- Contributor Covenant 3.0
- test_idiom_modal_navigation
- Narrow Qt App Context
- Usability Overhaul Ready Slices Plan
- TestEmptyStateStyling
- Application Theme
- SentenceCard
- push_command
- aenglisc_toolkit

## God Nodes (most connected - your core abstractions)
1. `get_runtime_session()` - 441 edges
2. `create_test_project()` - 353 edges
3. `Annotation` - 198 edges
4. `Project` - 194 edges
5. `SentenceCard` - 191 edges
6. `Sentence` - 172 edges
7. `Token` - 158 edges
8. `create_test_sentence()` - 131 edges
9. `MainWindow` - 116 edges
10. `Note` - 101 edges

## Surprising Connections (you probably didn't know these)
- `Task 1: Delete `get_session`` --references--> `get_runtime_session()`  [INFERRED]
  docs/superpowers/plans/2026-11-01-f7-annotation-apply-and-get-session.md → oeapp/db.py
- `Task 3: Allowlist the oeapp tree` --references--> `count_runtime_session_lookups()`  [INFERRED]
  docs/superpowers/plans/2026-10-26-runtime-session-freeze.md → tests/test_runtime_session_freeze.py
- `Task 8: Stack entries follow the sentence and the token` --references--> `CommandLocators`  [INFERRED]
  docs/superpowers/plans/2026-10-24-undo-history.md → oeapp/commands/abstract.py
- `F4: Finish SentenceCard Controller Split; Stop Widget ORM Writes — Implementation Plan` --references--> `Command`  [INFERRED]
  docs/superpowers/plans/2026-09-04-f4-sentence-card-controller-split.md → oeapp/commands/abstract.py
- `File Structure` --references--> `Command`  [INFERRED]
  docs/superpowers/plans/2026-10-24-undo-history.md → oeapp/commands/abstract.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Local data safety and recovery** — oeapp_help_topics_automatic_backups_scheduled_backup, oeapp_help_topics_project_export_import_json_export, oeapp_help_topics_start_here_undo_model, oeapp_help_topics_start_here_data_safety_model [EXTRACTED 1.00]
- **Formatted and project export formats** — oeapp_help_topics_export_formatting_docx_export, oeapp_help_topics_export_formatting_pdf_export, oeapp_help_topics_project_export_import_json_export [EXTRACTED 1.00]
- **Local backups, JSON export, and undo limits** — oeapp_help_assets_automatic_backups_backup_files, oeapp_help_assets_project_export_import_json_export, oeapp_help_assets_start_here_undo_model [EXTRACTED 1.00]
- **DOCX, PDF, and JSON export channels** — oeapp_help_assets_export_formatting_docx_export, oeapp_help_assets_export_formatting_pdf_export, oeapp_help_assets_project_export_import_json_export [EXTRACTED 1.00]
- **Project Export Formats** — oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_export_formatting_docx_export, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_export_formatting_pdf_export, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_project_export_import_json_export [EXTRACTED 1.00]
- **Help Topic Hub** — oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_start_here_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_annotation_guide_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_idioms_guide_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_incremental_annotation_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_notes_guide_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_search_guide_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_full_translation_window_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_export_formatting_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_project_export_import_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_automatic_backups_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_morphological_reference_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_troubleshooting_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_settings_page, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_keybindings_page [EXTRACTED 1.00]
- **Mandatory oeapp layer seams** — agents_fat_orm_models, agents_service_bridge, agents_pyside6_ui, agents_in_app_help [EXTRACTED 1.00]
- **Token and phrase annotation workflow** — oeapp_help_topics_annotation_guide_morphological_annotation, oeapp_help_topics_idioms_guide_idiom, oeapp_help_topics_incremental_annotation_iterative_refinement, oeapp_help_topics_remembered_annotations_reusable_token_template [INFERRED 0.85]
- **Annotation workflow across token, idiom, incremental, and remembered templates** — oeapp_help_assets_annotation_guide_morphological_annotation, oeapp_help_assets_idioms_guide_idiom_annotation, oeapp_help_assets_incremental_annotation_philosophy, oeapp_help_assets_remembered_annotations_templates [INFERRED 0.85]
- **Annotation Workflow** — oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_annotation_guide_morphological_annotation, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_idioms_guide_idiom, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_incremental_annotation_iterative_refinement, oeapp_help_macos_aenglisctoolkit_help_contents_resources_en_lproj_morphological_reference_tag_codes [INFERRED 0.85]

## Communities (307 total, 170 thin omitted)

### Community 0 - "db.py"
Cohesion: 0.04
Nodes (16): Base, _RuntimeState, run_migrations_offline(), Idiom, SaveDeleteMixin, RememberedAnnotation, from_utc_iso(), normalize_old_english() (+8 more)

### Community 1 - "WyrdcraeftIngestService"
Cohesion: 0.04
Nodes (8): AlreadyExists, CanonicalRun, VerseStanza, WyrdcraeftIngestService, TestAlreadyExists, _canonical_mixed(), test_ingest_mixed_creates_poem_chapter_and_prose_auto_titles(), test_ingest_pure_verse_chunks_sections_by_20_stanzas()

### Community 3 - ".get"
Cohesion: 0.10
Nodes (10): MergeParagraphCommand, SplitParagraphCommand, TestSplitParagraphCommand, _create_three_sentences_single_paragraph(), test_merge_paragraph_command_execute_and_undo(), test_merge_paragraph_command_fails_when_first_paragraph(), test_merge_paragraph_command_fails_when_sentence_not_paragraph_start(), test_split_paragraph_command_execute_and_undo() (+2 more)

### Community 4 - "AnnotationModal"
Cohesion: 0.04
Nodes (3): AnnotationModal, TestAnnotationModal, __init__()

### Community 5 - "sentence_separator_kind"
Cohesion: 0.11
Nodes (6): is_paragraph_start(), latex_separator(), plain_text_separator(), sentence_separator_kind(), SentenceSeparatorKind, TestTextFlow

### Community 6 - "Annotation"
Cohesion: 0.03
Nodes (8): Task 4b: Display helpers tolerate unrecognised codes, AnnotationTextualMixin, Annotation, create_test_sentence(), test_undo_snapshot_keeps_grammatical_and_lexical_fields_only(), TestAnnotation, TestAnnotationTextualMixin, TestAnnotationTextualMixinUnknownCodes

### Community 7 - "PosFieldCatalog"
Cohesion: 0.18
Nodes (13): Task 1: The catalog module and its parity tests, PosFieldCatalog, _check_codes(), test_check_parser_finds_known_columns(), test_declension_and_verb_class_opt_out_of_clear(), test_every_attr_is_an_annotation_column(), test_field_less_and_unknown_pos_have_no_fields(), test_lookup_map_codes_match_check_constraints() (+5 more)

### Community 8 - "test_typed_run.py"
Cohesion: 0.11
Nodes (33): _assert_new_step_after(), _assert_same_step_after(), card(), mock_services(), run(), test_add_note_dismissed_ends_run(), test_annotation_modal_dismissed_ends_run(), test_app_undo_and_redo_end_the_run() (+25 more)

### Community 9 - "Project"
Cohesion: 0.03
Nodes (8): Project, command_setup(), project_and_sentence(), _legacy_verbose_export_size(), TestProject, test_project_updated_at_on_sentence_create(), test_timestamps_are_utc(), search_project()

### Community 10 - "get_runtime_session"
Cohesion: 0.02
Nodes (11): get_runtime_session(), create_test_project(), test_annotation_preserved_on_multiple_typo_fixes(), test_annotation_preserved_on_typo_fix(), test_annotation_shift_on_deletion(), test_annotation_shift_on_insertion(), test_annotation_stability_with_duplicate_surfaces(), TestNote (+3 more)

### Community 12 - "AnnotationPreset"
Cohesion: 0.05
Nodes (4): AnnotationPreset, AnnotationPresetService, TestPartOfSpeechFormManager, TestAnnotationPresetService

### Community 13 - "Command"
Cohesion: 0.04
Nodes (14): Global Constraints, Command, ApplyAnnotationPropagationCommand, ApplyRememberedAnnotationsCommand, TokenBatchLocators, MergeChapterCommand, MergeSectionCommand, SplitChapterCommand (+6 more)

### Community 14 - "test_remembered_annotations.py"
Cohesion: 0.05
Nodes (21): AmbiguousRememberedSpellingError, RememberedAnnotationApplyPlan, RememberedAnnotationService, _run_apply_dialog(), _sorted_tokens(), test_annotation_modal_remembered_mode_disables_sense_and_blanks_on_save(), test_apply_blocks_global_when_the_project_group_is_ambiguous(), test_apply_folds_eth_dots_and_hyphens() (+13 more)

### Community 15 - "test_edit_menu.py"
Cohesion: 0.10
Nodes (17): _edit_menu(), _editing_section(), main_window(), mock_services(), _OkCommand, _runtime_bindings(), test_actions_follow_the_new_stack_after_reset(), test_edit_menu_roles_and_standard_keys() (+9 more)

### Community 18 - "Start Here"
Cohesion: 0.06
Nodes (39): Annotation Guide, Annotation metadata fields, Morphological annotation, Automatic Backups, Local database backup files, Export Formatting, DOCX export, Export glossary (+31 more)

### Community 20 - "test_runtime_session_freeze.py"
Cohesion: 0.14
Nodes (13): Task 2: Count app_context.session loads, _accumulate(), _call_kind(), count_runtime_session_lookups(), _is_app_context_session_load(), _lookup_kind(), _record(), scan_runtime_session_lookups() (+5 more)

### Community 22 - "ProjectExporter"
Cohesion: 0.09
Nodes (5): ProjectExporter, ProjectExportPayload, _assert_no_row_ids(), _build_full_project(), TestProjectExporter

### Community 23 - "Task 3: Migrate the three writers to layers (atomic)"
Cohesion: 0.05
Nodes (14): F3 Highlight Layers Implementation Plan, File Structure, Review Focus, Self-Review, Task 3: Migrate the three writers to layers (atomic), Task 4: Edit mode, re-render and `reapply_search`, Task 5: Theme switching recomposes all layers, SearchHighlighter (+6 more)

### Community 24 - "TestBackupService"
Cohesion: 0.03
Nodes (5): Task 4: WAL-safe `restore_backup` that never prunes first (D3), _make_sqlite(), _read_value(), TestBackupService, partial()

### Community 28 - "MigrationMetadataService"
Cohesion: 0.05
Nodes (7): Task 5: The injected engine is authoritative, with foreign keys OFF (D8), run_migrations_online(), _run_with_connection(), MigrationMetadataService, ProjectFoldersMixin, RevisionVersionResolver, TestMigrationMetadataWriteGuards

### Community 32 - "check_napoleon_gate.py"
Cohesion: 0.12
Nodes (13): _check_file(), _constructor_has_args(), _first_doc_line(), _has_doc_comment(), _is_test_path(), _iter_class_attributes(), _iter_init_instance_attrs(), _iter_python_files() (+5 more)

### Community 33 - "TokenTable"
Cohesion: 0.03
Nodes (5): TokenTableModel, TokenTable, _prep_obj_case_cell_text(), TestTokenTable, TestTokenTableModel

### Community 35 - "AnnotationJson"
Cohesion: 0.09
Nodes (10): Copied Annotation as a Validated AnnotationJson Implementation Plan, Global Constraints, Review Focus, Task 1: Move `AnnotationJson` to `oeapp.models`, Task 2: `AppContext` holds a validated `AnnotationJson`, Task 3: Refuse and log an invalid copy, Task 4: Docs, help, final gates, AnnotationJson (+2 more)

### Community 36 - "test_migration_flow.py"
Cohesion: 0.08
Nodes (16): MigrationResult, _backups(), _failing_apply(), apply(), flow(), _set(), _succeeding_apply(), apply() (+8 more)

### Community 37 - "OldEnglishTextEdit"
Cohesion: 0.03
Nodes (6): Task 2: Editor owns the layers (API + capability flag), FullProjectOldEnglishTextEdit, HighlightLayer, OldEnglishTextEdit, TestEditorLayerApi, TestOldEnglishTextEditInternal

### Community 39 - "Paragraph"
Cohesion: 0.07
Nodes (11): Chapter, Paragraph, test_chapter_model(), test_hierarchy_relationships(), test_paragraph_model(), test_section_model(), _run_migration(), TestHyphenatedWordMigration (+3 more)

### Community 40 - "import_export_schema.py"
Cohesion: 0.13
Nodes (8): ChapterJson, NoteJson, ParagraphJson, ParagraphRefJson, ProjectJson, RememberedAnnotationJson, SectionJson, SentenceJson

### Community 43 - "UnknownDatabaseRevision"
Cohesion: 0.08
Nodes (25): File Structure, Global Constraints, Migration and Backup Consolidation Implementation Plan, Review Focus, Task 0: Branch and baseline, Task 10: Startup handles `UnknownDatabaseRevision` (D6), Task 11: User-facing documentation (D6b), Task 12: Full verification and close-out (+17 more)

### Community 44 - "LogViewerDialog"
Cohesion: 0.14
Nodes (5): LogViewerDialog, test_log_viewer_dialog_filtering(), test_log_viewer_dialog_initial_load(), test_log_viewer_export(), test_log_viewer_local_time()

### Community 45 - "MigrationService"
Cohesion: 0.05
Nodes (5): Task 7: New `migrate()` flow (D1, D2a stamping, D4, D5), Task 8: Unknown database revision and version resolution (D6), MigrationFailed, MigrationService, TestMigrationFailed

### Community 47 - "AbstractPartOfSpeechRenderer"
Cohesion: 0.11
Nodes (11): Task 4: Sidebar renders from the catalog, AbstractPartOfSpeechRenderer, AdjectiveRenderer, AdverbRenderer, ArticleRenderer, ConjunctionRenderer, InterjectionRenderer, NounRenderer (+3 more)

### Community 50 - "MigrationFailureDialog"
Cohesion: 0.08
Nodes (3): MigrationFailureDialog, TestHonestRestoreText, TestMigrationFailureDialog

### Community 52 - "CommandLocators"
Cohesion: 0.04
Nodes (7): CommandLocators, _note_locators(), UpdateNoteCommand, TestAddNoteCommand, TestDeleteNoteCommand, TestUpdateNoteCommand, test_update_note_records_its_sentence_and_tokens()

### Community 54 - "ProjectImporter"
Cohesion: 0.08
Nodes (3): Task 2: Import rejects reading-text files, ProjectImporter, TestProjectImporter

### Community 58 - "HighlightLayers"
Cohesion: 0.11
Nodes (6): Task 1: `HighlightLayers` core (types, resolution, compose), HighlightEntry, HighlightLayers, HighlightStyle, selection_ranges(), TestHighlightLayers

### Community 60 - "annotation_modal.py"
Cohesion: 0.05
Nodes (16): Task 2: Annotation modal builds from the catalog, AnnotationFormState, AdjectiveFields, AdverbFields, ArticleFields, ConjunctionFields, InterjectionFields, NoneFields (+8 more)

### Community 63 - "UndoCommand"
Cohesion: 0.04
Nodes (18): File Structure, Global Constraints, Review Focus, Self-review, Spec coverage, Task 1: UndoCommand wrapper, Task 3: Plain undo names, Task 5: Translation undo is the application undo (+10 more)

### Community 64 - "HelpMenu"
Cohesion: 0.15
Nodes (3): HelpMenu, _non_separator_action_texts(), TestHelpMenu

### Community 66 - "RestoreDialog"
Cohesion: 0.05
Nodes (7): BackupsViewDialog, RestoreDialog, DateTimeTableWidgetItem, TestBackupsViewDialog, _dialog(), TestRestoreDialog, TestRestoreRefusalAndExit

### Community 67 - ".get_by_token"
Cohesion: 0.04
Nodes (25): F7 Annotation Apply and get_session Deletion Implementation Plan, File map, In, Out, Pre-existing gate failures, Self-review, Spec, Task 0: Record the gate baseline (+17 more)

### Community 68 - "main_window"
Cohesion: 0.12
Nodes (6): card(), main_window(), mock_services(), main_window(), main_window(), mock_services()

### Community 71 - "pdf_engine.py"
Cohesion: 0.11
Nodes (11): _bundle_has_required_index(), compile_latex_with_tectonic(), _normalize_platform(), PDFEngineError, resolve_tectonic_engine_paths(), TectonicEnginePaths, test_compile_omits_bundle_flags_when_bundle_missing(), test_compile_uses_bundle_and_offline_flags() (+3 more)

### Community 73 - "ToolsMenu"
Cohesion: 0.16
Nodes (3): ToolsMenu, show_dialog(), TestToolsMenu

### Community 75 - ".build"
Cohesion: 0.12
Nodes (3): AnnotationModalShortcuts, GlobalShortcuts, ShortcutsMixin

### Community 77 - "test_translation_undo_keys.py"
Cohesion: 0.35
Nodes (7): _no_reload(), _press(), test_apply_translation_does_not_push(), test_undo_key_elsewhere_runs_application_undo(), test_undo_key_in_oe_edit_mode_is_character_undo(), test_undo_key_in_translation_editor_is_application_undo(), _type()

### Community 80 - "Section"
Cohesion: 0.05
Nodes (13): Section, _build_section_with_paragraphs(), test_merge_section_command_execute_and_undo(), test_merge_section_command_fails_when_paragraph_not_section_start(), test_split_and_merge_chapter_commands_execute_and_undo(), test_split_chapter_command_fails_for_first_section(), test_split_section_command_execute_and_undo(), test_split_section_command_fails_for_first_paragraph() (+5 more)

### Community 81 - "_actions"
Cohesion: 0.09
Nodes (5): _actions(), _select_card(), TestCopyAnnotation, TestCopyPasteIntegration, TestPasteAnnotation

### Community 82 - "fixture"
Cohesion: 0.15
Nodes (6): isolate_qsettings(), isolated_qsettings(), mock_migration_services(), qapp(), sample_project(), sample_sentence()

### Community 83 - "build_help.py"
Cohesion: 0.12
Nodes (10): build_qhcp(), build_qhp(), first_heading(), keyword_id(), main(), parse_args(), render_html_page(), render_index_page() (+2 more)

### Community 85 - "7cd945e38aff_repair_declension_and_verb_class_codes.py"
Cohesion: 0.20
Nodes (11): _add_preset_checks(), _check_constraint_exists(), _column_exists(), downgrade(), _in_list(), _inspector(), _normalise(), _repair() (+3 more)

### Community 87 - "EditProjectDialog"
Cohesion: 0.13
Nodes (3): EditProjectDialog, test_edit_project_leaves_history(), TestEditProjectDialog

### Community 90 - "Token"
Cohesion: 0.03
Nodes (6): TokenOccurrenceMixin, Token, test_get_by_token_reads_the_session_it_is_given(), TestTokenOccurrenceMixin, TestCreateFromSentence, TestUpdateFromSentence

### Community 91 - "AnnotateTokenCommand"
Cohesion: 0.04
Nodes (7): Task 1: Fold idiom creation into `AnnotateTokenCommand`, Task 8: Stack entries follow the sentence and the token, StackAdjustment, AnnotateTokenCommand, _moved_sentence(), _token_ids(), TestUndoStackCommands

### Community 92 - "apply_theme"
Cohesion: 0.22
Nodes (3): apply_theme(), resolve_theme_name(), TestApplyTheme

### Community 93 - "AppContext"
Cohesion: 0.06
Nodes (5): Global Constraints, clear_runtime_session(), set_runtime_session(), AppContext, db_session()

### Community 95 - ".test_line_initial_token_can_be_remembered_from_context_menu"
Cohesion: 0.09
Nodes (3): TestAnnotationPropagationMenu, text(), __init__()

### Community 96 - "test_migration_pos_codes.py"
Cohesion: 0.17
Nodes (13): Self-Review, Task 5: Data migration and preset CHECK constraints, _check_names(), _column(), engine(), _load(), test_checks_added_and_existing_check_kept_when_clean(), test_labels_become_codes_in_presets_and_annotations() (+5 more)

### Community 98 - "d6d8b613bc53_annotation_verb_metadata_and_normalized_.py"
Cohesion: 0.11
Nodes (14): _backfill_annotation_roots(), _column_exists(), downgrade(), _normalize_old_english(), _table_exists(), upgrade(), _backfill_annotations(), _backfill_tokens() (+6 more)

### Community 99 - "ensure_runtime_help_assets"
Cohesion: 0.16
Nodes (7): ensure_runtime_help_assets(), HelpPaths, resolve_help_paths(), _bundle_dir(), test_ensure_runtime_help_assets_copies_qch_and_qhc(), test_ensure_runtime_help_assets_raises_when_bundled_artifacts_missing(), test_resolve_help_paths_uses_resource_and_app_data_locations()

### Community 100 - "TokenDetailsSidebar"
Cohesion: 0.10
Nodes (4): TokenDetailsSidebar, TestTokenDetailsSidebar, collect_labels(), collect_labels()

### Community 101 - "_check_function_doc"
Cohesion: 0.33
Nodes (4): _check_function_doc(), _function_has_args(), _function_has_keyword_args(), _function_uses_return_or_yield()

### Community 102 - "TestEditModeAndRerender"
Cohesion: 0.07
Nodes (7): Global Constraints, normalized_oe_query(), annotate_pos(), card(), TestEditModeAndRerender, TestSearchBeforeFirstRender, token_ids()

### Community 105 - "ADR NNNN: <short, decision-oriented title>"
Cohesion: 0.29
Nodes (6): ADR NNNN: <short, decision-oriented title>, Alternatives considered, Consequences, Context, Decision, Related

### Community 108 - "test_undo_navigation.py"
Cohesion: 0.24
Nodes (11): blink_translation(), _card(), _in_view(), test_blink_translation_restores_style_without_push(), test_chapter_change_focuses_first_old_english_editor(), test_redo_after_chapter_change_returns_to_sentence(), test_section_change_focuses_first_old_english_editor(), test_undo_after_section_change_returns_to_sentence() (+3 more)

### Community 109 - "Sentence"
Cohesion: 0.03
Nodes (11): Note, Sentence, NoteDialog, FullProjectNotesArea, TestNoteDialog, TestClickableNoteLabel, TestNotesPanel, on_clicked() (+3 more)

### Community 114 - "AnnotationPropagationService"
Cohesion: 0.12
Nodes (3): AnnotationPropagationPlan, AnnotationPropagationService, TestAnnotationPropagationService

### Community 117 - "EditSentenceCommand"
Cohesion: 0.12
Nodes (5): EditSentenceCommand, _idiom_ids(), test_needs_full_reload_by_field(), test_failed_translation_write_does_not_merge_into_open_run(), _edit()

### Community 118 - "MainMenu"
Cohesion: 0.10
Nodes (6): HelpTopic, FileMenu, MainMenu, PreferencesMenu, TestFileMenu, TestPreferencesMenu

### Community 119 - "PresetPartOfSpeechFieldsBase"
Cohesion: 0.10
Nodes (13): Task 3: Preset dialog builds from the catalog; presets store codes, PresetPartOfSpeechFieldsBase, PresetPosFormManager, PosField, _build(), test_boolean_and_blank_semantics_survive(), test_declension_and_verb_class_have_no_clear_choice(), test_declension_extracts_the_code_not_the_label() (+5 more)

### Community 120 - "read_text"
Cohesion: 0.18
Nodes (6): read_text(), test_macos_build_verifies_tectonic_assets(), test_make_dmg_uses_single_applications_link_strategy(), test_spec_includes_alembic_runtime_assets(), test_spec_includes_tectonic_assets(), test_windows_build_verifies_tectonic_assets()

### Community 121 - "test_state.py"
Cohesion: 0.08
Nodes (9): context(), FlakyCommand, OkCommand, test_failed_redo_drops_command(), test_failed_undo_keeps_command_undoable(), test_project_change_and_close_clear_history(), test_same_project_id_keeps_history(), test_undo_limit_is_50() (+1 more)

### Community 125 - "AutosaveService"
Cohesion: 0.08
Nodes (8): AutosaveService, disable_autosave_by_default(), test_autosave_can_be_enabled_per_test(), test_autosave_disabled_by_default(), test_project_updated_at_on_annotation_update(), test_project_updated_at_on_sentence_delete(), test_project_updated_at_on_sentence_update(), test_project_updated_at_on_token_update()

### Community 127 - "SentenceCardController"
Cohesion: 0.07
Nodes (5): F4: Finish SentenceCard Controller Split; Stop Widget ORM Writes — Implementation Plan, Self-Review Notes, Task 2: Move hierarchy dispatch and position query into `SentenceCardController`, Task 3: Rewire `SentenceCard` — require `command_manager`, delete ORM-direct writes, add `structure_changed`, SentenceCardController

### Community 129 - "prepare_tectonic_assets.py"
Cohesion: 0.20
Nodes (6): build_manifest(), copy_binary(), copy_bundle(), file_sha256(), main(), parse_args()

### Community 132 - "Sentence Notes"
Cohesion: 0.18
Nodes (13): Preterite-Present Requires Infinitive Shortcut, Export Formatting, PDF Glossary, PDF Export, Sentence Notes as PDF Footnotes, Full Translation Window, LaTeX PDF Layout Pipeline, Side-by-Side Full Translation View (+5 more)

### Community 136 - ".build"
Cohesion: 0.18
Nodes (3): Task 4: Edit menu and standard keys, WindowMenu, test_tools_menu_includes_remembered_annotation_actions()

### Community 137 - "test_search.py"
Cohesion: 0.09
Nodes (10): test_all_scope_combines_oe_mode_and_notes(), test_clear_restores_origin_mode_focus(), test_escape_clears_search_and_restores_origin_mode_focus(), test_mode_scope_only_searches_modern_english(), test_notes_scope_combines_notes_and_normalized_oe(), test_project_search_matches_respects_scope_and_order(), test_search_navigation_loads_other_chapter_and_focuses_mode_field(), test_search_oe_uses_normalized_token_and_root_matching() (+2 more)

### Community 138 - "Start Here"
Cohesion: 0.21
Nodes (13): Annotation Guide, Automatic Backups, Export Formatting, Idioms Guide, Incremental Annotation, Help Index Redirect, Keyboard Shortcuts, Notes Guide (+5 more)

### Community 139 - "Morphological Annotation"
Cohesion: 0.22
Nodes (10): Annotation Modal, Morphological Annotation, POS Keyboard Shortcuts, Idiom, Idiom Range Selection, Incremental Annotation, Morphological Tag Reference, Old English Morphological Tags (+2 more)

### Community 140 - "sqlalchemy"
Cohesion: 0.03
Nodes (29): upgrade(), upgrade(), downgrade(), downgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+21 more)

### Community 142 - "verify_tectonic_assets.py"
Cohesion: 0.13
Nodes (8): build_macos.sh script, _sha256(), _sync_file(), file_sha256(), main(), parse_args(), verify_manifest(), verify_required_layout()

### Community 145 - "Annotation"
Cohesion: 0.05
Nodes (36): Agent Tooling and Quality Contract, Alembic Desktop Migrations, Fat ORM Models, In-App Help Engine, oeapp Layered Architecture, Napoleon Documentation Contract, PySide6 UI Layer, Services as UI–Model Bridge (+28 more)

### Community 147 - "71b9d6456d8b_add_sqlite_performance_indexes.py"
Cohesion: 0.27
Nodes (6): _create_index_if_missing(), downgrade(), _drop_index_if_exists(), _index_exists(), _table_exists(), upgrade()

### Community 149 - "File Structure"
Cohesion: 0.29
Nodes (6): File Structure, Review Focus, Runtime Session Freeze Implementation Plan, Task 1: Count the six call names, Task 3: Allowlist the oeapp tree, Task 4: Point ADR 0011 at the test

### Community 150 - "_apply_message"
Cohesion: 0.33
Nodes (3): _apply_message(), _count_line(), _skipped_line()

### Community 151 - "AnnotationLookupsMixin"
Cohesion: 0.03
Nodes (14): CaseFilterDialog, NumberFilterDialog, PartOfSpeechFilterDialog, SentenceFilterDialog, CaseHighlighterCommand, HighlighterCommandBase, IdiomHighlighterCommand, NoneHighlighterCommand (+6 more)

### Community 154 - "create_engine_with_path"
Cohesion: 0.06
Nodes (22): Task 1: 1.0.0 baseline fixture and schema-drift test (D7), create_engine_with_path(), build_baseline_db(), build_create_all_db(), schema_snapshot(), _alembic_config(), _fetch_indexes(), TestMigrationUpgradeIndexes (+14 more)

### Community 155 - "MainWindow"
Cohesion: 0.04
Nodes (10): HelpEngineError, MainWindow, TokenTableColumn, create_test_token(), test_remembered_annotations_markdown_exists(), test_search_guide_markdown_exists(), main_window(), test_migration_failure_writes_last_working_version_only_when_restored() (+2 more)

### Community 156 - "MockMainWindow"
Cohesion: 0.11
Nodes (3): mock_main_window(), MockMainWindow, _MockProjectUI

### Community 159 - "test_migration_backup_restore.py"
Cohesion: 0.08
Nodes (6): InMemoryMigrationMetadataService, migration_service_with_temp_db(), temp_db_engine(), temp_db_path(), TestFreshDatabaseStamp, TestHasPendingMigrations

### Community 162 - "Annotation Modal"
Cohesion: 0.22
Nodes (8): Annotation Modal, POS Keyboard Shortcuts, Idiom Annotation Unit, Last-Used POS Field Memory, Annotation Keyboard Shortcuts, J K Sentence Navigation, Sentence Cards, Token Table

### Community 163 - "Ænglisc Toolkit"
Cohesion: 0.29
Nodes (5): J/K Sentence Navigation, Ænglisc Toolkit, Autosave, SQLite WAL Database Locking, Troubleshooting

### Community 170 - "Scheduled Project Database Backup"
Cohesion: 0.29
Nodes (8): Automatic Backups, Backups Folder, Pre-Migration Backup, Scheduled Project Database Backup, Backup Now, Backup Settings, Settings, Application Theme

### Community 171 - "DOCX Export"
Cohesion: 0.25
Nodes (8): DOCX Export, Annotation Alternatives, Compact DOCX Annotation Format, JSON Project Export, JSON Project Import, Export Migration Version, Project Export/Import, python-docx Dependency

### Community 172 - "schema_1_0_0.sql"
Cohesion: 0.17
Nodes (23): alembic_version, annotation_presets, annotations, chapters, idioms, idx_annotations_idiom_id, idx_annotations_token_id, idx_chapters_project_number (+15 more)

### Community 174 - "visible_titles"
Cohesion: 0.17
Nodes (8): File map, Global Constraints, Project Export Reading-Text Implementation Plan, Spec coverage (self-review), Task 1: `ReadingTextExporter` (strings only), Task 4: Help copy for the three Project Export items, visible_titles(), _indent_multiline_plain()

### Community 178 - "read_alembic_revision"
Cohesion: 0.09
Nodes (5): Task 2: Single `alembic_version` reader (D10), read_alembic_revision(), run_pragma_optimize(), TestReadAlembicRevision, TestSQLitePragmas

### Community 179 - "Elderly Scholar (Tolkien-like)"
Cohesion: 0.48
Nodes (7): Circular Storybook Logo Badge, Green Goblin or Orc Companion, Library Bookshelves, Shared Open Book, Elderly Scholar (Tolkien-like), Shared Reading and Storytelling, Warm Storybook Illustration Style

### Community 180 - "Circular App Logo Icon"
Cohesion: 0.57
Nodes (6): Circular App Logo Icon, Library Bookshelves, Green Goblin Reader, Shared Open Book, Elderly Bespectacled Scholar, Human and Monster Shared Literacy

### Community 181 - "Circular App Icon"
Cohesion: 0.62
Nodes (7): Cartoon Icon Style, Circular App Icon, Elderly Scholar, Green Creature, Library Bookshelf, Open Book, Shared Reading

### Community 182 - "Aenglisc Toolkit 512px icon"
Cohesion: 0.57
Nodes (6): Aenglisc Toolkit 512px icon, Circular badge crop on black, Green goblin-like reader, Library bookshelves, Elderly Tolkien-like scholar, Shared open book

### Community 183 - "Circular Library Reading Logo"
Cohesion: 0.67
Nodes (7): Circular Dark Brown Frame, Circular Library Reading Logo, Elderly Tolkien-like Reader, Goblinoid Book Companion, Library Bookshelves, Open Book, Shared Reading Scene

### Community 184 - "Aenglisc Toolkit circular logo"
Cohesion: 0.57
Nodes (6): Aenglisc Toolkit circular logo, Circular badge crop on black, Green goblin-like reader, Library bookshelves, Elderly Tolkien-like scholar, Shared open book

### Community 187 - "JSON Project Export"
Cohesion: 0.29
Nodes (6): Backup Database and Metadata Files, Scheduled Background Backup, JSON Project Export, JSON Project Import, Export Migration Version Compatibility, Backup Preference Settings

### Community 188 - "Aenglisc Toolkit"
Cohesion: 0.33
Nodes (4): Aenglisc Toolkit, Local SQLite Project Storage, 500ms Autosave, SQLite WAL Database Lock

### Community 194 - "test_pos_code_repair.py"
Cohesion: 0.29
Nodes (10): _importer(), _migration(), _repairers(), _revision(), test_json_tables_equal_the_frozen_migration_tables(), test_malformed_values_section_raises_and_is_not_swallowed(), test_old_export_label_values_import_as_codes(), test_rename_mappings_still_work_alongside_values() (+2 more)

### Community 196 - "_sqlite_pragma_settings"
Cohesion: 0.29
Nodes (4): set_sqlite_pragma(), _parse_env_choice(), _parse_env_int(), _sqlite_pragma_settings()

### Community 199 - "build_macos_helpbook.py"
Cohesion: 0.16
Nodes (7): _build_help_index(), _copy_html_pages(), main(), parse_args(), _prepare_output_directory(), _validate_source_html(), _write_helpbook_info_plist()

### Community 201 - "Circular App Icon"
Cohesion: 0.67
Nodes (6): Circular App Icon, Elderly Scholar, Green Goblin Creature, Library Bookshelves, Open Book, Scholarship and Fantasy

### Community 202 - "Circular Earth-Tone Emblem"
Cohesion: 0.40
Nodes (6): Solid Black Background, Circular Earth-Tone Emblem, Dark Brown Right Region, Possible Helmeted Profile Motif, Light Tan Left Region, 16x16 macOS Iconset Logo

### Community 203 - "Circular Logo Illustration"
Cohesion: 0.60
Nodes (6): 256px App Icon, Circular Logo Illustration, Library Bookshelves, Open Book, Green Orc or Goblin, Elderly Scholar in Suit

### Community 204 - "Circular App Logo Icon 32x32@2x"
Cohesion: 0.60
Nodes (6): Circular App Logo Icon 32x32@2x, Thick Black Circular Border, Gollum-like Creature, Library Bookshelves Background, Shared Open Book, Elderly Scholar Figure (Tolkien-like)

### Community 205 - "32x32 Circular App Icon"
Cohesion: 0.60
Nodes (6): 32x32 Circular App Icon, Circular Frame, Folklore Companionship, Green Creature Over Shoulder, Open Book, Bespectacled Scholar

### Community 206 - "Elderly Scholar in Glasses and Suit"
Cohesion: 0.73
Nodes (6): Circular App Logo Illustration, Green Goblin-like Creature, Library Bookshelves, Open Hardcover Book, Elderly Scholar in Glasses and Suit, Shared Reading Scene

### Community 208 - "Sentence Word-Range Notes"
Cohesion: 0.33
Nodes (5): Annotation Metadata Fields, Root and Surface Form Normalization, Sentence Word-Range Notes, OE Search Normalization, Search Scope Modes

### Community 209 - "DOCX Export"
Cohesion: 0.33
Nodes (6): DOCX Compact Annotation Format, DOCX Export, Annotation Alternatives, Morphological Tag Reference, Old English Morphological Tag Codes, python-docx Dependency

### Community 210 - "Start Here"
Cohesion: 0.43
Nodes (8): Annotation Guide, Idioms Guide, Annotation Keyboard Shortcuts, Keyboard Shortcuts, Notes Guide, Remembered Annotations, Search Guide, Start Here

### Community 211 - "Annotation Metadata Fields"
Cohesion: 0.33
Nodes (6): Annotation Metadata Fields, Root and Surface Form Normalization, Annotation Confidence, Annotation TODO Markers, OE Search Normalization, Search Modes

### Community 213 - "TranslationUndoFilter"
Cohesion: 0.27
Nodes (3): TranslationUndoFilter, test_filter_claims_undo_and_redo_shortcut_override(), test_filter_only_on_modern_english_editor()

### Community 215 - "BackupFailed"
Cohesion: 0.07
Nodes (7): main(), BackupFailed, MigrationCreationFailed, FieldMappingService, MigrationCreationResult, TestBackupFailed, TestMigrationCreationFailed

### Community 216 - "FullTranslationWindow"
Cohesion: 0.03
Nodes (5): FullTranslationWindow, HorizontalSeparatorWidget, full_window(), TestFullTranslationWindow, fake_export()

### Community 219 - "AppendTextDialog"
Cohesion: 0.10
Nodes (5): Task 2: One project-scoped stack, AppendTextDialog, OkCommand, test_append_clears_history(), TestAppendTextDialog

### Community 224 - "ReadingTextExporter"
Cohesion: 0.24
Nodes (4): ReadingTextExporter, _mark_verse(), _require_n_sentences(), TestReadingTextExporter

### Community 225 - "Morphological Annotation"
Cohesion: 0.50
Nodes (3): Morphological Annotation, Export Glossary, Verb Metadata Flags

### Community 226 - "Reusable Token Annotation Template"
Cohesion: 0.40
Nodes (5): Last-Used POS Field Memory, Apply Remembered Annotations, Exact Surface-Text Matching, Project Scope Overrides Global, Reusable Token Annotation Template

### Community 231 - "Bespectacled Reader"
Cohesion: 1.00
Nodes (4): Bespectacled Reader, Circular App Icon, Green Lurking Creature, Open Book

### Community 233 - "PDF Export"
Cohesion: 0.50
Nodes (4): PDF Export, LaTeX PDF Layout Pipeline, Full Translation Window, Side-by-Side Translation View

### Community 234 - "TestModalBuildsFromCatalog"
Cohesion: 0.17
Nodes (3): TestModalBuildsFromCatalog, TestPartOfSpeechSubclasses, TestPOSFieldModelMapping

### Community 243 - "File Structure"
Cohesion: 0.13
Nodes (5): File Structure, Task 6: Import remaps label-form values from older exports, Task 7: Docs, help, ADR status and final verification, PosCodeRepair, test_from_mapping_rejects_malformed_specs()

### Community 256 - "AddSentenceCommand"
Cohesion: 0.10
Nodes (6): AddSentenceCommand, test_add_sentence_after_first_sentence_succeeds(), test_add_sentence_before_first_sentence_succeeds(), test_delete_sentence_recalculates(), test_merge_sentences_recalculates(), Setup

### Community 257 - "test_token_details_sidebar.py"
Cohesion: 0.26
Nodes (4): PronounRenderer, _label_texts(), _render(), TestSidebarRendersFromCatalog

### Community 260 - "POS Field Catalog (F2) Implementation Plan"
Cohesion: 0.50
Nodes (3): Global Constraints, POS Field Catalog (F2) Implementation Plan, Review Focus

### Community 264 - "get_logger"
Cohesion: 0.04
Nodes (13): get_project_db_path(), main(), touch_project_on_change(), configure_logging(), get_log_dir(), get_log_file_path(), get_logger(), create_application() (+5 more)

### Community 266 - "token_details_sidebar.py"
Cohesion: 0.16
Nodes (5): NoAnnotationAvailable, BaseTokenDetailsSidebar, FullTranslationSidebar, clear_layout(), open_bosworth_toller()

### Community 285 - "test_idiom_modal_navigation"
Cohesion: 0.19
Nodes (3): test_all_pos_fields_save_via_modal(), test_idiom_modal_navigation(), test_idiom_selection_ui()

### Community 305 - "SentenceCard"
Cohesion: 0.04
Nodes (14): HierarchyPosition, SentenceCard, _select_card(), _card_for(), test_token_selection_edge_cases(), mock_main_window(), test_get_hierarchy_position_chapter_start(), test_get_hierarchy_position_middle_of_paragraph() (+6 more)

### Community 314 - "push_command"
Cohesion: 0.08
Nodes (34): _is_obsolete(), is_orphaned(), maintain_stack(), settle(), push_command(), redo_step(), undo_step(), add_note() (+26 more)

## Ambiguous Edges - Review These
- `Keyboard Shortcuts` → `Editor Versus Project Undo Model`  [AMBIGUOUS]
  oeapp/help/macos/AengliscToolkit.help/Contents/Resources/en.lproj/keybindings.html · relation: conceptually_related_to
- `Root` → `Empty Differential Dict Fixture`  [AMBIGUOUS]
  tests/differential/data/test_dict.txt · relation: conceptually_related_to
- `Undo Model` → `Keyboard Shortcuts`  [AMBIGUOUS]
  oeapp/help/topics/keybindings.md · relation: conceptually_related_to
- `Keyboard shortcuts` → `Troubleshooting`  [AMBIGUOUS]
  oeapp/help/assets/troubleshooting.html · relation: conceptually_related_to
- `Possible Helmeted Profile Motif` → `Circular Earth-Tone Emblem`  [AMBIGUOUS]
  assets/logo.iconset/icon_16x16.png · relation: conceptually_related_to

## Knowledge Gaps
- **78 isolated node(s):** `aenglisc_toolkit`, `Preterite-Present Requires Infinitive Shortcut`, `LaTeX PDF Layout Pipeline`, `Side-by-Side Full Translation View`, `Automatic Note Renumbering` (+73 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3282 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **170 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `get_runtime_session()` connect `get_runtime_session` to `AddSentenceCommand`, `db.py`, `.get`, `sentence_separator_kind`, `Annotation`, `get_logger`, `.reload_project`, `Project`, `OpenProjectDialog`, `AnnotationPreset`, `Command`, `test_remembered_annotations.py`, `test_typed_run.py`, `NewProjectDialog`, `TestAnnotationPresetManagementDialog`, `.create`, `ProjectExporter`, `DeleteProjectDialog`, `MainWindow`, `TestSentenceCard`, `OldEnglishTextEdit`, `._reload_after_structure_change`, `AnnotationPresetManagementDialog`, `Paragraph`, `.from_annotation`, `RememberedAnnotationsDialog`, `.load_section`, `visible_titles`, `DOCXExporter`, `CommandLocators`, `push_command`, `BackupService`, `annotation_modal.py`, `ProjectMenu`, `UndoCommand`, `RestoreDialog`, `.get_by_token`, `load_projects_into_table`, `main_window`, `MainWindowActions`, `ImportProjectDialog`, `test_translation_undo_keys.py`, `Section`, `_actions`, `fixture`, `EditProjectDialog`, `FullTranslationWindow`, `.upsert_fields`, `Token`, `AnnotateTokenCommand`, `AppendTextDialog`, `AppContext`, `ReadingTextExporter`, `.perform_search`, `AnnotationPosFormManager`, `TestAnnotationEmptinessPredicates`, `.record_sentences`, `Sentence`, `test_undo_navigation.py`, `.export_side_by_side_pdf`, `AnnotationPropagationService`, `EditSentenceCommand`, `MainMenu`, `AutosaveService`, `SentenceCardController`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `get_runtime_session()` (e.g. with `Global Constraints` and `Out`) actually correct?**
  _`get_runtime_session()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `aenglisc_toolkit`, `Preterite-Present Requires Infinitive Shortcut`, `LaTeX PDF Layout Pipeline` to the rest of the system?**
  _78 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `db.py` be split into smaller, more focused modules?**
  _Cohesion score 0.04429794124450613 - nodes in this community are weakly interconnected._
- **Why does `Project` connect `Project` to `db.py`, `WyrdcraeftIngestService`, `sentence_separator_kind`, `Annotation`, `get_logger`, `.build`, `get_runtime_session`, `OpenProjectDialog`, `test_search.py`, `test_typed_run.py`, `._build_glossary_entries`, `NewProjectDialog`, `ProjectExporter`, `DeleteProjectDialog`, `.split_sentences`, `MainWindow`, `SearchController`, `OldEnglishTextEdit`, `Paragraph`, `.load_section`, `SearchResult`, `._render_two_columns`, `SentenceCard`, `DOCXExporter`, `ProjectImporter`, `push_command`, `BackupService`, `ProjectMenu`, `load_projects_into_table`, `main_window`, `TestFullTranslationPDFExporter`, `MainWindowActions`, `ProjectUI`, `test_translation_undo_keys.py`, `._render`, `Section`, `_actions`, `fixture`, `EditProjectDialog`, `FullTranslationWindow`, `Token`, `export_docx.py`, `AppendTextDialog`, `ReadingTextExporter`, `test_undo_navigation.py`, `Sentence`, `FullTranslationPDFExporter`, `MainMenu`?**
  _High betweenness centrality (0.093) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Keyboard Shortcuts` and `Editor Versus Project Undo Model`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Root` and `Empty Differential Dict Fixture`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
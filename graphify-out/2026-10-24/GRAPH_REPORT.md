# Graph Report - aenglisc_toolkit  (2026-10-24)

## Corpus Check
- 269 files · ~1,437,263 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 35 file(s) not represented in the graph (top: (none) 12, .ttf 5, .spec 2)

## Summary
- 6591 nodes · 14615 edges · 282 communities (104 shown, 178 thin omitted)
- Extraction: 88% EXTRACTED · 12% INFERRED · 0% AMBIGUOUS · INFERRED: 1734 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a1b87062`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Project
- WyrdcraeftIngestService
- AnnotationPreset
- AnnotationModal
- test_project_touch.py
- .from_json
- PosFieldCatalog
- DeleteProjectDialog
- TestProject
- create_test_project
- Messages
- AnnotationPresetService
- ProjectExporter
- Token
- AppContext
- typing
- Start Here
- AutosaveService
- .create
- MainWindowActions
- AnnotationPropagationService
- TestBackupService
- Sentence
- .split_sentences
- TestTokenize
- OldEnglishTextSelector
- TokenTableModel
- fixture
- SearchController
- check_napoleon_gate.py
- test_search.py
- Note
- test_migration_flow.py
- HighlightLayers
- .get
- .create_from_sentence
- import_export_schema.py
- Task 3: Migrate the three writers to layers (atomic)
- LogTableModel
- pytest
- LogViewerDialog
- AnnotateTokenCommand
- ProjectImporter
- token_details_sidebar.py
- HelpCenterDialog
- FullProjectModernEnglishTextEdit
- MigrationFailureDialog
- test_commands.py
- HelpEngine
- OldEnglishTextEdit
- TokenTable
- CommandManager
- BackupService
- ThemeMixin
- TestMainWindowInitialization
- NoteDialog
- sentence_separator_kind
- test_remembered_annotations.py
- BackupsViewDialog
- Annotation
- AnnotationPresetManagementDialog
- TestFullTranslationPDFExporter
- .create
- pdf_engine.py
- get_project_db_path
- NotesPanel
- shortcuts.py
- ImportProjectDialog
- TestHighlighting
- TokenOccurrenceMixin
- HelpTextBrowser
- TestSentenceFilters
- _actions
- build_help.py
- TestOldEnglishTextEdit
- 7cd945e38aff_repair_declension_and_verb_class_codes.py
- EditProjectDialog
- RestoreDialog
- Task 4: Wire `structure_changed` in `ProjectWorkspace`
- TestSentence
- apply_theme
- table_to_model_name
- .test_line_initial_token_can_be_remembered_from_context_menu
- test_migration_pos_codes.py
- MigrationService
- log_file
- help_paths.py
- AnnotationPosFormManager
- .export_side_by_side_pdf
- help_center_dialog.py
- ADR NNNN: <short, decision-oriented title>
- test_annotation.py
- AlreadyExists
- ._latex_escape
- d6d8b613bc53_annotation_verb_metadata_and_normalized_.py
- get_logger
- WholeSentenceHighlighter
- DOCXExporter
- TestModalBuildsFromCatalog
- test_settings_dialog.py
- pos_form_system.py
- read_text
- .render_idiom
- .build
- test_idiom_modal_navigation
- TestAnnotationModalLifecycle
- annotation_modal.py
- prepare_tectonic_assets.py
- MainWindow
- MockSentenceCard
- Sentence Notes
- test_main_window.py
- test_restore_dialog.py
- pathlib
- AnnotationFormState
- TestFromUtcIso
- Start Here
- Morphological Annotation
- sqlalchemy
- sys
- File Structure
- TestTokenize
- Annotation
- 71b9d6456d8b_add_sqlite_performance_indexes.py
- .get
- main_window.py
- NewProjectDialog
- Bundled Tectonic PDF Payload
- create_engine_with_path
- SearchResult
- _MockProjectUI
- MainMenu
- TestToUtcIso
- TestHasPendingMigrations
- _sqlite_pragma_settings
- Annotation Modal
- Ænglisc Toolkit
- TestGetLogoPixmap
- TestPartOfSpeechFieldsBase
- FullProjectOldEnglishTextEdit
- apply_theme Helper
- ._build_stanzas
- Scheduled Project Database Backup
- DOCX Export
- schema_1_0_0.sql
- FullTranslationPDFExporter
- SingleInstanceHighlighter
- HorizontalSeparatorWidget
- DateTimeTableWidgetItem
- .__init__
- Elderly Scholar (Tolkien-like)
- Circular App Logo Icon
- Circular App Icon
- Aenglisc Toolkit 512px icon
- Circular Library Reading Logo
- Aenglisc Toolkit circular logo
- _actions
- JSON Project Export
- Aenglisc Toolkit
- _apply_message
- .update_logs
- json
- TestResolveThemeName
- TestSettingsDialog
- build_macos_helpbook.py
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
- _legacy_verbose_export_size
- exc.py
- FullTranslationWindow
- AppendTextDialog
- Morphological Annotation
- Reusable Token Annotation Template
- test_all_pos_fields_save_via_modal
- Bespectacled Reader
- .save
- PDF Export
- TestSessionLocal
- TestBase
- SentenceCard
- TestRestoreDialog
- TestGetResourcePath
- NoAnnotationAvailable
- SettingsDialog
- _run_with_connection
- ProjectUI
- test_log_table_model
- check_help_rebuild.sh
- Chris Malek
- Contributor Covenant 3.0
- Narrow Qt App Context
- Usability Overhaul Ready Slices Plan
- Application Theme
- TestSentenceCard
- .root
- BaseTokenDetailsSidebar
- aenglisc_toolkit

## God Nodes (most connected - your core abstractions)
1. `create_test_project()` - 334 edges
2. `SentenceCard` - 187 edges
3. `Annotation` - 183 edges
4. `Project` - 183 edges
5. `Sentence` - 157 edges
6. `Token` - 150 edges
7. `create_test_sentence()` - 131 edges
8. `MainWindow` - 101 edges
9. `Note` - 99 edges
10. `CommandManager` - 93 edges

## Surprising Connections (you probably didn't know these)
- `F4: Finish SentenceCard Controller Split; Stop Widget ORM Writes — Implementation Plan` --references--> `Command`  [INFERRED]
  docs/superpowers/plans/2026-09-04-f4-sentence-card-controller-split.md → oeapp/commands/abstract.py
- `Global Constraints` --references--> `Command`  [INFERRED]
  docs/superpowers/plans/2026-09-04-f4-sentence-card-controller-split.md → oeapp/commands/abstract.py
- `F4: Finish SentenceCard Controller Split; Stop Widget ORM Writes — Implementation Plan` --references--> `AnnotateTokenCommand`  [INFERRED]
  docs/superpowers/plans/2026-09-04-f4-sentence-card-controller-split.md → oeapp/commands/annotation.py
- `Task 1: Fold idiom creation into `AnnotateTokenCommand`` --references--> `AnnotateTokenCommand`  [INFERRED]
  docs/superpowers/plans/2026-09-04-f4-sentence-card-controller-split.md → oeapp/commands/annotation.py
- `Global Constraints` --references--> `MergeSectionCommand`  [INFERRED]
  docs/superpowers/plans/2026-09-04-f4-sentence-card-controller-split.md → oeapp/commands/hierarchy.py

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

## Communities (282 total, 178 thin omitted)

### Community 0 - "Project"
Cohesion: 0.03
Nodes (28): MergeChapterCommand, MergeSectionCommand, SplitChapterCommand, Chapter, Paragraph, Project, Section, TestDOCXExporter (+20 more)

### Community 1 - "WyrdcraeftIngestService"
Cohesion: 0.08
Nodes (4): CanonicalRun, WyrdcraeftIngestService, test_ingest_mixed_creates_poem_chapter_and_prose_auto_titles(), test_ingest_pure_verse_chunks_sections_by_20_stanzas()

### Community 4 - "AnnotationModal"
Cohesion: 0.07
Nodes (3): AnnotationModal, TestAnnotationModal, __init__()

### Community 5 - "test_project_touch.py"
Cohesion: 0.14
Nodes (8): test_project_updated_at_on_annotation_update(), test_project_updated_at_on_note_create(), test_project_updated_at_on_note_delete(), test_project_updated_at_on_sentence_create(), test_project_updated_at_on_sentence_delete(), test_project_updated_at_on_sentence_update(), test_project_updated_at_on_token_update(), test_timestamps_are_utc()

### Community 6 - ".from_json"
Cohesion: 0.06
Nodes (6): sentence(), test_idiom_creation(), test_idiom_deletion_on_token_removal(), test_idiom_preservation_on_insertion_in_middle(), test_idiom_preservation_on_token_modification(), test_idiom_to_json_from_json()

### Community 7 - "PosFieldCatalog"
Cohesion: 0.16
Nodes (12): _PosEntry, PosFieldCatalog, _check_codes(), test_check_parser_finds_known_columns(), test_declension_and_verb_class_opt_out_of_clear(), test_every_attr_is_an_annotation_column(), test_field_less_and_unknown_pos_have_no_fields(), test_lookup_map_codes_match_check_constraints() (+4 more)

### Community 10 - "create_test_project"
Cohesion: 0.03
Nodes (13): Task 4b: Display helpers tolerate unrecognised codes, AnnotationTextualMixin, create_test_project(), create_test_sentence(), test_annotation_preserved_on_multiple_typo_fixes(), test_annotation_preserved_on_typo_fix(), test_annotation_shift_on_deletion(), test_annotation_shift_on_insertion() (+5 more)

### Community 13 - "ProjectExporter"
Cohesion: 0.10
Nodes (4): ProjectExporter, ProjectExportPayload, _assert_no_row_ids(), TestProjectExporter

### Community 16 - "AppContext"
Cohesion: 0.03
Nodes (13): Copied Annotation as a Validated AnnotationJson Implementation Plan, Global Constraints, Review Focus, Task 1: Move `AnnotationJson` to `oeapp.models`, Task 2: `AppContext` holds a validated `AnnotationJson`, Task 3: Refuse and log an invalid copy, Task 4: Docs, help, final gates, AnnotationJson (+5 more)

### Community 17 - "typing"
Cohesion: 0.04
Nodes (21): Base, clear_runtime_session(), get_runtime_session(), get_session(), _RuntimeState, set_runtime_session(), run_migrations_offline(), downgrade() (+13 more)

### Community 18 - "Start Here"
Cohesion: 0.06
Nodes (39): Annotation Guide, Annotation metadata fields, Morphological annotation, Automatic Backups, Local database backup files, Export Formatting, DOCX export, Export glossary (+31 more)

### Community 19 - "AutosaveService"
Cohesion: 0.06
Nodes (5): AutosaveService, disable_autosave_by_default(), test_autosave_can_be_enabled_per_test(), test_autosave_disabled_by_default(), TestAutosaveService

### Community 23 - "AnnotationPropagationService"
Cohesion: 0.13
Nodes (3): AnnotationPropagationPlan, AnnotationPropagationService, TestAnnotationPropagationService

### Community 24 - "TestBackupService"
Cohesion: 0.03
Nodes (5): Task 4: WAL-safe `restore_backup` that never prunes first (D3), _make_sqlite(), _read_value(), TestBackupService, partial()

### Community 25 - "Sentence"
Cohesion: 0.03
Nodes (14): Command, ApplyAnnotationPropagationCommand, ApplyRememberedAnnotationsCommand, AddSentenceCommand, DeleteSentenceCommand, EditSentenceCommand, MergeSentenceCommand, Idiom (+6 more)

### Community 30 - "fixture"
Cohesion: 0.11
Nodes (9): command_setup(), isolate_qsettings(), isolated_qsettings(), mock_main_window(), mock_migration_services(), project_and_sentence(), qapp(), sample_project() (+1 more)

### Community 32 - "check_napoleon_gate.py"
Cohesion: 0.08
Nodes (18): _check_file(), _check_function_doc(), _constructor_has_args(), _first_doc_line(), _function_has_args(), _function_has_keyword_args(), _function_uses_return_or_yield(), _has_doc_comment() (+10 more)

### Community 34 - "test_search.py"
Cohesion: 0.09
Nodes (10): test_all_scope_combines_oe_mode_and_notes(), test_clear_restores_origin_mode_focus(), test_escape_clears_search_and_restores_origin_mode_focus(), test_mode_scope_only_searches_modern_english(), test_notes_scope_combines_notes_and_normalized_oe(), test_project_search_matches_respects_scope_and_order(), test_search_navigation_loads_other_chapter_and_focuses_mode_field(), test_search_oe_uses_normalized_token_and_root_matching() (+2 more)

### Community 35 - "Note"
Cohesion: 0.04
Nodes (5): Note, FullProjectNotesArea, TestFullTranslationWindow, fake_export(), TestNote

### Community 36 - "test_migration_flow.py"
Cohesion: 0.07
Nodes (15): MigrationResult, InMemoryMigrationMetadataService, _backups(), _failing_apply(), apply(), flow(), _set(), _succeeding_apply() (+7 more)

### Community 37 - "HighlightLayers"
Cohesion: 0.07
Nodes (12): File Structure, Task 1: `HighlightLayers` core (types, resolution, compose), Task 2: Editor owns the layers (API + capability flag), Task 5: Theme switching recomposes all layers, HighlightEntry, HighlightLayer, HighlightLayers, HighlightStyle (+4 more)

### Community 38 - ".get"
Cohesion: 0.09
Nodes (10): MergeParagraphCommand, SplitParagraphCommand, TestSplitParagraphCommand, _create_three_sentences_single_paragraph(), test_merge_paragraph_command_execute_and_undo(), test_merge_paragraph_command_fails_when_first_paragraph(), test_merge_paragraph_command_fails_when_sentence_not_paragraph_start(), test_split_paragraph_command_execute_and_undo() (+2 more)

### Community 40 - "import_export_schema.py"
Cohesion: 0.10
Nodes (8): ChapterJson, NoteJson, ParagraphJson, ParagraphRefJson, ProjectJson, RememberedAnnotationJson, SectionJson, SentenceJson

### Community 41 - "Task 3: Migrate the three writers to layers (atomic)"
Cohesion: 0.03
Nodes (18): F3 Highlight Layers Implementation Plan, Global Constraints, Review Focus, Self-Review, Task 3: Migrate the three writers to layers (atomic), SearchHighlighter, normalized_oe_query(), annotate_pos() (+10 more)

### Community 43 - "pytest"
Cohesion: 0.09
Nodes (19): Task 10: Startup handles `UnknownDatabaseRevision` (D6), Task 6: Delete skip/abort and dead code (D9, D10), UnknownDatabaseRevision, describe_unknown_revision(), UnknownRevisionDialog, test_migration_failure_writes_last_working_version_only_when_restored(), test_unknown_revision_shows_the_dialog_then_exits(), test_dialog_builds_with_the_message() (+11 more)

### Community 44 - "LogViewerDialog"
Cohesion: 0.15
Nodes (5): LogViewerDialog, test_log_viewer_dialog_filtering(), test_log_viewer_dialog_initial_load(), test_log_viewer_export(), test_log_viewer_local_time()

### Community 46 - "ProjectImporter"
Cohesion: 0.07
Nodes (4): Task 2: Import rejects reading-text files, ProjectImporter, _build_full_project(), TestProjectImporter

### Community 47 - "token_details_sidebar.py"
Cohesion: 0.12
Nodes (12): Task 4: Sidebar renders from the catalog, AbstractPartOfSpeechRenderer, AdjectiveRenderer, AdverbRenderer, ArticleRenderer, ConjunctionRenderer, InterjectionRenderer, NounRenderer (+4 more)

### Community 50 - "MigrationFailureDialog"
Cohesion: 0.08
Nodes (3): MigrationFailureDialog, TestHonestRestoreText, TestMigrationFailureDialog

### Community 52 - "test_commands.py"
Cohesion: 0.05
Nodes (6): AddNoteCommand, DeleteNoteCommand, UpdateNoteCommand, TestAddNoteCommand, TestDeleteNoteCommand, TestUpdateNoteCommand

### Community 55 - "TokenTable"
Cohesion: 0.04
Nodes (5): AnnotationTableWidget, TokenTable, _prep_obj_case_cell_text(), TestAnnotationTableWidget, TestTokenTable

### Community 56 - "CommandManager"
Cohesion: 0.03
Nodes (23): F4: Finish SentenceCard Controller Split; Stop Widget ORM Writes — Implementation Plan, Global Constraints, Self-Review Notes, Task 1: Fold idiom creation into `AnnotateTokenCommand`, Task 2: Move hierarchy dispatch and position query into `SentenceCardController`, Task 3: Rewire `SentenceCard` — require `command_manager`, delete ORM-direct writes, add `structure_changed`, Task 5: Add `command_manager` to every remaining bare `SentenceCard(...)` test call site, CommandManager (+15 more)

### Community 64 - "sentence_separator_kind"
Cohesion: 0.06
Nodes (14): File map, Global Constraints, Project Export Reading-Text Implementation Plan, Spec coverage (self-review), Task 1: `ReadingTextExporter` (strings only), Task 4: Help copy for the three Project Export items, is_paragraph_start(), latex_separator() (+6 more)

### Community 65 - "test_remembered_annotations.py"
Cohesion: 0.09
Nodes (13): AmbiguousRememberedSpellingError, RememberedAnnotationApplyPlan, RememberedAnnotationService, _sorted_tokens(), test_apply_folds_eth_dots_and_hyphens(), test_apply_matches_partial_spelling_and_keeps_length_marks(), test_apply_remembered_annotations_exact_match_precedence_and_undo(), test_apply_remembered_annotations_reports_noop_states() (+5 more)

### Community 67 - "Annotation"
Cohesion: 0.03
Nodes (9): Annotation, TokenDetailsSidebar, TestAnnotationFromAnnotation, _label_texts(), _render(), TestSidebarRendersFromCatalog, TestTokenDetailsSidebar, collect_labels() (+1 more)

### Community 68 - "AnnotationPresetManagementDialog"
Cohesion: 0.04
Nodes (3): AnnotationPresetManagementDialog, _field(), TestAnnotationPresetManagementDialog

### Community 70 - ".create"
Cohesion: 0.06
Nodes (5): ReadingTextExporter, _mark_verse(), _require_n_sentences(), TestReadingTextExporter, full_window()

### Community 71 - "pdf_engine.py"
Cohesion: 0.10
Nodes (12): _bundle_has_required_index(), compile_latex_with_tectonic(), _normalize_platform(), PDFEngineError, resolve_tectonic_engine_paths(), TectonicEnginePaths, get_resource_path(), test_compile_omits_bundle_flags_when_bundle_missing() (+4 more)

### Community 74 - "NotesPanel"
Cohesion: 0.04
Nodes (6): ClickableNoteLabel, NotesPanel, _card_for(), TestClickableNoteLabel, TestNotesPanel, on_clicked()

### Community 75 - "shortcuts.py"
Cohesion: 0.14
Nodes (3): AnnotationModalShortcuts, GlobalShortcuts, ShortcutsMixin

### Community 81 - "_actions"
Cohesion: 0.09
Nodes (5): _actions(), _select_card(), TestCopyAnnotation, TestCopyPasteIntegration, TestPasteAnnotation

### Community 83 - "build_help.py"
Cohesion: 0.12
Nodes (10): build_qhcp(), build_qhp(), first_heading(), keyword_id(), main(), parse_args(), render_html_page(), render_index_page() (+2 more)

### Community 84 - "TestOldEnglishTextEdit"
Cohesion: 0.05
Nodes (3): _focus_new_card(), TestOldEnglishTextEdit, TestTokenSelector

### Community 85 - "7cd945e38aff_repair_declension_and_verb_class_codes.py"
Cohesion: 0.20
Nodes (11): _add_preset_checks(), _check_constraint_exists(), _column_exists(), downgrade(), _in_list(), _inspector(), _normalise(), _repair() (+3 more)

### Community 92 - "apply_theme"
Cohesion: 0.22
Nodes (3): apply_theme(), resolve_theme_name(), TestApplyTheme

### Community 96 - "test_migration_pos_codes.py"
Cohesion: 0.17
Nodes (13): Self-Review, Task 5: Data migration and preset CHECK constraints, _check_names(), _column(), engine(), _load(), test_checks_added_and_existing_check_kept_when_clean(), test_labels_become_codes_in_presets_and_annotations() (+5 more)

### Community 97 - "MigrationService"
Cohesion: 0.04
Nodes (15): File Structure, Global Constraints, Migration and Backup Consolidation Implementation Plan, Review Focus, Task 0: Branch and baseline, Task 11: User-facing documentation (D6b), Task 12: Full verification and close-out, Task 5: The injected engine is authoritative, with foreign keys OFF (D8) (+7 more)

### Community 99 - "help_paths.py"
Cohesion: 0.09
Nodes (12): ensure_runtime_help_assets(), HelpPaths, resolve_help_paths(), _sha256(), _sync_file(), get_app_data_path(), _bundle_dir(), test_ensure_runtime_help_assets_copies_qch_and_qhc() (+4 more)

### Community 105 - "ADR NNNN: <short, decision-oriented title>"
Cohesion: 0.29
Nodes (6): ADR NNNN: <short, decision-oriented title>, Alternatives considered, Consequences, Context, Decision, Related

### Community 111 - "d6d8b613bc53_annotation_verb_metadata_and_normalized_.py"
Cohesion: 0.11
Nodes (14): _backfill_annotation_roots(), _column_exists(), downgrade(), _normalize_old_english(), _table_exists(), upgrade(), _backfill_annotations(), _backfill_tokens() (+6 more)

### Community 113 - "get_logger"
Cohesion: 0.07
Nodes (10): main(), touch_project_on_change(), configure_logging(), get_log_dir(), get_log_file_path(), get_logger(), create_application(), temp_log_dir() (+2 more)

### Community 119 - "pos_form_system.py"
Cohesion: 0.07
Nodes (13): Task 3: Preset dialog builds from the catalog; presets store codes, PresetPartOfSpeechFieldsBase, PresetPosFormManager, PosField, _build(), test_boolean_and_blank_semantics_survive(), test_declension_and_verb_class_have_no_clear_choice(), test_declension_extracts_the_code_not_the_label() (+5 more)

### Community 120 - "read_text"
Cohesion: 0.18
Nodes (6): read_text(), test_macos_build_verifies_tectonic_assets(), test_make_dmg_uses_single_applications_link_strategy(), test_spec_includes_alembic_runtime_assets(), test_spec_includes_tectonic_assets(), test_windows_build_verifies_tectonic_assets()

### Community 128 - "annotation_modal.py"
Cohesion: 0.05
Nodes (14): Task 2: Annotation modal builds from the catalog, AdjectiveFields, AdverbFields, ArticleFields, ConjunctionFields, InterjectionFields, NoneFields, NounFields (+6 more)

### Community 129 - "prepare_tectonic_assets.py"
Cohesion: 0.20
Nodes (6): build_manifest(), copy_binary(), copy_bundle(), file_sha256(), main(), parse_args()

### Community 130 - "MainWindow"
Cohesion: 0.03
Nodes (4): MainWindow, on_key_pressed(), TestMainWindowOptimizeHooks, TestTokenSelectionRobustness

### Community 132 - "Sentence Notes"
Cohesion: 0.18
Nodes (13): Preterite-Present Requires Infinitive Shortcut, Export Formatting, PDF Glossary, PDF Export, Sentence Notes as PDF Footnotes, Full Translation Window, LaTeX PDF Layout Pipeline, Side-by-Side Full Translation View (+5 more)

### Community 133 - "test_main_window.py"
Cohesion: 0.04
Nodes (9): main_window(), mock_services(), TestEmptyStateStyling, TestMainWindowActions, TestMainWindowHelp, TestMainWindowStartupDialogs, TestNavigationButtonAffordances, TestSidebarResizing (+1 more)

### Community 135 - "pathlib"
Cohesion: 0.03
Nodes (12): MigrationMetadataService, ProjectFoldersMixin, RevisionVersionResolver, _alembic_config(), _fetch_indexes(), TestFreshSchemaIndexes, TestMigrationUpgradeIndexes, migration_service_with_temp_db() (+4 more)

### Community 138 - "Start Here"
Cohesion: 0.21
Nodes (13): Annotation Guide, Automatic Backups, Export Formatting, Idioms Guide, Incremental Annotation, Help Index Redirect, Keyboard Shortcuts, Notes Guide (+5 more)

### Community 139 - "Morphological Annotation"
Cohesion: 0.22
Nodes (10): Annotation Modal, Morphological Annotation, POS Keyboard Shortcuts, Idiom, Idiom Range Selection, Incremental Annotation, Morphological Tag Reference, Old English Morphological Tags (+2 more)

### Community 140 - "sqlalchemy"
Cohesion: 0.03
Nodes (21): upgrade(), upgrade(), downgrade(), downgrade(), upgrade(), upgrade(), downgrade(), upgrade() (+13 more)

### Community 142 - "sys"
Cohesion: 0.22
Nodes (5): file_sha256(), main(), parse_args(), verify_manifest(), verify_required_layout()

### Community 143 - "File Structure"
Cohesion: 0.13
Nodes (7): File Structure, Global Constraints, POS Field Catalog (F2) Implementation Plan, Review Focus, Task 1: The catalog module and its parity tests, Task 6: Import remaps label-form values from older exports, Task 7: Docs, help, ADR status and final verification

### Community 145 - "Annotation"
Cohesion: 0.05
Nodes (36): Agent Tooling and Quality Contract, Alembic Desktop Migrations, Fat ORM Models, In-App Help Engine, oeapp Layered Architecture, Napoleon Documentation Contract, PySide6 UI Layer, Services as UI–Model Bridge (+28 more)

### Community 147 - "71b9d6456d8b_add_sqlite_performance_indexes.py"
Cohesion: 0.17
Nodes (10): _create_index_if_missing(), downgrade(), _drop_index_if_exists(), _index_exists(), _table_exists(), upgrade(), _column_exists(), downgrade() (+2 more)

### Community 151 - "main_window.py"
Cohesion: 0.05
Nodes (13): CaseFilterDialog, NumberFilterDialog, PartOfSpeechFilterDialog, SentenceFilterDialog, CaseHighlighterCommand, HighlighterCommandBase, NoneHighlighterCommand, NumberHighlighterCommand (+5 more)

### Community 152 - "NewProjectDialog"
Cohesion: 0.06
Nodes (5): NewProjectDialog, OpenProjectDialog, filter_projects_table(), load_projects_into_table(), TestNewProjectDialog

### Community 154 - "create_engine_with_path"
Cohesion: 0.05
Nodes (24): Task 1: 1.0.0 baseline fixture and schema-drift test (D7), Task 2: Single `alembic_version` reader (D10), create_engine_with_path(), read_alembic_revision(), run_pragma_optimize(), build_baseline_db(), build_create_all_db(), schema_snapshot() (+16 more)

### Community 157 - "MainMenu"
Cohesion: 0.03
Nodes (18): RememberedAnnotationsDialog, FileMenu, HelpMenu, _is_offscreen_qt_platform(), MainMenu, PreferencesMenu, ProjectMenu, ToolsMenu (+10 more)

### Community 160 - "_sqlite_pragma_settings"
Cohesion: 0.29
Nodes (4): set_sqlite_pragma(), _parse_env_choice(), _parse_env_int(), _sqlite_pragma_settings()

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

### Community 191 - "_apply_message"
Cohesion: 0.33
Nodes (3): _apply_message(), _count_line(), _skipped_line()

### Community 194 - "json"
Cohesion: 0.13
Nodes (12): PosCodeRepair, _importer(), _migration(), _repairers(), _revision(), test_from_mapping_rejects_malformed_specs(), test_json_tables_equal_the_frozen_migration_tables(), test_malformed_values_section_raises_and_is_not_swallowed() (+4 more)

### Community 199 - "build_macos_helpbook.py"
Cohesion: 0.13
Nodes (8): build_macos.sh script, _build_help_index(), _copy_html_pages(), main(), parse_args(), _prepare_output_directory(), _validate_source_html(), _write_helpbook_info_plist()

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

### Community 215 - "exc.py"
Cohesion: 0.06
Nodes (10): main(), BackupFailed, DoesNotExist, MigrationCreationFailed, FieldMappingService, MigrationCreationResult, TestBackupFailed, TestDoesNotExist (+2 more)

### Community 219 - "AppendTextDialog"
Cohesion: 0.06
Nodes (3): AppendTextDialog, TextInputMixin, TestAppendTextDialog

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

### Community 236 - "SentenceCard"
Cohesion: 0.02
Nodes (5): Task 4: Edit mode, re-render and `reapply_search`, SentenceCard, _select_card(), TestAnnotationPropagationMenu, test_token_selection_edge_cases()

## Ambiguous Edges - Review These
- `Root` → `Empty Differential Dict Fixture`  [AMBIGUOUS]
  tests/differential/data/test_dict.txt · relation: conceptually_related_to
- `Keyboard Shortcuts` → `Undo Model`  [AMBIGUOUS]
  oeapp/help/topics/keybindings.md · relation: conceptually_related_to
- `Keyboard shortcuts` → `Troubleshooting`  [AMBIGUOUS]
  oeapp/help/assets/troubleshooting.html · relation: conceptually_related_to
- `Keyboard Shortcuts` → `Editor Versus Project Undo Model`  [AMBIGUOUS]
  oeapp/help/macos/AengliscToolkit.help/Contents/Resources/en.lproj/keybindings.html · relation: conceptually_related_to
- `Possible Helmeted Profile Motif` → `Circular Earth-Tone Emblem`  [AMBIGUOUS]
  assets/logo.iconset/icon_16x16.png · relation: conceptually_related_to

## Knowledge Gaps
- **78 isolated node(s):** `aenglisc_toolkit`, `Preterite-Present Requires Infinitive Shortcut`, `LaTeX PDF Layout Pipeline`, `Side-by-Side Full Translation View`, `Automatic Note Renumbering` (+73 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 3084 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **178 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `create_test_project()` connect `create_test_project` to `Project`, `MainWindow`, `test_main_window.py`, `.from_json`, `DeleteProjectDialog`, `ProjectExporter`, `AppContext`, `typing`, `.get`, `AnnotationPropagationService`, `main_window.py`, `TestBackupService`, `NewProjectDialog`, `Sentence`, `MainMenu`, `TokenTableModel`, `.export`, `Note`, `.get`, `Task 3: Migrate the three writers to layers (atomic)`, `ProjectImporter`, `TestSentenceCard`, `.export_side_by_side`, `TokenTable`, `CommandManager`, `_actions`, `TestMainWindowInitialization`, `NoteDialog`, `test_remembered_annotations.py`, `Annotation`, `TestFullTranslationPDFExporter`, `.create`, `NotesPanel`, `ImportProjectDialog`, `TestHighlighting`, `TokenOccurrenceMixin`, `_actions`, `TestOldEnglishTextEdit`, `EditProjectDialog`, `TestSentence`, `.test_line_initial_token_can_be_remembered_from_context_menu`, `._build_glossary_entries`, `.export_side_by_side_pdf`, `test_annotation.py`, `SentenceCard`, `.test_export_handles_file_write_error`, `DOCXExporter`, `._render_two_columns`, `.build`?**
  _High betweenness centrality (0.096) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `create_test_project()` (e.g. with `Task 3: Export submenu, enablement, save-then-write` and `Project`) actually correct?**
  _`create_test_project()` has 2 INFERRED edges - model-reasoned connections that need verification._
- **What connects `aenglisc_toolkit`, `Preterite-Present Requires Infinitive Shortcut`, `LaTeX PDF Layout Pipeline` to the rest of the system?**
  _78 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Project` be split into smaller, more focused modules?**
  _Cohesion score 0.025990454832959576 - nodes in this community are weakly interconnected._
- **Why does `Sentence` connect `Sentence` to `Project`, `WyrdcraeftIngestService`, `test_main_window.py`, `.from_json`, `TestProject`, `create_test_project`, `ProjectUI`, `export_docx.py`, `Token`, `typing`, `._on_token_selected_for_details`, `AnnotationPropagationService`, `main_window.py`, `SearchResult`, `OldEnglishTextSelector`, `fixture`, `.sorted_notes`, `test_search.py`, `Note`, `.get`, `.create_from_sentence`, `AnnotateTokenCommand`, `FullTranslationPDFExporter`, `ProjectImporter`, `token_details_sidebar.py`, `test_commands.py`, `OldEnglishTextEdit`, `CommandManager`, `.reference_label`, `TestMainWindowInitialization`, `NoteDialog`, `sentence_separator_kind`, `BaseTokenDetailsSidebar`, `TestFullTranslationPDFExporter`, `.create`, `TestSentence`, `SentenceCard`, `get_logger`, `._render_two_columns`?**
  _High betweenness centrality (0.084) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Root` and `Empty Differential Dict Fixture`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Keyboard Shortcuts` and `Undo Model`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
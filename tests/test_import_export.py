"""Unit tests for ProjectExporter and ProjectImporter."""

import gzip
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from oeapp.models.annotation import Annotation
from oeapp.models.chapter import Chapter
from oeapp.models.idiom import Idiom
from oeapp.models.note import Note
from oeapp.models.paragraph import Paragraph
from oeapp.models.project import Project
from oeapp.models.section import Section
from oeapp.models.sentence import Sentence
from oeapp.services.import_export import ProjectExporter, ProjectImporter
from oeapp.services.import_export_schema import ProjectExportPayload
from tests.conftest import create_test_project

FORBIDDEN_ID_KEYS = {
    "id",
    "project_id",
    "sentence_id",
    "token_id",
    "idiom_id",
    "chapter_id",
    "section_id",
    "paragraph_id",
    "start_token_id",
    "end_token_id",
}


def _assert_no_row_ids(data):
    """Assert recursively that no row ID fields are present."""
    if isinstance(data, dict):
        for key, value in data.items():
            assert key not in FORBIDDEN_ID_KEYS
            _assert_no_row_ids(value)
    elif isinstance(data, list):
        for item in data:
            _assert_no_row_ids(item)


def _build_full_project(db_session) -> Project:
    """Create a project with structure, notes, token and idiom annotations."""
    project = create_test_project(
        db_session,
        text="Se cyning. Þæt scip.",
        name="Full Export Test",
        source="Source",
        translator="Translator",
        notes="Notes",
    )
    sentence = project.sentences[0]
    tokens = sorted(sentence.tokens, key=lambda t: t.order_index)
    token_annotation = Annotation.get_by_token(tokens[0].id)
    assert token_annotation is not None
    token_annotation.pos = "N"
    token_annotation.gender = "m"
    token_annotation.save()

    note = Note(
        sentence_id=sentence.id,
        start_token=tokens[0].id,
        end_token=tokens[1].id,
        note_text_md="Token note",
        note_type="span",
    )
    note.save()

    idiom = Idiom(
        sentence_id=sentence.id,
        start_token_id=tokens[0].id,
        end_token_id=tokens[1].id,
    )
    idiom.save()
    idiom_annotation = Annotation(idiom_id=idiom.id, pos="R")
    idiom_annotation.save()
    db_session.commit()
    return project


def _legacy_verbose_export_size(project: Project, migration_version: str) -> int:
    """Build legacy-style verbose pretty JSON and return size in bytes."""
    project_data = {
        "export_version": "2.0",
        "migration_version": migration_version,
        "project": project.to_json(),
        "sentences": [
            sentence.to_json()
            for sentence in sorted(project.sentences, key=lambda s: s.display_order)
        ],
    }
    payload = ProjectExportPayload.model_validate(project_data)
    legacy_text = json.dumps(payload.model_dump(), indent=2, ensure_ascii=False)
    return len(legacy_text.encode("utf-8"))


class TestProjectExporter:
    """Test cases for ProjectExporter."""

    def test_sanitize_filename(self):
        """Test sanitize_filename() replaces spaces and removes dots."""
        assert ProjectExporter.sanitize_filename("My Project.json") == "My_Projectjson"
        assert ProjectExporter.sanitize_filename("My.Project.json") == "MyProjectjson"

    def test_get_project_success(self, db_session):
        """Test get_project() returns existing project."""
        project = create_test_project(db_session, name="Test Project")
        exporter = ProjectExporter(migration_service=MagicMock())
        retrieved = exporter.get_project(project.id)
        assert retrieved.id == project.id
        assert retrieved.name == "Test Project"

    def test_get_project_not_found(self, db_session):
        """Test get_project() raises ValueError when project not found."""
        exporter = ProjectExporter(migration_service=MagicMock())
        with pytest.raises(ValueError, match="Project with ID 99999 not found"):
            exporter.get_project(99999)

    def test_export_project_json(self, db_session, tmp_path):
        """Test export_project_json() creates JSON file with strict v2 schema."""
        project = _build_full_project(db_session)

        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v123"
        exporter = ProjectExporter(migration_service=mock_migration)

        export_file = tmp_path / "test_export.json"
        exporter.export_project_json(project.id, str(export_file))

        assert export_file.exists()
        with export_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["export_version"] == "2.0"
        assert data["migration_version"] == "v123"
        assert data["project"]["name"] == "Full Export Test"
        assert "chapters" in data["project"]
        assert data["project"]["chapters"][0]["sections"][0]["paragraphs"][0]["order"] == 1
        assert len(data["sentences"]) == 2
        assert data["sentences"][0]["text_oe"] == "Se cyning."
        assert "paragraph_ref" in data["sentences"][0]
        assert "idioms" in data["sentences"][0]
        _assert_no_row_ids(data)
        token_annotation = data["sentences"][0]["tokens"][0]["annotation"]
        assert "verb_requires_infinitive" not in token_annotation
        assert "verb_impersonal" not in token_annotation
        assert "verb_transitivity" not in token_annotation

    def test_export_project_json_adds_extension(self, db_session, tmp_path):
        """Test export_project_json() adds .json extension if missing."""
        project = create_test_project(db_session, name="ExtTest")
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)

        base_path = tmp_path / "export_no_ext"
        exporter.export_project_json(project.id, str(base_path))

        assert Path(str(base_path) + ".json").exists()

    def test_export_project_json_serialization_error(self, db_session, tmp_path):
        """Test export_project_json() handles serialization errors."""
        project = create_test_project(db_session, name="SerialError")
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)

        with patch("json.dumps", side_effect=TypeError("Not serializable")):
            with pytest.raises(ValueError, match="Failed to serialize project data"):
                exporter.export_project_json(project.id, str(tmp_path / "error.json"))

    def test_export_project_json_writes_gzip_file(self, db_session, tmp_path):
        """Test exporter writes gzip-compressed JSON when filename ends with .gz."""
        project = _build_full_project(db_session)
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)

        export_file = tmp_path / "compressed_export.json.gz"
        exporter.export_project_json(project.id, str(export_file))

        assert export_file.exists()
        with gzip.open(export_file, "rt", encoding="utf-8") as f:
            data = json.load(f)
        assert data["export_version"] == "2.0"
        assert data["project"]["name"] == "Full Export Test"

    def test_export_project_json_compact_flag_false_writes_pretty_json(
        self, db_session, tmp_path
    ):
        """Test compact=False writes sparse but pretty-printed JSON."""
        project = _build_full_project(db_session)
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)

        export_file = tmp_path / "pretty_export.json"
        exporter.export_project_json(project.id, str(export_file), compact=False)
        content = export_file.read_text(encoding="utf-8")

        assert "\n  " in content
        data = json.loads(content)
        assert data["export_version"] == "2.0"

    def test_export_project_json_sparse_omits_none_and_default_values(
        self, db_session, tmp_path
    ):
        """Test default export omits null and schema-default values."""
        project = create_test_project(db_session, name="Sparse Export", text="Se cyning.")
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)

        export_file = tmp_path / "sparse_export.json"
        exporter.export_project_json(project.id, str(export_file))
        data = json.loads(export_file.read_text(encoding="utf-8"))

        sentence = data["sentences"][0]
        assert "annotation" not in sentence["tokens"][0]

    def test_export_project_json_reduces_size_for_sparse_projects(
        self, db_session, tmp_path
    ):
        """Test compact sparse export is substantially smaller than legacy verbose export."""
        text = " ".join(["Ic eom cyning." for _ in range(60)])
        project = create_test_project(db_session, name="Size Regression", text=text)
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)

        export_file = tmp_path / "size_regression.json"
        exporter.export_project_json(project.id, str(export_file))
        compact_size = export_file.stat().st_size
        legacy_size = _legacy_verbose_export_size(project, "v1")

        assert compact_size < legacy_size
        reduction_ratio = 1 - (compact_size / legacy_size)
        assert reduction_ratio >= 0.40


class TestProjectImporter:
    """Test cases for ProjectImporter."""

    def test_validate_migration_version_success(self):
        """Test validation passes when versions match or no version requirement."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v1"
        importer = ProjectImporter(migration_service=mock_migration)

        importer._validate_migration_version("v1")

        mock_migration.code_migration_version.return_value = None
        importer._validate_migration_version("any")

    def test_validate_migration_version_missing(self):
        """Test validation raises if version is missing in export."""
        importer = ProjectImporter(migration_service=MagicMock())
        with pytest.raises(ValueError, match="Export file missing migration_version"):
            importer._validate_migration_version("")

    def test_validate_migration_version_incompatible(self):
        """Test validation raises if no revision chain found."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "new_v"
        mock_migration.revision_chain.return_value = []

        mock_metadata = MagicMock()
        mock_metadata.get_min_version_for_migration.return_value = None

        importer = ProjectImporter(
            migration_service=mock_migration,
            migration_metadata_service=mock_metadata,
        )

        with pytest.raises(ValueError, match="is not compatible"):
            importer._validate_migration_version("old_v")

    def test_validate_migration_version_min_app_requirement(self):
        """Test validation raises with minimum app version message."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v2"
        mock_migration.revision_chain.return_value = []

        mock_metadata = MagicMock()
        mock_metadata.get_min_version_for_migration.return_value = "0.5.0"

        importer = ProjectImporter(
            migration_service=mock_migration,
            migration_metadata_service=mock_metadata,
        )

        with pytest.raises(ValueError, match="requires at least version 0.5.0"):
            importer._validate_migration_version("v1")

    def test_transform_data_with_mappings(self):
        """Test data transformation applies field mappings."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v2"
        mock_migration.revision_chain.return_value = ["rev1"]

        importer = ProjectImporter(migration_service=mock_migration)
        data = {"project": {"old_name": "Project"}}
        mappings = {"rev1": {"Project": {"old_name": "new_name"}}}

        with patch.object(importer, "_load_field_mappings", return_value=mappings):
            transformed = importer._transform_data(data, "v1")

        assert transformed["project"]["new_name"] == "Project"
        assert "old_name" not in transformed["project"]

    def test_import_project_json_full_round_trip(self, db_session, tmp_path):
        """Test full export -> import -> export round-trip preserves project data."""
        project = _build_full_project(db_session)
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        mock_migration.code_migration_version.return_value = "v1"

        exporter = ProjectExporter(migration_service=mock_migration)
        importer = ProjectImporter(migration_service=mock_migration)

        export_file = tmp_path / "roundtrip_export.json"
        exporter.export_project_json(project.id, str(export_file))
        original_data = json.loads(export_file.read_text(encoding="utf-8"))

        project.delete()
        db_session.commit()

        imported_project, renamed = importer.import_project_json(str(export_file))
        assert imported_project.name == "Full Export Test"
        assert not renamed

        reexport_file = tmp_path / "roundtrip_reexport.json"
        exporter.export_project_json(imported_project.id, str(reexport_file))
        reexport_data = json.loads(reexport_file.read_text(encoding="utf-8"))

        assert reexport_data == original_data
        _assert_no_row_ids(reexport_data)

    def test_import_project_json_rejects_legacy_flat_format(self, db_session, tmp_path):
        """Test import rejects legacy sentence payload with paragraph_id."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v1"
        importer = ProjectImporter(migration_service=mock_migration)

        legacy_payload = {
            "export_version": "2.0",
            "migration_version": "v1",
            "project": {
                "name": "Legacy",
                "source": None,
                "translator": None,
                "notes": None,
                "created_at": None,
                "updated_at": None,
                "chapters": [],
            },
            "sentences": [
                {
                    "display_order": 1,
                    "paragraph_id": 123,
                    "text_oe": "legacy",
                    "tokens": [],
                    "notes": [],
                }
            ],
        }
        import_file = tmp_path / "legacy.json"
        import_file.write_text(json.dumps(legacy_payload), encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid project export format"):
            importer.import_project_json(str(import_file))

    def test_import_project_json_rejects_extra_keys(self, db_session, tmp_path):
        """Test strict schema rejects unknown keys in payload."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v1"
        importer = ProjectImporter(migration_service=mock_migration)

        payload = {
            "export_version": "2.0",
            "migration_version": "v1",
            "project": {
                "name": "Imported Project",
                "source": None,
                "translator": None,
                "notes": "Test notes",
                "created_at": None,
                "updated_at": None,
                "chapters": [
                    {
                        "number": 1,
                        "title": None,
                        "paragraphs": [],  # invalid extra key for chapter
                        "sections": [
                            {
                                "number": 1,
                                "title": None,
                                "paragraphs": [{"order": 1}],
                            }
                        ],
                    }
                ],
            },
            "sentences": [],
        }
        import_file = tmp_path / "invalid_extra.json"
        import_file.write_text(json.dumps(payload), encoding="utf-8")

        with pytest.raises(ValueError, match="Invalid project export format"):
            importer.import_project_json(str(import_file))

    def test_import_project_json_invalid_file(self):
        """Test import raises error for missing or invalid files."""
        importer = ProjectImporter(MagicMock())

        with pytest.raises(ValueError, match="not found"):
            importer.import_project_json("nonexistent.json")

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_bytes", side_effect=PermissionError("Denied")):
                with pytest.raises(ValueError, match="Failed to load"):
                    importer.import_project_json("denied.json")

    def test_import_project_json_accepts_gzip_with_non_gz_extension(
        self, db_session, tmp_path
    ):
        """Test importer uses magic header detection even when extension is not .gz."""
        project = _build_full_project(db_session)
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        mock_migration.code_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)
        importer = ProjectImporter(migration_service=mock_migration)

        export_file = tmp_path / "source.json"
        exporter.export_project_json(project.id, str(export_file))
        payload_bytes = export_file.read_bytes()
        disguised_file = tmp_path / "payload.bin"
        disguised_file.write_bytes(gzip.compress(payload_bytes))

        project.delete()
        db_session.commit()

        imported_project, _renamed = importer.import_project_json(str(disguised_file))
        assert imported_project.name == "Full Export Test"

    def test_import_project_json_accepts_plain_json_with_gz_extension(
        self, db_session, tmp_path
    ):
        """Test importer falls back to plain JSON parsing if content is not gzip."""
        project = _build_full_project(db_session)
        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        mock_migration.code_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)
        importer = ProjectImporter(migration_service=mock_migration)

        export_file = tmp_path / "source.json"
        exporter.export_project_json(project.id, str(export_file))
        disguised_file = tmp_path / "not_really_gzip.gz"
        disguised_file.write_text(export_file.read_text(encoding="utf-8"), encoding="utf-8")

        project.delete()
        db_session.commit()

        imported_project, _renamed = importer.import_project_json(str(disguised_file))
        assert imported_project.name == "Full Export Test"

    def test_import_project_json_accepts_token_annotation_null(
        self, db_session, tmp_path
    ):
        """Test importer accepts token annotation set to null."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v1"
        importer = ProjectImporter(migration_service=mock_migration)

        payload = {
            "export_version": "2.0",
            "migration_version": "v1",
            "project": {
                "name": "Null Annotation",
                "source": None,
                "translator": None,
                "notes": None,
                "created_at": None,
                "updated_at": None,
                "chapters": [
                    {
                        "number": 1,
                        "title": None,
                        "sections": [
                            {
                                "number": 1,
                                "title": None,
                                "paragraphs": [{"order": 1}],
                            }
                        ],
                    }
                ],
            },
            "sentences": [
                {
                    "display_order": 1,
                    "text_oe": "Se cyning.",
                    "text_modern": None,
                    "paragraph_ref": {
                        "chapter_number": 1,
                        "section_number": 1,
                        "paragraph_order": 1,
                    },
                    "tokens": [
                        {
                            "order_index": 0,
                            "surface": "Se",
                            "annotation": None,
                        },
                        {
                            "order_index": 1,
                            "surface": "cyning",
                        },
                    ],
                    "notes": [],
                    "idioms": [],
                }
            ],
        }
        import_file = tmp_path / "null_annotation.json"
        import_file.write_text(json.dumps(payload), encoding="utf-8")

        project, _renamed = importer.import_project_json(str(import_file))
        assert project.name == "Null Annotation"

    def test_round_trip_preserves_verse_spans_and_auto_titles(
        self, db_session, tmp_path
    ):
        """Verse span metadata and title_auto flags should survive export/import."""
        project = Project(name="Verse Roundtrip")
        project.save()
        chapter = Chapter.create(
            project_id=project.id,
            number=1,
            title="Auto Prose Header ....",
            title_auto=True,
            commit=False,
        )
        section = Section.create(
            chapter_id=chapter.id,
            number=1,
            title="Lines 1-5",
            title_auto=True,
            commit=False,
        )
        paragraph = Paragraph(section_id=section.id, order=1)
        db_session.add(paragraph)
        db_session.flush()
        Sentence.create(
            project_id=project.id,
            display_order=1,
            text_oe="Hwæt!\nwē Gār-Dena",
            paragraph_id=paragraph.id,
            verse_line_start=1,
            verse_line_end=5,
            commit=False,
        )
        db_session.commit()

        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v1"
        mock_migration.code_migration_version.return_value = "v1"
        exporter = ProjectExporter(migration_service=mock_migration)
        importer = ProjectImporter(migration_service=mock_migration)

        export_file = tmp_path / "verse_roundtrip.json"
        exporter.export_project_json(project.id, str(export_file))
        exported = json.loads(export_file.read_text(encoding="utf-8"))

        assert exported["project"]["chapters"][0]["title_auto"] is True
        assert exported["project"]["chapters"][0]["sections"][0]["title_auto"] is True
        assert exported["sentences"][0]["verse_line_start"] == 1
        assert exported["sentences"][0]["verse_line_end"] == 5

        project.delete()
        db_session.commit()
        imported_project, was_renamed = importer.import_project_json(str(export_file))
        assert was_renamed is False

        imported_chapter = imported_project.chapters[0]
        imported_section = imported_chapter.sections[0]
        imported_sentence = imported_project.sentences[0]
        assert imported_chapter.title_auto is True
        assert imported_section.title_auto is True
        assert imported_sentence.verse_line_start == 1
        assert imported_sentence.verse_line_end == 5
        assert imported_sentence.reference_label == "Verse: 1-5"

    def test_load_field_mappings_io_error(self):
        """Test _load_field_mappings handles errors gracefully."""
        importer = ProjectImporter(MagicMock())
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", side_effect=OSError):
                assert importer._load_field_mappings() == {}

        with patch("pathlib.Path.exists", return_value=True):
            with patch(
                "pathlib.Path.open",
                side_effect=json.JSONDecodeError("msg", "doc", 0),
            ):
                assert importer._load_field_mappings() == {}

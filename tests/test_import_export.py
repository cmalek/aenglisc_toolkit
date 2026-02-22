"""Unit tests for ProjectExporter and ProjectImporter."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from oeapp.models.annotation import Annotation
from oeapp.models.idiom import Idiom
from oeapp.models.note import Note
from oeapp.models.project import Project
from oeapp.services.import_export import ProjectExporter, ProjectImporter
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

        with patch("json.dump", side_effect=TypeError("Not serializable")):
            with pytest.raises(ValueError, match="Failed to serialize project data"):
                exporter.export_project_json(project.id, str(tmp_path / "error.json"))


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
            with patch("pathlib.Path.open", side_effect=PermissionError("Denied")):
                with pytest.raises(ValueError, match="Failed to load"):
                    importer.import_project_json("denied.json")

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

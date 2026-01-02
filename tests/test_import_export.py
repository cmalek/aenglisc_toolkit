"""Unit tests for ProjectExporter and ProjectImporter."""

import json
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from oeapp.services.import_export import ProjectExporter, ProjectImporter
from tests.conftest import create_test_project


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
        """Test export_project_json() creates JSON file with correct data."""
        project = create_test_project(
            db_session,
            text="Se cyning. Þæt scip.",
            name="Export Test",
            source="Source",
            translator="Translator",
            notes="Notes",
        )

        mock_migration = MagicMock()
        mock_migration.db_migration_version.return_value = "v123"
        exporter = ProjectExporter(migration_service=mock_migration)

        export_file = tmp_path / "test_export.json"
        exporter.export_project_json(project.id, str(export_file))

        assert export_file.exists()
        with export_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["export_version"] == "1.0"
        assert data["migration_version"] == "v123"
        assert data["project"]["name"] == "Export Test"
        assert len(data["sentences"]) == 2
        assert data["sentences"][0]["text_oe"] == "Se cyning."
        assert data["sentences"][1]["text_oe"] == "Þæt scip."

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

        # Mock json.dump to raise TypeError
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

        # Matching version
        importer._validate_migration_version("v1")

        # No current version (e.g. no migrations yet)
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
        mock_migration.revision_chain.return_value = [] # No chain found

        mock_metadata = MagicMock()
        mock_metadata.get_min_version_for_migration.return_value = None

        importer = ProjectImporter(migration_service=mock_migration, migration_metadata_service=mock_metadata)

        with pytest.raises(ValueError, match="is not compatible"):
            importer._validate_migration_version("old_v")

    def test_validate_migration_version_min_app_requirement(self):
        """Test validation raises with minimum app version message."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v2"
        mock_migration.revision_chain.return_value = []

        mock_metadata = MagicMock()
        mock_metadata.get_min_version_for_migration.return_value = "0.5.0"

        importer = ProjectImporter(migration_service=mock_migration, migration_metadata_service=mock_metadata)

        with pytest.raises(ValueError, match="requires at least version 0.5.0"):
            importer._validate_migration_version("v1")

    def test_validate_migration_version_generic_exception(self):
        """Test validation handles generic exceptions from migration service."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v2"
        mock_migration.revision_chain.side_effect = Exception("Internal Error")

        mock_metadata = MagicMock()
        mock_metadata.get_min_version_for_migration.return_value = "0.6.0"

        importer = ProjectImporter(migration_service=mock_migration, migration_metadata_service=mock_metadata)

        # Should catch Exception and check min_version
        with pytest.raises(ValueError, match="requires at least version 0.6.0"):
            importer._validate_migration_version("v1")

        # Should catch Exception and raise generic incompatibility if no min_version
        mock_metadata.get_min_version_for_migration.return_value = None
        with pytest.raises(ValueError, match="is not compatible with the current application version"):
            importer._validate_migration_version("v1")

    def test_transform_data_no_change(self):
        """Test data is returned unchanged if versions match."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v1"
        importer = ProjectImporter(migration_service=mock_migration)

        data = {"key": "value"}
        assert importer._transform_data(data, "v1") == data

    def test_transform_data_with_mappings(self):
        """Test data transformation applies field mappings."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v2"
        mock_migration.revision_chain.return_value = ["rev1"]

        importer = ProjectImporter(migration_service=mock_migration)

        data = {
            "project": {"old_name": "Project"},
            "sentences": [{"old_text": "OE Text"}]
        }

        mappings = {
            "rev1": {
                "Project": {"old_name": "new_name"},
                "Sentence": {"old_text": "new_text"}
            }
        }

        with patch.object(importer, "_load_field_mappings", return_value=mappings):
            transformed = importer._transform_data(data, "v1")

        assert transformed["project"]["new_name"] == "Project"
        assert "old_name" not in transformed["project"]
        assert transformed["sentences"][0]["new_text"] == "OE Text"

    def test_apply_mappings_recursive(self):
        """Test recursive mapping application on nested dicts and lists."""
        importer = ProjectImporter(MagicMock())
        data = {
            "a": {"old": 1},
            "b": [{"old": 2}, {"other": 3}]
        }
        mappings = {"Model": {"old": "new"}}

        importer._apply_mappings_recursive(data, mappings)

        assert data["a"]["new"] == 1
        assert data["b"][0]["new"] == 2
        assert data["b"][1]["other"] == 3

    def test_apply_field_mappings_skips_missing_sha(self):
        """Test _apply_field_mappings skips migrations without mappings."""
        importer = ProjectImporter(MagicMock())
        data = {"key": "val"}

        with patch.object(importer, "_load_field_mappings", return_value={}):
            result = importer._apply_field_mappings(data, ["missing_sha"])
            assert result == data

    def test_resolve_project_name(self, db_session):
        """Test project name collision resolution."""
        create_test_project(db_session, name="Existing")
        importer = ProjectImporter(MagicMock())

        # No collision
        name, renamed = importer._resolve_project_name("Unique")
        assert name == "Unique"
        assert not renamed

        # Collision
        name, renamed = importer._resolve_project_name("Existing")
        assert name == "Existing (1)"
        assert renamed

        # Multi-collision
        create_test_project(db_session, name="Existing (1)")
        name, renamed = importer._resolve_project_name("Existing")
        assert name == "Existing (2)"

    def test_import_project_json_full(self, db_session, tmp_path):
        """Test the full import process from a JSON file."""
        mock_migration = MagicMock()
        mock_migration.code_migration_version.return_value = "v1"
        importer = ProjectImporter(migration_service=mock_migration)

        project_data = {
            "migration_version": "v1",
            "project": {
            "name": "Imported Project",
                "notes": "Test notes"
            },
            "sentences": [
                {
                    "display_order": 1,
                    "text_oe": "Se cyning.",
                    "tokens": [
                        {"order_index": 0, "surface": "Se"},
                        {"order_index": 1, "surface": "cyning"}
                    ],
                    "notes": []
                }
            ]
        }

        import_file = tmp_path / "import.json"
        import_file.write_text(json.dumps(project_data))

        project, renamed = importer.import_project_json(str(import_file))

        assert project.name == "Imported Project"
        assert not renamed
        assert len(project.sentences) == 1
        assert project.sentences[0].text_oe == "Se cyning."
        assert len(project.sentences[0].tokens) == 2

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
        # OSError/PermissionError
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", side_effect=OSError):
                assert importer._load_field_mappings() == {}

        # JSONDecodeError
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.open", side_effect=json.JSONDecodeError("msg", "doc", 0)):
                assert importer._load_field_mappings() == {}

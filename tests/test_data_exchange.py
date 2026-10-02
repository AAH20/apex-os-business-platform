"""Tests for the data exchange module."""
import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import pytest

from apex_os_bp.data_exchange import (
    CSVHandler,
    DataExchangeError,
    DataRecord,
    DataSchema,
    Column,
    ExcelHandler,
    ExportError,
    ImportError,
    ImportResult,
    JSONHandler,
    ValidationError,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_schema():
    """Create a sample schema for testing."""
    return DataSchema(
        name="test_schema",
        columns=[
            Column(name="id", data_type="integer", required=True),
            Column(name="name", data_type="string", required=True),
            Column(name="email", data_type="string"),
            Column(name="age", data_type="integer"),
            Column(name="salary", data_type="float"),
            Column(name="active", data_type="boolean"),
        ],
    )


@pytest.fixture
def sample_records():
    """Create sample data records."""
    return [
        DataRecord(
            data={"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30, "salary": 50000.0, "active": True},
            row_number=1,
        ),
        DataRecord(
            data={"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25, "salary": 45000.0, "active": False},
            row_number=2,
        ),
        DataRecord(
            data={"id": 3, "name": "Charlie", "email": "charlie@example.com", "age": 35, "salary": 60000.0, "active": True},
            row_number=3,
        ),
    ]


@pytest.fixture
def csv_file(tmp_path):
    """Create a sample CSV file."""
    path = tmp_path / "test.csv"
    path.write_text("id,name,email,age,salary,active\n1,Alice,alice@example.com,30,50000.0,true\n2,Bob,bob@example.com,25,45000.0,false\n")
    return path


@pytest.fixture
def json_file(tmp_path):
    """Create a sample JSON file."""
    path = tmp_path / "test.json"
    data = [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "age": 30, "salary": 50000.0, "active": True},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "age": 25, "salary": 45000.0, "active": False},
    ]
    path.write_text(json.dumps(data))
    return path


# ── Model Tests ───────────────────────────────────────────────────────────────


class TestDataSchema:
    """Test DataSchema model."""

    def test_schema_creation(self):
        """Schema can be created with columns."""
        schema = DataSchema(
            name="test",
            columns=[Column(name="id", data_type="integer", required=True)],
        )
        assert schema.name == "test"
        assert len(schema.columns) == 1

    def test_get_column(self):
        """Column can be retrieved by name."""
        schema = DataSchema(
            name="test",
            columns=[
                Column(name="id", data_type="integer"),
                Column(name="name", data_type="string"),
            ],
        )
        col = schema.get_column("name")
        assert col is not None
        assert col.name == "name"
        assert col.data_type == "string"

    def test_get_column_not_found(self):
        """Returns None for non-existent column."""
        schema = DataSchema(name="test", columns=[])
        assert schema.get_column("nonexistent") is None

    def test_validate_record_valid(self):
        """Valid record passes validation."""
        schema = DataSchema(
            name="test",
            columns=[
                Column(name="id", data_type="integer", required=True),
                Column(name="name", data_type="string", required=True),
            ],
        )
        errors = schema.validate_record({"id": 1, "name": "Alice"})
        assert len(errors) == 0

    def test_validate_record_missing_required(self):
        """Missing required column produces error."""
        schema = DataSchema(
            name="test",
            columns=[
                Column(name="id", data_type="integer", required=True),
                Column(name="name", data_type="string", required=True),
            ],
        )
        errors = schema.validate_record({"id": 1})
        assert len(errors) == 1
        assert "name" in errors[0]

    def test_validate_record_type_mismatch(self):
        """Type mismatch produces error."""
        schema = DataSchema(
            name="test",
            columns=[Column(name="age", data_type="integer")],
        )
        errors = schema.validate_record({"age": "not_a_number"})
        assert len(errors) == 1
        assert "age" in errors[0]


class TestDataRecord:
    """Test DataRecord model."""

    def test_record_creation(self):
        """Record can be created."""
        record = DataRecord(data={"key": "value"}, row_number=1)
        assert record.data["key"] == "value"
        assert record.row_number == 1

    def test_record_get(self):
        """Record get method works."""
        record = DataRecord(data={"key": "value"})
        assert record.get("key") == "value"
        assert record.get("missing") is None
        assert record.get("missing", "default") == "default"

    def test_record_set(self):
        """Record set method works."""
        record = DataRecord()
        record.set("key", "value")
        assert record.data["key"] == "value"

    def test_record_to_dict(self):
        """Record converts to dictionary."""
        record = DataRecord(data={"a": 1, "b": 2})
        d = record.to_dict()
        assert d == {"a": 1, "b": 2}


class TestImportResult:
    """Test ImportResult model."""

    def test_result_creation(self):
        """Result can be created."""
        result = ImportResult(success=True, records_imported=5)
        assert result.success is True
        assert result.records_imported == 5
        assert result.records_failed == 0

    def test_add_error(self):
        """Error can be added."""
        result = ImportResult(success=True)
        result.add_error("Something went wrong")
        assert len(result.errors) == 1
        assert "Something went wrong" in result.errors[0]

    def test_add_warning(self):
        """Warning can be added."""
        result = ImportResult(success=True)
        result.add_warning("Something suspicious")
        assert len(result.warnings) == 1

    def test_to_dict(self):
        """Result converts to dictionary."""
        result = ImportResult(success=True, records_imported=3, records_failed=1)
        result.add_error("err")
        result.add_warning("warn")
        d = result.to_dict()
        assert d["success"] is True
        assert d["records_imported"] == 3
        assert d["records_failed"] == 1
        assert len(d["errors"]) == 1
        assert len(d["warnings"]) == 1


# ── Exception Tests ───────────────────────────────────────────────────────────


class TestExceptions:
    """Test custom exceptions."""

    def test_data_exchange_error(self):
        """Base exception can be raised."""
        with pytest.raises(DataExchangeError):
            raise DataExchangeError("test")

    def test_import_error(self):
        """ImportError can be raised."""
        with pytest.raises(ImportError):
            raise ImportError("test")

    def test_export_error(self):
        """ExportError can be raised."""
        with pytest.raises(ExportError):
            raise ExportError("test")

    def test_validation_error(self):
        """ValidationError can be raised."""
        with pytest.raises(ValidationError):
            raise ValidationError("test")

    def test_exception_hierarchy(self):
        """All exceptions inherit from DataExchangeError."""
        assert issubclass(ImportError, DataExchangeError)
        assert issubclass(ExportError, DataExchangeError)
        assert issubclass(ValidationError, DataExchangeError)


# ── CSV Import Tests ──────────────────────────────────────────────────────────


class TestCSVImport:
    """Test CSV import functionality."""

    def test_import_from_file(self, csv_file, sample_schema):
        """Import CSV from file path."""
        handler = CSVHandler(schema=sample_schema)
        result = handler.import_data(csv_file)
        assert result.success is True
        assert result.records_imported == 2
        assert result.records_failed == 0

    def test_import_from_string_io(self, sample_schema):
        """Import CSV from StringIO buffer."""
        csv_content = "id,name,email\n1,Alice,alice@test.com\n2,Bob,bob@test.com\n"
        handler = CSVHandler(schema=sample_schema)
        result = handler.import_data(io.StringIO(csv_content))
        assert result.success is True
        assert result.records_imported == 2

    def test_import_without_schema(self, csv_file):
        """Import CSV without schema."""
        handler = CSVHandler()
        result = handler.import_data(csv_file)
        assert result.success is True
        assert result.records_imported == 2

    def test_import_file_not_found(self, sample_schema):
        """Import raises error for missing file."""
        handler = CSVHandler(schema=sample_schema)
        with pytest.raises(ImportError):
            handler.import_data("/nonexistent/path/file.csv")

    def test_import_empty_file(self, tmp_path, sample_schema):
        """Import handles empty CSV file."""
        path = tmp_path / "empty.csv"
        path.write_text("")
        handler = CSVHandler(schema=sample_schema)
        result = handler.import_data(path)
        assert result.records_imported == 0
        assert len(result.warnings) > 0

    def test_import_with_skip_rows(self, tmp_path, sample_schema):
        """Import with skip_rows parameter."""
        path = tmp_path / "skip.csv"
        path.write_text("metadata line\nanother metadata\nid,name\n1,Alice\n")
        handler = CSVHandler(schema=sample_schema)
        result = handler.import_data(path, skip_rows=2)
        assert result.success is True
        assert result.records_imported == 1

    def test_import_without_header(self, tmp_path):
        """Import CSV without header row."""
        schema = DataSchema(
            name="noheader",
            columns=[
                Column(name="id", data_type="integer"),
                Column(name="name", data_type="string"),
                Column(name="email", data_type="string"),
            ],
        )
        path = tmp_path / "noheader.csv"
        path.write_text("1,Alice,alice@test.com\n2,Bob,bob@test.com\n")
        handler = CSVHandler(schema=schema)
        result = handler.import_data(path, has_header=False)
        assert result.success is True
        assert result.records_imported == 2

    def test_import_type_conversion(self, tmp_path):
        """Import converts types based on schema."""
        schema = DataSchema(
            name="typed",
            columns=[
                Column(name="id", data_type="integer"),
                Column(name="score", data_type="float"),
                Column(name="active", data_type="boolean"),
            ],
        )
        path = tmp_path / "typed.csv"
        path.write_text("id,score,active\n1,95.5,true\n2,87.3,false\n")
        handler = CSVHandler(schema=schema)
        result = handler.import_data(path)
        assert result.success is True
        records = result.metadata["records"]
        assert records[0].data["id"] == 1
        assert records[0].data["score"] == 95.5
        assert records[0].data["active"] is True

    def test_import_validation_failure(self, tmp_path):
        """Import with invalid data records failure."""
        schema = DataSchema(
            name="strict",
            columns=[Column(name="id", data_type="integer", required=True)],
        )
        path = tmp_path / "invalid.csv"
        path.write_text("id,name\n1,Alice\n,Bob\n")  # Missing id in second row
        handler = CSVHandler(schema=schema)
        result = handler.import_data(path)
        assert result.success is False
        assert result.records_imported == 1
        assert result.records_failed == 1

    def test_import_extra_columns_warning(self, tmp_path):
        """Import warns about columns not in schema."""
        schema = DataSchema(
            name="limited",
            columns=[Column(name="id", data_type="integer")],
        )
        path = tmp_path / "extra.csv"
        path.write_text("id,extra_col\n1,value\n")
        handler = CSVHandler(schema=schema)
        result = handler.import_data(path)
        assert result.success is True
        assert len(result.warnings) > 0


# ── CSV Export Tests ──────────────────────────────────────────────────────────


class TestCSVExport:
    """Test CSV export functionality."""

    def test_export_to_string(self, sample_records):
        """Export records to CSV string."""
        handler = CSVHandler()
        result = handler.export_data(sample_records)
        assert isinstance(result, str)
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 records
        assert "id" in lines[0]
        assert "name" in lines[0]

    def test_export_to_file(self, sample_records, tmp_path):
        """Export records to CSV file."""
        path = tmp_path / "output.csv"
        handler = CSVHandler()
        handler.export_data(sample_records, destination=path)
        assert path.exists()
        content = path.read_text()
        assert "id" in content
        assert "Alice" in content

    def test_export_to_string_io(self, sample_records):
        """Export records to StringIO buffer."""
        buffer = io.StringIO()
        handler = CSVHandler()
        handler.export_data(sample_records, destination=buffer)
        content = buffer.getvalue()
        assert "id" in content
        assert "Alice" in content

    def test_export_with_schema(self, sample_records, sample_schema):
        """Export uses schema for column ordering."""
        handler = CSVHandler(schema=sample_schema)
        result = handler.export_data(sample_records)
        lines = result.strip().split("\n")
        header = lines[0]
        # Schema columns should be in order
        assert header.index("id") < header.index("name")
        assert header.index("name") < header.index("email")

    def test_export_without_header(self, sample_records):
        """Export without header row."""
        handler = CSVHandler()
        result = handler.export_data(sample_records, include_header=False)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # no header

    def test_export_empty_records(self):
        """Export empty record list."""
        handler = CSVHandler()
        result = handler.export_data([])
        assert isinstance(result, str)

    def test_export_creates_parent_dirs(self, sample_records, tmp_path):
        """Export creates parent directories."""
        path = tmp_path / "subdir" / "nested" / "output.csv"
        handler = CSVHandler()
        handler.export_data(sample_records, destination=path)
        assert path.exists()


# ── JSON Import Tests ─────────────────────────────────────────────────────────


class TestJSONImport:
    """Test JSON import functionality."""

    def test_import_from_file(self, json_file, sample_schema):
        """Import JSON from file."""
        handler = JSONHandler(schema=sample_schema)
        result = handler.import_data(json_file)
        assert result.success is True
        assert result.records_imported == 2

    def test_import_without_schema(self, json_file):
        """Import JSON without schema."""
        handler = JSONHandler()
        result = handler.import_data(json_file)
        assert result.success is True
        assert result.records_imported == 2

    def test_import_file_not_found(self):
        """Import raises error for missing file."""
        handler = JSONHandler()
        with pytest.raises(ImportError):
            handler.import_data("/nonexistent/file.json")

    def test_import_invalid_json(self, tmp_path):
        """Import raises error for invalid JSON."""
        path = tmp_path / "invalid.json"
        path.write_text("{invalid json content")
        handler = JSONHandler()
        with pytest.raises(ImportError):
            handler.import_data(path)

    def test_import_with_data_key(self, tmp_path):
        """Import JSON with nested data key."""
        path = tmp_path / "nested.json"
        data = {"records": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}
        path.write_text(json.dumps(data))
        handler = JSONHandler()
        result = handler.import_data(path, data_key="records")
        assert result.success is True
        assert result.records_imported == 2

    def test_import_auto_detect_data_key(self, tmp_path):
        """Import auto-detects common data keys."""
        path = tmp_path / "auto.json"
        data = {"data": [{"id": 1, "name": "Alice"}]}
        path.write_text(json.dumps(data))
        handler = JSONHandler()
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 1

    def test_import_empty_array(self, tmp_path):
        """Import empty JSON array."""
        path = tmp_path / "empty.json"
        path.write_text("[]")
        handler = JSONHandler()
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 0

    def test_import_non_dict_items(self, tmp_path):
        """Import handles non-dict items in array."""
        path = tmp_path / "mixed.json"
        path.write_text('[{"id": 1}, "not a dict", {"id": 2}]')
        handler = JSONHandler()
        result = handler.import_data(path)
        assert result.success is False
        assert result.records_imported == 2
        assert result.records_failed == 1

    def test_import_validation(self, tmp_path):
        """Import validates against schema."""
        schema = DataSchema(
            name="strict",
            columns=[Column(name="id", data_type="integer", required=True)],
        )
        path = tmp_path / "invalid.json"
        path.write_text('[{"id": 1}, {"name": "no id"}]')
        handler = JSONHandler(schema=schema)
        result = handler.import_data(path)
        assert result.success is False
        assert result.records_failed == 1


# ── JSON Export Tests ─────────────────────────────────────────────────────────


class TestJSONExport:
    """Test JSON export functionality."""

    def test_export_to_string(self, sample_records):
        """Export records to JSON string."""
        handler = JSONHandler()
        result = handler.export_data(sample_records)
        assert isinstance(result, str)
        data = json.loads(result)
        assert len(data) == 3
        assert data[0]["name"] == "Alice"

    def test_export_to_file(self, sample_records, tmp_path):
        """Export records to JSON file."""
        path = tmp_path / "output.json"
        handler = JSONHandler()
        handler.export_data(sample_records, destination=path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data) == 3

    def test_export_with_data_key(self, sample_records):
        """Export with wrapping data key."""
        handler = JSONHandler()
        result = handler.export_data(sample_records, data_key="records")
        data = json.loads(result)
        assert "records" in data
        assert len(data["records"]) == 3

    def test_export_with_schema(self, sample_records, sample_schema):
        """Export uses schema for field ordering."""
        handler = JSONHandler(schema=sample_schema)
        result = handler.export_data(sample_records)
        data = json.loads(result)
        # Should have all schema fields
        assert "id" in data[0]
        assert "name" in data[0]

    def test_export_pretty_print(self, sample_records):
        """Export with pretty printing."""
        handler = JSONHandler(indent=4)
        result = handler.export_data(sample_records)
        assert "\n" in result
        assert "    " in result  # 4-space indent

    def test_export_compact(self, sample_records):
        """Export without pretty printing."""
        handler = JSONHandler()
        result = handler.export_data(sample_records, pretty=False)
        data = json.loads(result)
        assert len(data) == 3

    def test_export_empty_records(self):
        """Export empty record list."""
        handler = JSONHandler()
        result = handler.export_data([])
        data = json.loads(result)
        assert data == []

    def test_export_creates_parent_dirs(self, sample_records, tmp_path):
        """Export creates parent directories."""
        path = tmp_path / "subdir" / "output.json"
        handler = JSONHandler()
        handler.export_data(sample_records, destination=path)
        assert path.exists()


# ── Excel Import Tests ────────────────────────────────────────────────────────


class TestExcelImport:
    """Test Excel import functionality."""

    def _create_test_xlsx(self, path, sheet_name="Sheet1", headers=None, rows=None):
        """Helper to create a minimal XLSX file for testing."""
        if headers is None:
            headers = ["id", "name", "email"]
        if rows is None:
            rows = [[1, "Alice", "alice@test.com"], [2, "Bob", "bob@test.com"]]
        # When headers is an empty list, treat as no header row
        if headers == []:
            headers = None

        # Build shared strings
        shared_strings = []
        string_index = {}

        def get_string_idx(s):
            if s not in string_index:
                string_index[s] = len(shared_strings)
                shared_strings.append(s)
            return string_index[s]

        # Build sheet XML
        ns_main = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        ns_rel = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

        sheet_lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<worksheet xmlns="{ns_main}" xmlns:r="{ns_rel}">',
            "<sheetData>",
        ]

        all_rows = rows if headers is None else [headers] + rows
        for row_idx, row in enumerate(all_rows, start=1):
            sheet_lines.append(f'<row r="{row_idx}">')
            for col_idx, value in enumerate(row):
                col_letter = chr(65 + col_idx)
                cell_ref = f"{col_letter}{row_idx}"
                if isinstance(value, str):
                    idx = get_string_idx(value)
                    sheet_lines.append(f'<c r="{cell_ref}" t="s"><v>{idx}</v></c>')
                elif isinstance(value, bool):
                    sheet_lines.append(f'<c r="{cell_ref}" t="b"><v>{1 if value else 0}</v></c>')
                elif isinstance(value, (int, float)):
                    sheet_lines.append(f'<c r="{cell_ref}"><v>{value}</v></c>')
                else:
                    sheet_lines.append(f'<c r="{cell_ref}" t="s"><v>{get_string_idx(str(value))}</v></c>')
            sheet_lines.append("</row>")

        sheet_lines.append("</sheetData>")
        sheet_lines.append("</worksheet>")
        sheet_xml = "\n".join(sheet_lines)

        # Build shared strings XML
        ss_lines = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<sst xmlns="{ns_main}" count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">',
        ]
        for s in shared_strings:
            ss_lines.append(f"<si><t>{s}</t></si>")
        ss_lines.append("</sst>")
        shared_strings_xml = "\n".join(ss_lines)

        # Build workbook XML
        workbook_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<workbook xmlns="{ns_main}" xmlns:r="{ns_rel}">'
            "<sheets>"
            f'<sheet name="{sheet_name}" sheetId="1" r:id="rId1"/>'
            "</sheets>"
            "</workbook>"
        )

        # Build relationships
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        workbook_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{rel_ns}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            'Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" '
            'Target="sharedStrings.xml"/>'
            "</Relationships>"
        )

        root_rels = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<Relationships xmlns="{rel_ns}">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

        content_types = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/sharedStrings.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
            "</Types>"
        )

        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", root_rels)
            zf.writestr("xl/workbook.xml", workbook_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
            zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
            zf.writestr("xl/sharedStrings.xml", shared_strings_xml)

    def test_import_from_file(self, tmp_path, sample_schema):
        """Import Excel from file."""
        path = tmp_path / "test.xlsx"
        self._create_test_xlsx(path)
        handler = ExcelHandler(schema=sample_schema)
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 2

    def test_import_file_not_found(self):
        """Import raises error for missing file."""
        handler = ExcelHandler()
        with pytest.raises(ImportError):
            handler.import_data("/nonexistent/file.xlsx")

    def test_import_without_schema(self, tmp_path):
        """Import Excel without schema."""
        path = tmp_path / "test.xlsx"
        self._create_test_xlsx(path)
        handler = ExcelHandler()
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 2

    def test_import_without_header(self, tmp_path):
        """Import Excel without header row."""
        schema = DataSchema(
            name="noheader",
            columns=[
                Column(name="id", data_type="integer"),
                Column(name="name", data_type="string"),
            ],
        )
        path = tmp_path / "test.xlsx"
        self._create_test_xlsx(path, headers=[], rows=[[1, "Alice"], [2, "Bob"]])
        handler = ExcelHandler(schema=schema)
        result = handler.import_data(path, has_header=False)
        assert result.success is True
        assert result.records_imported == 2

    def test_import_type_conversion(self, tmp_path):
        """Import converts types based on schema."""
        schema = DataSchema(
            name="typed",
            columns=[
                Column(name="id", data_type="integer"),
                Column(name="score", data_type="float"),
            ],
        )
        path = tmp_path / "typed.xlsx"
        self._create_test_xlsx(path, headers=["id", "score"], rows=[[1, 95.5], [2, 87.3]])
        handler = ExcelHandler(schema=schema)
        result = handler.import_data(path)
        assert result.success is True
        records = result.metadata["records"]
        assert records[0].data["id"] == 1
        assert records[0].data["score"] == 95.5

    def test_import_validation_failure(self, tmp_path):
        """Import with invalid data records failure."""
        schema = DataSchema(
            name="strict",
            columns=[Column(name="id", data_type="integer", required=True)],
        )
        path = tmp_path / "invalid.xlsx"
        self._create_test_xlsx(path, headers=["id", "name"], rows=[[1, "Alice"]])
        handler = ExcelHandler(schema=schema)
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 1


# ── Excel Export Tests ────────────────────────────────────────────────────────


class TestExcelExport:
    """Test Excel export functionality."""

    def test_export_to_file(self, sample_records, tmp_path):
        """Export records to Excel file."""
        path = tmp_path / "output.xlsx"
        handler = ExcelHandler()
        handler.export_data(sample_records, destination=path)
        assert path.exists()
        # Verify it's a valid ZIP (XLSX)
        assert zipfile.is_zipfile(path)

    def test_export_creates_parent_dirs(self, sample_records, tmp_path):
        """Export creates parent directories."""
        path = tmp_path / "subdir" / "nested" / "output.xlsx"
        handler = ExcelHandler()
        handler.export_data(sample_records, destination=path)
        assert path.exists()

    def test_export_with_schema(self, sample_records, sample_schema, tmp_path):
        """Export uses schema for column ordering."""
        path = tmp_path / "output.xlsx"
        handler = ExcelHandler(schema=sample_schema)
        handler.export_data(sample_records, destination=path)
        assert path.exists()

    def test_export_without_header(self, sample_records, tmp_path):
        """Export without header row."""
        path = tmp_path / "output.xlsx"
        handler = ExcelHandler()
        handler.export_data(sample_records, destination=path, include_header=False)
        assert path.exists()

    def test_export_custom_sheet_name(self, sample_records, tmp_path):
        """Export with custom sheet name."""
        path = tmp_path / "output.xlsx"
        handler = ExcelHandler()
        handler.export_data(sample_records, destination=path, sheet_name="CustomSheet")
        assert path.exists()

    def test_export_empty_records(self, tmp_path):
        """Export empty record list."""
        path = tmp_path / "empty.xlsx"
        handler = ExcelHandler()
        handler.export_data([], destination=path)
        assert path.exists()

    def test_export_roundtrip(self, sample_records, tmp_path):
        """Export then import produces same data."""
        path = tmp_path / "roundtrip.xlsx"
        export_handler = ExcelHandler()
        export_handler.export_data(sample_records, destination=path)

        import_handler = ExcelHandler()
        result = import_handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 3

    def test_export_various_types(self, tmp_path):
        """Export handles various data types."""
        records = [
            DataRecord(data={"int_val": 42, "float_val": 3.14, "str_val": "hello", "bool_val": True}),
            DataRecord(data={"int_val": 99, "float_val": 2.71, "str_val": "world", "bool_val": False}),
        ]
        path = tmp_path / "types.xlsx"
        handler = ExcelHandler()
        handler.export_data(records, destination=path)
        assert path.exists()


# ── Cross-format Tests ────────────────────────────────────────────────────────


class TestCrossFormat:
    """Test cross-format import/export consistency."""

    def test_csv_to_json_roundtrip(self, sample_records):
        """Export to CSV then import preserves data."""
        csv_handler = CSVHandler()
        csv_content = csv_handler.export_data(sample_records)

        json_handler = JSONHandler()
        json_content = json_handler.export_data(sample_records)

        # Both should contain the same core data
        assert "Alice" in csv_content
        assert "Alice" in json_content

    def test_all_formats_export_same_data(self, sample_records, tmp_path):
        """All formats export the same logical data."""
        csv_handler = CSVHandler()
        json_handler = JSONHandler()
        excel_handler = ExcelHandler()

        csv_result = csv_handler.export_data(sample_records)
        json_result = json_handler.export_data(sample_records)

        # CSV and JSON should both contain all names
        for record in sample_records:
            assert record.data["name"] in csv_result
            assert record.data["name"] in json_result

    def test_import_csv_export_json(self, csv_file, tmp_path):
        """Import from CSV, export to JSON."""
        csv_handler = CSVHandler()
        import_result = csv_handler.import_data(csv_file)

        records = import_result.metadata["records"]
        json_handler = JSONHandler()
        json_content = json_handler.export_data(records)

        data = json.loads(json_content)
        assert len(data) == 2
        assert data[0]["name"] == "Alice"


# ── Handler Initialization Tests ──────────────────────────────────────────────


class TestHandlerInit:
    """Test handler initialization options."""

    def test_csv_handler_with_delimiter(self):
        """CSV handler accepts custom delimiter."""
        handler = CSVHandler(delimiter=";")
        assert handler.delimiter == ";"

    def test_csv_handler_with_encoding(self):
        """CSV handler accepts custom encoding."""
        handler = CSVHandler(encoding="latin-1")
        assert handler.encoding == "latin-1"

    def test_json_handler_with_indent(self):
        """JSON handler accepts custom indent."""
        handler = JSONHandler(indent=4)
        assert handler.indent == 4

    def test_handlers_with_schema(self, sample_schema):
        """Handlers accept schema at initialization."""
        csv_handler = CSVHandler(schema=sample_schema)
        json_handler = JSONHandler(schema=sample_schema)
        excel_handler = ExcelHandler(schema=sample_schema)
        assert csv_handler.schema is sample_schema
        assert json_handler.schema is sample_schema
        assert excel_handler.schema is sample_schema


# ── Edge Case Tests ───────────────────────────────────────────────────────────


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_csv_with_quoted_fields(self, tmp_path):
        """CSV handles quoted fields with commas."""
        path = tmp_path / "quoted.csv"
        path.write_text('id,name,description\n1,"Doe, John","A person, with commas"\n')
        handler = CSVHandler()
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 1

    def test_csv_with_empty_fields(self, tmp_path):
        """CSV handles empty fields."""
        path = tmp_path / "empty_fields.csv"
        path.write_text("id,name,email\n1,Alice,\n2,,bob@test.com\n")
        handler = CSVHandler()
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 2

    def test_json_with_nested_objects(self, tmp_path):
        """JSON import handles nested objects."""
        path = tmp_path / "nested.json"
        path.write_text('[{"id": 1, "name": "Alice", "address": {"city": "NYC"}}]')
        handler = JSONHandler()
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 1

    def test_json_export_with_datetime(self, tmp_path):
        """JSON export handles datetime values."""
        records = [DataRecord(data={"created": datetime(2024, 1, 15, 10, 30, 0)})]
        handler = JSONHandler()
        result = handler.export_data(records)
        data = json.loads(result)
        assert len(data) == 1

    def test_excel_export_import_roundtrip_with_schema(self, sample_records, sample_schema, tmp_path):
        """Full roundtrip with schema preserves data."""
        path = tmp_path / "roundtrip.xlsx"
        export_handler = ExcelHandler(schema=sample_schema)
        export_handler.export_data(sample_records, destination=path)

        import_handler = ExcelHandler(schema=sample_schema)
        result = import_handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 3

    def test_large_csv_import(self, tmp_path):
        """Import handles larger CSV files."""
        path = tmp_path / "large.csv"
        lines = ["id,name"]
        for i in range(1000):
            lines.append(f"{i},User{i}")
        path.write_text("\n".join(lines))
        handler = CSVHandler()
        result = handler.import_data(path)
        assert result.success is True
        assert result.records_imported == 1000

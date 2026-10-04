"""JSON import/export handler."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from apex_os_bp.data_exchange.exceptions import ImportError, ExportError
from apex_os_bp.data_exchange.models import DataRecord, DataSchema, ImportResult


class JSONHandler:
    """Handler for JSON import and export operations."""

    def __init__(self, schema: Optional[DataSchema] = None, encoding: str = "utf-8", indent: int = 2):
        self.schema = schema
        self.encoding = encoding
        self.indent = indent

    def import_data(
        self,
        source: Union[str, Path],
        schema: Optional[DataSchema] = None,
        data_key: Optional[str] = None,
    ) -> ImportResult:
        """Import data from a JSON file.

        Args:
            source: Path to JSON file.
            schema: Schema for validation. Uses instance schema if not provided.
            data_key: Key containing the array of records. If None, expects a top-level array
                     or a dict with a single array value.

        Returns:
            ImportResult with details of the import operation.
        """
        schema = schema or self.schema
        result = ImportResult(success=True)

        try:
            path = Path(source)
            if not path.exists():
                raise ImportError(f"JSON file not found: {path}")
            content = path.read_text(encoding=self.encoding)
            raw_data = json.loads(content)
        except ImportError:
            raise
        except json.JSONDecodeError as e:
            raise ImportError(f"Invalid JSON: {e}") from e
        except Exception as e:
            raise ImportError(f"Failed to read JSON: {e}") from e

        # Extract records array
        records_data = self._extract_records(raw_data, data_key)

        if not isinstance(records_data, list):
            raise ImportError(f"Expected JSON array of records, got {type(records_data).__name__}")

        # Parse records
        records: List[DataRecord] = []
        for idx, item in enumerate(records_data, start=1):
            if not isinstance(item, dict):
                result.records_failed += 1
                result.add_error(f"Record {idx}: expected object, got {type(item).__name__}")
                continue

            record = DataRecord(data=dict(item), row_number=idx, source="json")

            # Validate against schema
            if schema:
                errors = schema.validate_record(item)
                if errors:
                    result.records_failed += 1
                    for err in errors:
                        result.add_error(f"Record {idx}: {err}")
                    continue

            records.append(record)
            result.records_imported += 1

        result.metadata = {
            "format": "json",
            "total_records": len(records_data),
            "records": records,
        }

        if result.records_failed > 0:
            result.success = False

        return result

    def export_data(
        self,
        records: List[DataRecord],
        destination: Optional[Union[str, Path]] = None,
        schema: Optional[DataSchema] = None,
        data_key: Optional[str] = None,
        pretty: bool = True,
    ) -> Optional[str]:
        """Export data records to JSON format.

        Args:
            records: List of DataRecord objects to export.
            destination: Path to output file. If None, returns JSON string.
            schema: Schema for field ordering/selection.
            data_key: If provided, wrap records in a dict with this key.
            pretty: Whether to format with indentation.

        Returns:
            JSON string if destination is None, otherwise None.
        """
        schema = schema or self.schema

        # Build output data
        output_data: List[Dict[str, Any]] = []
        for record in records:
            if schema:
                ordered = {}
                for col in schema.columns:
                    if col.name in record.data:
                        ordered[col.name] = record.data[col.name]
                # Include extra fields not in schema
                for key, value in record.data.items():
                    if key not in ordered:
                        ordered[key] = value
                output_data.append(ordered)
            else:
                output_data.append(record.to_dict())

        if data_key:
            output_data = {data_key: output_data}

        indent = self.indent if pretty else None
        json_content = json.dumps(output_data, indent=indent, default=str, ensure_ascii=False)

        if destination is None:
            return json_content

        try:
            path = Path(destination)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json_content, encoding=self.encoding)
        except Exception as e:
            raise ExportError(f"Failed to write JSON: {e}") from e

        return None

    def _extract_records(self, raw_data: Any, data_key: Optional[str]) -> Any:
        """Extract the records array from parsed JSON data."""
        if data_key:
            if isinstance(raw_data, dict) and data_key in raw_data:
                return raw_data[data_key]
            raise ImportError(f"Key '{data_key}' not found in JSON data")

        if isinstance(raw_data, list):
            return raw_data

        if isinstance(raw_data, dict):
            # Try common keys
            for key in ("data", "records", "items", "results"):
                if key in raw_data and isinstance(raw_data[key], list):
                    return raw_data[key]
            # If dict has a single list value, use that
            list_values = [v for v in raw_data.values() if isinstance(v, list)]
            if len(list_values) == 1:
                return list_values[0]

        return raw_data

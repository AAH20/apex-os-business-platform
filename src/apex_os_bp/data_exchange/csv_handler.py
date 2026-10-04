"""CSV import/export handler."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from apex_os_bp.data_exchange.exceptions import ImportError, ExportError
from apex_os_bp.data_exchange.models import DataRecord, DataSchema, ImportResult


class CSVHandler:
    """Handler for CSV import and export operations."""

    def __init__(self, schema: Optional[DataSchema] = None, delimiter: str = ",", encoding: str = "utf-8"):
        self.schema = schema
        self.delimiter = delimiter
        self.encoding = encoding

    def import_data(
        self,
        source: Union[str, Path, io.StringIO],
        schema: Optional[DataSchema] = None,
        has_header: bool = True,
        skip_rows: int = 0,
    ) -> ImportResult:
        """Import data from a CSV file or string buffer.

        Args:
            source: Path to CSV file or StringIO buffer.
            schema: Schema for validation. Uses instance schema if not provided.
            has_header: Whether the first row is a header.
            skip_rows: Number of rows to skip at the beginning.

        Returns:
            ImportResult with details of the import operation.
        """
        schema = schema or self.schema
        result = ImportResult(success=True)

        try:
            if isinstance(source, (str, Path)):
                path = Path(source)
                if not path.exists():
                    raise ImportError(f"CSV file not found: {path}")
                content = path.read_text(encoding=self.encoding)
                reader = csv.reader(io.StringIO(content), delimiter=self.delimiter)
            else:
                reader = csv.reader(source, delimiter=self.delimiter)

            rows = list(reader)
        except ImportError:
            raise
        except Exception as e:
            raise ImportError(f"Failed to read CSV: {e}") from e

        if skip_rows > 0:
            rows = rows[skip_rows:]

        if not rows:
            result.add_warning("CSV file is empty")
            return result

        # Determine headers
        if has_header:
            headers = [h.strip() for h in rows[0]]
            data_rows = rows[1:]
        else:
            if schema:
                headers = [col.name for col in schema.columns]
            else:
                headers = [f"column_{i}" for i in range(len(rows[0]))]
            data_rows = rows

        # Validate headers against schema
        if schema:
            schema_cols = {col.name for col in schema.columns}
            for header in headers:
                if header not in schema_cols:
                    result.add_warning(f"Column '{header}' not found in schema")

        # Parse data rows
        records: List[DataRecord] = []
        for row_idx, row in enumerate(data_rows, start=2 if has_header else 1):
            record_data: Dict[str, Any] = {}
            for col_idx, header in enumerate(headers):
                value = row[col_idx].strip() if col_idx < len(row) else ""
                # Type conversion based on schema
                if schema:
                    col = schema.get_column(header)
                    if col and value:
                        value = self._convert_value(value, col.data_type)
                record_data[header] = value

            record = DataRecord(data=record_data, row_number=row_idx, source="csv")

            # Validate against schema
            if schema:
                errors = schema.validate_record(record_data)
                if errors:
                    result.records_failed += 1
                    for err in errors:
                        result.add_error(f"Row {row_idx}: {err}")
                    continue

            records.append(record)
            result.records_imported += 1

        result.metadata = {
            "format": "csv",
            "headers": headers,
            "total_rows": len(data_rows),
            "records": records,
        }

        if result.records_failed > 0:
            result.success = False

        return result

    def export_data(
        self,
        records: List[DataRecord],
        destination: Optional[Union[str, Path, io.StringIO]] = None,
        schema: Optional[DataSchema] = None,
        include_header: bool = True,
    ) -> Optional[str]:
        """Export data records to CSV format.

        Args:
            records: List of DataRecord objects to export.
            destination: Path to output file or StringIO buffer. If None, returns CSV string.
            schema: Schema for column ordering. Uses instance schema if not provided.
            include_header: Whether to include a header row.

        Returns:
            CSV string if destination is None, otherwise None.
        """
        schema = schema or self.schema

        output = io.StringIO()
        writer = csv.writer(output, delimiter=self.delimiter)

        # Determine headers
        if schema:
            headers = [col.name for col in schema.columns]
        elif records:
            headers = list(records[0].data.keys())
        else:
            headers = []

        if include_header and headers:
            writer.writerow(headers)

        for record in records:
            row = []
            for header in headers:
                value = record.data.get(header, "")
                if value is None:
                    value = ""
                row.append(str(value))
            writer.writerow(row)

        csv_content = output.getvalue()

        if destination is None:
            return csv_content

        try:
            if isinstance(destination, (str, Path)):
                path = Path(destination)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(csv_content, encoding=self.encoding)
            else:
                destination.write(csv_content)
        except Exception as e:
            raise ExportError(f"Failed to write CSV: {e}") from e

        return None

    def _convert_value(self, value: str, data_type: str) -> Any:
        """Convert a string value to the appropriate type."""
        if not value:
            return value
        try:
            if data_type == "integer":
                return int(value)
            elif data_type == "float":
                return float(value)
            elif data_type == "boolean":
                return value.lower() in ("true", "1", "yes")
            elif data_type == "date":
                from datetime import datetime
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            else:
                return value
        except (ValueError, TypeError):
            return value

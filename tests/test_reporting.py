"""Tests for the APEX-OS reporting system."""

from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from apex_os_bp.reporting.builder import (
    ReportBuilder,
    ReportColumn,
    ReportDefinition,
    ReportFilter,
    ReportResult,
    ReportStatus,
    ReportType,
)
from apex_os_bp.reporting.distributor import (
    DistributionChannel,
    DistributionConfig,
    DistributionResult,
    DistributionStatus,
    ReportDistributor,
)
from apex_os_bp.reporting.exporter import (
    ExportFormat,
    ExportResult,
    ReportExporter,
)
from apex_os_bp.reporting.scheduler import (
    ReportScheduler,
    ScheduleConfig,
    ScheduleFrequency,
    ScheduleRun,
    ScheduleStatus,
)
from apex_os_bp.reporting.templates import (
    ReportTemplate,
    TemplateRegistry,
)


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

SAMPLE_SALES_DATA = [
    {"region": "North", "product": "Widget", "total_sales": 1000, "order_count": 10},
    {"region": "North", "product": "Gadget", "total_sales": 2000, "order_count": 20},
    {"region": "South", "product": "Widget", "total_sales": 1500, "order_count": 15},
    {"region": "South", "product": "Gadget", "total_sales": 500, "order_count": 5},
    {"region": "East", "product": "Widget", "total_sales": 3000, "order_count": 30},
    {"region": "East", "product": "Gadget", "total_sales": 2500, "order_count": 25},
]


def _make_columns() -> list[ReportColumn]:
    return [
        ReportColumn("region", "Region", "string"),
        ReportColumn("product", "Product", "string"),
        ReportColumn("total_sales", "Total Sales", "number"),
        ReportColumn("order_count", "Order Count", "integer"),
    ]


def _make_definition(
    name: str = "Test Report",
    data_source: str = "test_source",
    filters: list[ReportFilter] | None = None,
    group_by: list[str] | None = None,
    order_by: list[str] | None = None,
    limit: int | None = None,
) -> ReportDefinition:
    return ReportDefinition(
        name=name,
        report_type=ReportType.SUMMARY,
        columns=_make_columns(),
        data_source=data_source,
        filters=filters or [],
        group_by=group_by or [],
        order_by=order_by or [],
        limit=limit,
    )


# ===================================================================
# 1. Report Builder Tests
# ===================================================================

class TestReportBuilder(unittest.TestCase):
    """Tests for ReportBuilder."""

    def setUp(self) -> None:
        self.builder = ReportBuilder()
        self.builder.register_data_source("test_source", SAMPLE_SALES_DATA)

    def test_register_data_source(self) -> None:
        src = [{"a": 1}]
        self.builder.register_data_source("extra", src)
        # Should not raise

    def test_create_definition(self) -> None:
        defn = self.builder.create_definition(
            name="My Report",
            report_type=ReportType.DETAIL,
            columns=_make_columns(),
            data_source="test_source",
        )
        self.assertEqual(defn.name, "My Report")
        self.assertEqual(defn.report_type, ReportType.DETAIL)
        self.assertEqual(len(defn.columns), 4)
        self.assertEqual(defn.status, ReportStatus.DRAFT)

    def test_build_basic(self) -> None:
        defn = _make_definition()
        result = self.builder.build(defn)
        self.assertEqual(result.status, ReportStatus.READY)
        self.assertEqual(result.total_count, 6)
        self.assertEqual(len(result.rows), 6)
        self.assertIsNone(result.error)
        self.assertGreater(result.execution_time_ms, 0)

    def test_build_with_limit(self) -> None:
        defn = _make_definition(limit=3)
        result = self.builder.build(defn)
        self.assertEqual(result.total_count, 6)
        self.assertEqual(len(result.rows), 3)

    def test_build_with_ordering(self) -> None:
        defn = _make_definition(order_by=["-total_sales"])
        result = self.builder.build(defn)
        sales = [r["total_sales"] for r in result.rows]
        self.assertEqual(sales, sorted(sales, reverse=True))

    def test_build_with_grouping(self) -> None:
        defn = _make_definition(group_by=["region"])
        result = self.builder.build(defn)
        self.assertEqual(len(result.rows), 3)  # 3 unique regions
        for row in result.rows:
            self.assertIn("_count", row)
            self.assertIn("_items", row)

    def test_build_with_filter_eq(self) -> None:
        defn = _make_definition(
            filters=[ReportFilter("region", "eq", "North")]
        )
        result = self.builder.build(defn)
        self.assertEqual(result.total_count, 2)
        for row in result.rows:
            self.assertEqual(row["region"], "North")

    def test_build_with_filter_gt(self) -> None:
        defn = _make_definition(
            filters=[ReportFilter("total_sales", "gt", 1500)]
        )
        result = self.builder.build(defn)
        self.assertEqual(result.total_count, 3)

    def test_build_with_filter_in(self) -> None:
        defn = _make_definition(
            filters=[ReportFilter("region", "in", ["North", "South"])]
        )
        result = self.builder.build(defn)
        self.assertEqual(result.total_count, 4)

    def test_build_with_filter_contains(self) -> None:
        defn = _make_definition(
            filters=[ReportFilter("product", "contains", "adget")]
        )
        result = self.builder.build(defn)
        self.assertEqual(result.total_count, 3)  # Gadget rows

    def test_build_unknown_data_source(self) -> None:
        defn = _make_definition(data_source="nonexistent")
        result = self.builder.build(defn)
        self.assertEqual(result.status, ReportStatus.FAILED)
        self.assertIsNotNone(result.error)
        self.assertIn("nonexistent", result.error)

    def test_build_with_dict_source(self) -> None:
        self.builder.register_data_source("dict_src", {"key": "value"})
        defn = _make_definition(data_source="dict_src")
        result = self.builder.build(defn)
        self.assertEqual(result.status, ReportStatus.READY)
        self.assertEqual(len(result.rows), 1)

    def test_build_with_query_source(self) -> None:
        mock_source = MagicMock()
        mock_source.query.return_value = SAMPLE_SALES_DATA
        self.builder.register_data_source("query_src", mock_source)
        defn = _make_definition(data_source="query_src")
        result = self.builder.build(defn)
        self.assertEqual(result.status, ReportStatus.READY)
        mock_source.query.assert_called_once()

    def test_build_with_get_all_source(self) -> None:
        mock_source = MagicMock()
        mock_source.get_all.return_value = SAMPLE_SALES_DATA
        # Remove query attribute so get_all is used
        del mock_source.query
        self.builder.register_data_source("getall_src", mock_source)
        defn = _make_definition(data_source="getall_src")
        result = self.builder.build(defn)
        self.assertEqual(result.status, ReportStatus.READY)
        mock_source.get_all.assert_called_once()

    def test_build_unsupported_source_type(self) -> None:
        self.builder.register_data_source("bad_src", 42)
        defn = _make_definition(data_source="bad_src")
        result = self.builder.build(defn)
        self.assertEqual(result.status, ReportStatus.FAILED)

    def test_get_history(self) -> None:
        defn = _make_definition()
        self.builder.build(defn)
        history = self.builder.get_history()
        self.assertEqual(len(history), 1)

    def test_get_history_by_status(self) -> None:
        defn_ok = _make_definition()
        self.builder.build(defn_ok)
        defn_fail = _make_definition(data_source="missing")
        self.builder.build(defn_fail)
        ready = self.builder.get_history_by_status(ReportStatus.READY)
        failed = self.builder.get_history_by_status(ReportStatus.FAILED)
        self.assertEqual(len(ready), 1)
        self.assertEqual(len(failed), 1)

    def test_multiple_filters(self) -> None:
        defn = _make_definition(
            filters=[
                ReportFilter("region", "eq", "North"),
                ReportFilter("total_sales", "gte", 1500),
            ]
        )
        result = self.builder.build(defn)
        self.assertEqual(result.total_count, 1)
        self.assertEqual(result.rows[0]["product"], "Gadget")

    def test_ordering_ascending(self) -> None:
        defn = _make_definition(order_by=["total_sales"])
        result = self.builder.build(defn)
        sales = [r["total_sales"] for r in result.rows]
        self.assertEqual(sales, sorted(sales))

    def test_definition_has_uuid(self) -> None:
        defn = _make_definition()
        self.assertIsInstance(defn.id, str)
        self.assertTrue(len(defn.id) > 0)

    def test_definition_timestamps(self) -> None:
        defn = _make_definition()
        self.assertIsInstance(defn.created_at, datetime)


# ===================================================================
# 2. Report Scheduler Tests
# ===================================================================

class TestReportScheduler(unittest.TestCase):
    """Tests for ReportScheduler."""

    def setUp(self) -> None:
        self.scheduler = ReportScheduler()

    def tearDown(self) -> None:
        self.scheduler.stop()

    def test_create_schedule(self) -> None:
        config = ScheduleConfig(
            name="Daily Report",
            frequency=ScheduleFrequency.DAILY,
            report_definition_id="def-123",
        )
        result = self.scheduler.create_schedule(config)
        self.assertEqual(result.name, "Daily Report")
        self.assertIsNotNone(result.id)
        self.assertEqual(result.status, ScheduleStatus.PENDING)

    def test_create_schedule_cron_requires_expression(self) -> None:
        with self.assertRaises(ValueError):
            self.scheduler.create_schedule(ScheduleConfig(
                name="Cron Report",
                frequency=ScheduleFrequency.CRON,
                report_definition_id="def-123",
            ))

    def test_create_schedule_cron_with_expression(self) -> None:
        config = ScheduleConfig(
            name="Cron Report",
            frequency=ScheduleFrequency.CRON,
            report_definition_id="def-123",
            cron_expression="0 0 * * *",
        )
        result = self.scheduler.create_schedule(config)
        self.assertEqual(result.frequency, ScheduleFrequency.CRON)

    def test_cancel_schedule(self) -> None:
        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        self.assertTrue(self.scheduler.cancel_schedule(created.id))
        self.assertEqual(
            self.scheduler.get_schedule(created.id).status,
            ScheduleStatus.CANCELLED,
        )

    def test_cancel_nonexistent(self) -> None:
        self.assertFalse(self.scheduler.cancel_schedule("no-such-id"))

    def test_pause_and_resume(self) -> None:
        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.DAILY,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        self.assertTrue(self.scheduler.pause_schedule(created.id))
        self.assertEqual(
            self.scheduler.get_schedule(created.id).status,
            ScheduleStatus.PAUSED,
        )
        self.assertTrue(self.scheduler.resume_schedule(created.id))
        self.assertEqual(
            self.scheduler.get_schedule(created.id).status,
            ScheduleStatus.PENDING,
        )

    def test_delete_schedule(self) -> None:
        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        self.assertTrue(self.scheduler.delete_schedule(created.id))
        self.assertIsNone(self.scheduler.get_schedule(created.id))

    def test_delete_nonexistent(self) -> None:
        self.assertFalse(self.scheduler.delete_schedule("no-such-id"))

    def test_get_schedule(self) -> None:
        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.HOURLY,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        fetched = self.scheduler.get_schedule(created.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, created.id)

    def test_list_schedules(self) -> None:
        for i in range(3):
            self.scheduler.create_schedule(ScheduleConfig(
                name=f"Schedule {i}",
                frequency=ScheduleFrequency.DAILY,
                report_definition_id=f"def-{i}",
            ))
        schedules = self.scheduler.list_schedules()
        self.assertEqual(len(schedules), 3)

    def test_list_schedules_filtered(self) -> None:
        self.scheduler.create_schedule(ScheduleConfig(
            name="Active",
            frequency=ScheduleFrequency.DAILY,
            report_definition_id="def-1",
        ))
        paused = self.scheduler.create_schedule(ScheduleConfig(
            name="Paused",
            frequency=ScheduleFrequency.DAILY,
            report_definition_id="def-2",
        ))
        self.scheduler.pause_schedule(paused.id)
        pending = self.scheduler.list_schedules(ScheduleStatus.PENDING)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].name, "Active")

    def test_execute_now(self) -> None:
        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        run = self.scheduler.execute_now(created.id)
        self.assertIsNotNone(run)
        self.assertEqual(run.status, ScheduleStatus.COMPLETED)
        self.assertIsNotNone(run.completed_at)

    def test_execute_now_nonexistent(self) -> None:
        run = self.scheduler.execute_now("no-such-id")
        self.assertIsNone(run)

    def test_execute_now_cancelled(self) -> None:
        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        self.scheduler.cancel_schedule(created.id)
        run = self.scheduler.execute_now(created.id)
        self.assertIsNone(run)

    def test_get_runs(self) -> None:
        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        self.scheduler.execute_now(created.id)
        self.scheduler.execute_now(created.id)
        runs = self.scheduler.get_runs(created.id)
        self.assertEqual(len(runs), 2)

    def test_register_callback(self) -> None:
        callback_runs: list[ScheduleRun] = []

        def cb(run: ScheduleRun) -> None:
            callback_runs.append(run)

        config = ScheduleConfig(
            name="Test",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        self.scheduler.register_callback(created.id, cb)
        self.scheduler.execute_now(created.id)
        self.assertEqual(len(callback_runs), 1)

    def test_next_run_computation_hourly(self) -> None:
        config = ScheduleConfig(
            name="Hourly",
            frequency=ScheduleFrequency.HOURLY,
            report_definition_id="def-123",
            start_time=datetime(2026, 1, 1, 0, 0, 0),
        )
        created = self.scheduler.create_schedule(config)
        self.assertIsNotNone(created.next_run)
        self.assertEqual(created.next_run, datetime(2026, 1, 1, 1, 0, 0))

    def test_next_run_computation_daily(self) -> None:
        config = ScheduleConfig(
            name="Daily",
            frequency=ScheduleFrequency.DAILY,
            report_definition_id="def-123",
            start_time=datetime(2026, 1, 1, 0, 0, 0),
        )
        created = self.scheduler.create_schedule(config)
        self.assertEqual(created.next_run, datetime(2026, 1, 2, 0, 0, 0))

    def test_next_run_computation_weekly(self) -> None:
        config = ScheduleConfig(
            name="Weekly",
            frequency=ScheduleFrequency.WEEKLY,
            report_definition_id="def-123",
            start_time=datetime(2026, 1, 1, 0, 0, 0),
        )
        created = self.scheduler.create_schedule(config)
        self.assertEqual(created.next_run, datetime(2026, 1, 8, 0, 0, 0))

    def test_next_run_computation_monthly(self) -> None:
        config = ScheduleConfig(
            name="Monthly",
            frequency=ScheduleFrequency.MONTHLY,
            report_definition_id="def-123",
            start_time=datetime(2026, 1, 1, 0, 0, 0),
        )
        created = self.scheduler.create_schedule(config)
        self.assertEqual(created.next_run, datetime(2026, 1, 31, 0, 0, 0))

    def test_next_run_none_for_once(self) -> None:
        config = ScheduleConfig(
            name="Once",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id="def-123",
        )
        created = self.scheduler.create_schedule(config)
        self.assertIsNone(created.next_run)

    def test_max_runs(self) -> None:
        config = ScheduleConfig(
            name="Limited",
            frequency=ScheduleFrequency.HOURLY,
            report_definition_id="def-123",
            max_runs=2,
        )
        created = self.scheduler.create_schedule(config)
        self.scheduler.execute_now(created.id)
        self.scheduler.execute_now(created.id)
        self.assertEqual(created.run_count, 2)

    def test_background_start_stop(self) -> None:
        self.scheduler.start()
        self.assertTrue(self.scheduler._running)
        self.scheduler.stop()
        self.assertFalse(self.scheduler._running)

    def test_schedule_with_end_time(self) -> None:
        config = ScheduleConfig(
            name="Bounded",
            frequency=ScheduleFrequency.DAILY,
            report_definition_id="def-123",
            start_time=datetime(2026, 1, 1),
            end_time=datetime(2026, 12, 31),
        )
        created = self.scheduler.create_schedule(config)
        self.assertEqual(created.end_time, datetime(2026, 12, 31))


# ===================================================================
# 3. Report Exporter Tests
# ===================================================================

class TestReportExporter(unittest.TestCase):
    """Tests for ReportExporter."""

    def setUp(self) -> None:
        self.builder = ReportBuilder()
        self.builder.register_data_source("test_source", SAMPLE_SALES_DATA)
        defn = _make_definition()
        self.result = self.builder.build(defn)
        self.exporter = ReportExporter(output_dir=tempfile.mkdtemp())

    def test_export_csv(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.CSV, "test_csv")
        self.assertIsNone(result.error)
        self.assertTrue(os.path.exists(result.file_path))
        self.assertTrue(result.file_path.endswith(".csv"))
        self.assertGreater(result.file_size, 0)
        self.assertEqual(result.row_count, 6)
        self.assertEqual(result.format, ExportFormat.CSV)

    def test_export_csv_content(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.CSV, "test_csv_content")
        with open(result.file_path, "r") as f:
            content = f.read()
        self.assertIn("region", content)
        self.assertIn("product", content)
        self.assertIn("North", content)

    def test_export_json(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.JSON, "test_json")
        self.assertIsNone(result.error)
        self.assertTrue(os.path.exists(result.file_path))
        self.assertTrue(result.file_path.endswith(".json"))
        import json
        with open(result.file_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["report_name"], "Test Report")
        self.assertEqual(data["total_count"], 6)
        self.assertEqual(len(data["rows"]), 6)

    def test_export_html(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.HTML, "test_html")
        self.assertIsNone(result.error)
        self.assertTrue(os.path.exists(result.file_path))
        self.assertTrue(result.file_path.endswith(".html"))
        with open(result.file_path, "r") as f:
            content = f.read()
        self.assertIn("<html>", content)
        self.assertIn("Test Report", content)
        self.assertIn("North", content)

    def test_export_excel(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.EXCEL, "test_excel")
        self.assertIsNone(result.error)
        self.assertTrue(os.path.exists(result.file_path))
        self.assertTrue(
            result.file_path.endswith(".xlsx") or result.file_path.endswith(".xls")
        )
        self.assertGreater(result.file_size, 0)

    def test_export_pdf(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.PDF, "test_pdf")
        self.assertIsNone(result.error)
        self.assertTrue(os.path.exists(result.file_path))
        self.assertTrue(result.file_path.endswith(".pdf"))
        self.assertGreater(result.file_size, 0)

    def test_export_auto_filename(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.CSV)
        self.assertIsNone(result.error)
        self.assertTrue(os.path.exists(result.file_path))

    def test_export_unsupported_format(self) -> None:
        result = self.exporter.export(self.result, "xml")  # type: ignore
        self.assertIsNotNone(result.error)

    def test_get_history(self) -> None:
        self.exporter.export(self.result, ExportFormat.CSV, "hist1")
        self.exporter.export(self.result, ExportFormat.JSON, "hist2")
        history = self.exporter.get_history()
        self.assertEqual(len(history), 2)

    def test_get_history_by_format(self) -> None:
        self.exporter.export(self.result, ExportFormat.CSV, "f1")
        self.exporter.export(self.result, ExportFormat.CSV, "f2")
        self.exporter.export(self.result, ExportFormat.JSON, "f3")
        csv_history = self.exporter.get_history_by_format(ExportFormat.CSV)
        self.assertEqual(len(csv_history), 2)

    def test_export_result_has_uuid(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.CSV, "uuid_test")
        self.assertIsInstance(result.id, str)
        self.assertTrue(len(result.id) > 0)

    def test_export_result_timestamp(self) -> None:
        result = self.exporter.export(self.result, ExportFormat.CSV, "ts_test")
        self.assertIsInstance(result.generated_at, datetime)

    def test_export_empty_result(self) -> None:
        empty_result = ReportResult(
            definition=_make_definition(),
            rows=[],
            total_count=0,
        )
        result = self.exporter.export(empty_result, ExportFormat.CSV, "empty")
        self.assertIsNone(result.error)
        self.assertEqual(result.row_count, 0)


# ===================================================================
# 4. Report Templates Tests
# ===================================================================

class TestReportTemplates(unittest.TestCase):
    """Tests for ReportTemplate and TemplateRegistry."""

    def setUp(self) -> None:
        self.registry = TemplateRegistry()

    def test_register_template(self) -> None:
        template = ReportTemplate(
            name="Custom",
            description="A custom template",
            report_type=ReportType.CUSTOM,
            columns=[ReportColumn("id", "ID", "string")],
            data_source="test",
        )
        self.registry.register(template)
        fetched = self.registry.get(template.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Custom")

    def test_unregister_template(self) -> None:
        template = ReportTemplate(
            name="Temp",
            description="Temporary",
            report_type=ReportType.CUSTOM,
            columns=[ReportColumn("id", "ID", "string")],
            data_source="test",
        )
        self.registry.register(template)
        self.assertTrue(self.registry.unregister(template.id))
        self.assertIsNone(self.registry.get(template.id))

    def test_unregister_nonexistent(self) -> None:
        self.assertFalse(self.registry.unregister("no-such-id"))

    def test_get_by_name(self) -> None:
        template = self.registry.get_by_name("Sales Summary")
        self.assertIsNotNone(template)
        self.assertEqual(template.report_type, ReportType.SUMMARY)

    def test_get_by_name_not_found(self) -> None:
        self.assertIsNone(self.registry.get_by_name("Nonexistent"))

    def test_list_templates(self) -> None:
        templates = self.registry.list_templates()
        self.assertGreaterEqual(len(templates), 5)

    def test_list_templates_filtered(self) -> None:
        summaries = self.registry.list_templates(ReportType.SUMMARY)
        self.assertGreaterEqual(len(summaries), 2)
        for t in summaries:
            self.assertEqual(t.report_type, ReportType.SUMMARY)

    def test_instantiate(self) -> None:
        template = self.registry.get_by_name("Sales Summary")
        self.assertIsNotNone(template)
        defn = template.instantiate(name="Q1 Sales")
        self.assertEqual(defn.name, "Q1 Sales")
        self.assertEqual(defn.report_type, ReportType.SUMMARY)
        self.assertEqual(len(defn.columns), 5)
        self.assertEqual(defn.data_source, "sales_db")

    def test_instantiate_with_overrides(self) -> None:
        template = self.registry.get_by_name("Sales Summary")
        self.assertIsNotNone(template)
        custom_filters = [ReportFilter("region", "eq", "West")]
        defn = template.instantiate(
            name="West Sales",
            filters=custom_filters,
            limit=50,
            metadata={"quarter": "Q1"},
        )
        self.assertEqual(defn.name, "West Sales")
        self.assertEqual(len(defn.filters), 1)
        self.assertEqual(defn.limit, 50)
        self.assertEqual(defn.metadata.get("quarter"), "Q1")

    def test_create_from_template(self) -> None:
        template = self.registry.get_by_name("User Activity")
        self.assertIsNotNone(template)
        defn = self.registry.create_from_template(
            template.id,
            name="Daily Users",
        )
        self.assertIsNotNone(defn)
        self.assertEqual(defn.name, "Daily Users")

    def test_create_from_template_not_found(self) -> None:
        defn = self.registry.create_from_template("no-such-id")
        self.assertIsNone(defn)

    def test_default_templates_registered(self) -> None:
        names = [t.name for t in self.registry.list_templates()]
        self.assertIn("Sales Summary", names)
        self.assertIn("User Activity", names)
        self.assertIn("Audit Trail", names)
        self.assertIn("Revenue Detail", names)
        self.assertIn("Inventory Status", names)

    def test_template_has_uuid(self) -> None:
        template = ReportTemplate(
            name="Test",
            description="Test",
            report_type=ReportType.CUSTOM,
            columns=[],
            data_source="test",
        )
        self.assertIsInstance(template.id, str)
        self.assertTrue(len(template.id) > 0)

    def test_template_version(self) -> None:
        template = ReportTemplate(
            name="Versioned",
            description="Test",
            report_type=ReportType.CUSTOM,
            columns=[],
            data_source="test",
            version=3,
        )
        self.assertEqual(template.version, 3)

    def test_template_default_filters(self) -> None:
        template = self.registry.get_by_name("Inventory Status")
        self.assertIsNotNone(template)
        self.assertGreater(len(template.default_filters), 0)


# ===================================================================
# 5. Report Distributor Tests
# ===================================================================

class TestReportDistributor(unittest.TestCase):
    """Tests for ReportDistributor."""

    def setUp(self) -> None:
        self.distributor = ReportDistributor()
        self.exporter = ReportExporter(output_dir=tempfile.mkdtemp())
        builder = ReportBuilder()
        builder.register_data_source("test_source", SAMPLE_SALES_DATA)
        defn = _make_definition()
        report_result = builder.build(defn)
        self.export_result = self.exporter.export(
            report_result, ExportFormat.CSV, "dist_test"
        )

    def test_add_config(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.EMAIL,
            name="Email Config",
            to_addresses=["test@example.com"],
        )
        result = self.distributor.add_config(config)
        self.assertEqual(result.name, "Email Config")
        self.assertTrue(result.enabled)

    def test_remove_config(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.EMAIL,
            name="Temp",
        )
        added = self.distributor.add_config(config)
        self.assertTrue(self.distributor.remove_config(added.id))
        self.assertIsNone(self.distributor.get_config(added.id))

    def test_remove_nonexistent(self) -> None:
        self.assertFalse(self.distributor.remove_config("no-such-id"))

    def test_get_config(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.WEBHOOK,
            name="Webhook",
            webhook_url="https://example.com/hook",
        )
        added = self.distributor.add_config(config)
        fetched = self.distributor.get_config(added.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.channel, DistributionChannel.WEBHOOK)

    def test_list_configs(self) -> None:
        self.distributor.add_config(DistributionConfig(
            channel=DistributionChannel.EMAIL, name="E1"
        ))
        self.distributor.add_config(DistributionConfig(
            channel=DistributionChannel.SLACK, name="S1"
        ))
        configs = self.distributor.list_configs()
        self.assertEqual(len(configs), 2)

    def test_list_configs_filtered(self) -> None:
        self.distributor.add_config(DistributionConfig(
            channel=DistributionChannel.EMAIL, name="E1"
        ))
        self.distributor.add_config(DistributionConfig(
            channel=DistributionChannel.EMAIL, name="E2"
        ))
        self.distributor.add_config(DistributionConfig(
            channel=DistributionChannel.SLACK, name="S1"
        ))
        email_configs = self.distributor.list_configs(DistributionChannel.EMAIL)
        self.assertEqual(len(email_configs), 2)

    def test_distribute_nonexistent_config(self) -> None:
        result = self.distributor.distribute("no-such-id", self.export_result)
        self.assertEqual(result.status, DistributionStatus.FAILED)
        self.assertIsNotNone(result.error)

    def test_distribute_disabled_config(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.EMAIL,
            name="Disabled",
            enabled=False,
        )
        added = self.distributor.add_config(config)
        result = self.distributor.distribute(added.id, self.export_result)
        self.assertEqual(result.status, DistributionStatus.FAILED)
        self.assertIn("disabled", result.error.lower())

    @patch("smtplib.SMTP")
    def test_distribute_email(self, mock_smtp: MagicMock) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.EMAIL,
            name="Email Test",
            smtp_host="localhost",
            smtp_port=25,
            from_address="reports@test.com",
            to_addresses=["user@test.com"],
        )
        added = self.distributor.add_config(config)
        result = self.distributor.distribute(
            added.id, self.export_result, subject="Test Report"
        )
        self.assertEqual(result.status, DistributionStatus.SENT)
        self.assertIsNone(result.error)

    @patch("urllib.request.urlopen")
    def test_distribute_webhook(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value = mock_resp
        config = DistributionConfig(
            channel=DistributionChannel.WEBHOOK,
            name="Webhook Test",
            webhook_url="https://example.com/webhook",
        )
        added = self.distributor.add_config(config)
        result = self.distributor.distribute(added.id, self.export_result)
        self.assertEqual(result.status, DistributionStatus.SENT)

    def test_distribute_file_share(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = DistributionConfig(
                channel=DistributionChannel.FILE_SHARE,
                name="File Share Test",
                file_share_path=tmpdir,
            )
            added = self.distributor.add_config(config)
            result = self.distributor.distribute(added.id, self.export_result)
            self.assertEqual(result.status, DistributionStatus.SENT)
            # Verify file was copied
            files = os.listdir(tmpdir)
            self.assertTrue(len(files) > 0)

    @patch("urllib.request.urlopen")
    def test_distribute_slack(self, mock_urlopen: MagicMock) -> None:
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"ok"
        mock_urlopen.return_value = mock_resp
        config = DistributionConfig(
            channel=DistributionChannel.SLACK,
            name="Slack Test",
            slack_webhook_url="https://hooks.slack.com/test",
            slack_channel="#reports",
        )
        added = self.distributor.add_config(config)
        result = self.distributor.distribute(added.id, self.export_result)
        self.assertEqual(result.status, DistributionStatus.SENT)

    def test_get_history(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.FILE_SHARE,
            name="Hist",
            file_share_path=tempfile.mkdtemp(),
        )
        added = self.distributor.add_config(config)
        self.distributor.distribute(added.id, self.export_result)
        self.distributor.distribute(added.id, self.export_result)
        history = self.distributor.get_history()
        self.assertEqual(len(history), 2)

    def test_get_history_by_config(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.FILE_SHARE,
            name="Filtered",
            file_share_path=tempfile.mkdtemp(),
        )
        added = self.distributor.add_config(config)
        self.distributor.distribute(added.id, self.export_result)
        history = self.distributor.get_history(added.id)
        self.assertEqual(len(history), 1)

    def test_get_history_by_status(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.FILE_SHARE,
            name="Status",
            file_share_path=tempfile.mkdtemp(),
        )
        added = self.distributor.add_config(config)
        self.distributor.distribute(added.id, self.export_result)
        sent = self.distributor.get_history_by_status(DistributionStatus.SENT)
        self.assertEqual(len(sent), 1)

    def test_distribution_result_has_uuid(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.FILE_SHARE,
            name="UUID",
            file_share_path=tempfile.mkdtemp(),
        )
        added = self.distributor.add_config(config)
        result = self.distributor.distribute(added.id, self.export_result)
        self.assertIsInstance(result.id, str)
        self.assertTrue(len(result.id) > 0)

    def test_distribution_result_timestamp(self) -> None:
        config = DistributionConfig(
            channel=DistributionChannel.FILE_SHARE,
            name="Timestamp",
            file_share_path=tempfile.mkdtemp(),
        )
        added = self.distributor.add_config(config)
        result = self.distributor.distribute(added.id, self.export_result)
        self.assertIsInstance(result.sent_at, datetime)


# ===================================================================
# Integration Tests
# ===================================================================

class TestReportingIntegration(unittest.TestCase):
    """End-to-end integration tests for the reporting pipeline."""

    def test_full_pipeline(self) -> None:
        """Build -> Export -> Distribute."""
        # 1. Build
        builder = ReportBuilder()
        builder.register_data_source("sales", SAMPLE_SALES_DATA)
        defn = builder.create_definition(
            name="Pipeline Report",
            report_type=ReportType.SUMMARY,
            columns=_make_columns(),
            data_source="sales",
            order_by=["-total_sales"],
        )
        result = builder.build(defn)
        self.assertEqual(result.status, ReportStatus.READY)

        # 2. Export
        exporter = ReportExporter(output_dir=tempfile.mkdtemp())
        export_result = exporter.export(result, ExportFormat.CSV, "pipeline")
        self.assertIsNone(export_result.error)
        self.assertTrue(os.path.exists(export_result.file_path))

        # 3. Distribute
        distributor = ReportDistributor()
        config = DistributionConfig(
            channel=DistributionChannel.FILE_SHARE,
            name="Pipeline Share",
            file_share_path=tempfile.mkdtemp(),
        )
        added = distributor.add_config(config)
        dist_result = distributor.distribute(added.id, export_result)
        self.assertEqual(dist_result.status, DistributionStatus.SENT)

    def test_template_to_report(self) -> None:
        """Template -> Definition -> Build."""
        registry = TemplateRegistry()
        template = registry.get_by_name("Sales Summary")
        self.assertIsNotNone(template)
        defn = template.instantiate(name="My Sales Report")
        builder = ReportBuilder()
        builder.register_data_source("sales_db", SAMPLE_SALES_DATA)
        result = builder.build(defn)
        self.assertEqual(result.status, ReportStatus.READY)
        self.assertGreater(result.total_count, 0)

    def test_scheduler_with_builder(self) -> None:
        """Scheduler -> Build -> History."""
        builder = ReportBuilder()
        builder.register_data_source("test", SAMPLE_SALES_DATA)
        defn = _make_definition()
        scheduler = ReportScheduler()
        config = ScheduleConfig(
            name="Integration",
            frequency=ScheduleFrequency.ONCE,
            report_definition_id=defn.id,
        )
        created = scheduler.create_schedule(config)
        run = scheduler.execute_now(created.id)
        self.assertIsNotNone(run)
        self.assertEqual(run.status, ScheduleStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()

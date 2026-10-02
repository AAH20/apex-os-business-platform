"""Tests for the data warehouse system."""

from __future__ import annotations

import pytest

from apex_os_bp.data_warehouse import (
    ETLPipeline,
    ETLStage,
    ETLResult,
    ETLError,
    StarSchema,
    Dimension,
    FactTable,
    Column,
    DataType,
    Relationship,
    DataQualityEngine,
    QualityRule,
    QualityCheckResult,
    QualityReport,
    RuleType,
    DataGovernance,
    GovernancePolicy,
    DataLineage,
    AccessLevel,
    SensitivityLevel,
    AuditEvent,
    DataCatalog,
    CatalogEntry,
    CatalogTag,
    SearchResult,
    AssetType,
    AssetStatus,
)


# ============================================================================
# ETL Pipeline Tests
# ============================================================================


class TestETLPipeline:
    """Tests for ETL pipeline functionality."""

    def test_pipeline_creation(self):
        pipeline = ETLPipeline("test_pipeline")
        assert pipeline.name == "test_pipeline"
        assert pipeline._stages == []

    def test_add_stage(self):
        pipeline = ETLPipeline("test_pipeline")
        stage = ExtractStage("extract", lambda: [{"id": 1}])
        pipeline.add_stage(stage)
        assert len(pipeline._stages) == 1

    def test_pipeline_execution_success(self):
        pipeline = ETLPipeline("test_pipeline")
        pipeline.add_stage(ExtractStage("extract", lambda: [{"id": 1}, {"id": 2}]))
        pipeline.add_stage(TransformStage("transform", lambda data: data))
        pipeline.add_stage(LoadStage("load", lambda data: len(data)))
        results = pipeline.execute()
        assert len(results) == 3
        assert all(r.success for r in results)
        assert pipeline.success

    def test_pipeline_execution_failure(self):
        pipeline = ETLPipeline("test_pipeline")
        pipeline.add_stage(ExtractStage("extract", lambda: (_ for _ in ()).throw(Exception("fail"))))
        results = pipeline.execute()
        assert len(results) == 1
        assert not results[0].success
        assert not pipeline.success

    def test_pipeline_no_stages_raises(self):
        pipeline = ETLPipeline("empty")
        with pytest.raises(ETLError):
            pipeline.execute()

    def test_pipeline_get_summary(self):
        pipeline = ETLPipeline("test_pipeline")
        pipeline.add_stage(ExtractStage("extract", lambda: [{"id": 1}]))
        pipeline.execute()
        summary = pipeline.get_summary()
        assert summary["pipeline"] == "test_pipeline"
        assert summary["success"] is True
        assert summary["stages_executed"] == 1

    def test_etl_result_merge(self):
        r1 = ETLResult(success=True, stage=ETLStage.EXTRACT, records_processed=10)
        r2 = ETLResult(success=True, stage=ETLStage.TRANSFORM, records_processed=8)
        merged = r1.merge(r2)
        assert merged.records_processed == 18
        assert merged.success is True

    def test_etl_result_merge_failure(self):
        r1 = ETLResult(success=True, stage=ETLStage.EXTRACT, records_processed=10)
        r2 = ETLResult(success=False, stage=ETLStage.TRANSFORM, records_processed=0, errors=["err"])
        merged = r1.merge(r2)
        assert merged.success is False
        assert merged.errors == ["err"]

    def test_validate_stage(self):
        pipeline = ETLPipeline("test_pipeline")
        validator = lambda data: (True, [])
        pipeline.add_stage(ValidateStage("validate", validator))
        results = pipeline.execute([{"id": 1}])
        assert results[0].success is True

    def test_validate_stage_failure(self):
        pipeline = ETLPipeline("test_pipeline")
        validator = lambda data: (False, ["invalid data"])
        pipeline.add_stage(ValidateStage("validate", validator))
        results = pipeline.execute([{"id": 1}])
        assert results[0].success is False
        assert results[0].errors == ["invalid data"]


# ============================================================================
# Data Modeling Tests
# ============================================================================


class TestDataModeling:
    """Tests for data modeling functionality."""

    def test_column_creation(self):
        col = Column(name="id", data_type=DataType.INTEGER, primary_key=True)
        assert col.name == "id"
        assert col.data_type == DataType.INTEGER
        assert col.primary_key is True
        assert col.nullable is True

    def test_column_validate_value_string(self):
        col = Column(name="name", data_type=DataType.STRING)
        assert col.validate_value("hello") is True
        assert col.validate_value(123) is False
        assert col.validate_value(None) is True  # nullable

    def test_column_validate_value_integer(self):
        col = Column(name="age", data_type=DataType.INTEGER, nullable=False)
        assert col.validate_value(25) is True
        assert col.validate_value("25") is False
        assert col.validate_value(None) is False  # not nullable

    def test_column_validate_value_boolean(self):
        col = Column(name="active", data_type=DataType.BOOLEAN)
        assert col.validate_value(True) is True
        assert col.validate_value(False) is True
        assert col.validate_value(1) is False

    def test_dimension_creation(self):
        dim = Dimension(
            name="dim_customer",
            columns=[
                Column(name="customer_id", data_type=DataType.INTEGER, primary_key=True),
                Column(name="name", data_type=DataType.STRING),
            ],
        )
        assert dim.name == "dim_customer"
        assert len(dim.columns) == 2
        assert dim.primary_key.name == "customer_id"

    def test_dimension_validate_no_pk(self):
        dim = Dimension(
            name="dim_test",
            columns=[Column(name="col1", data_type=DataType.STRING)],
        )
        errors = dim.validate()
        assert len(errors) == 1
        assert "no primary key" in errors[0]

    def test_dimension_validate_scd(self):
        dim = Dimension(
            name="dim_scd",
            columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
            slowly_changing_dimension=True,
            scd_type=2,
        )
        errors = dim.validate()
        assert len(errors) == 0

    def test_dimension_validate_invalid_scd(self):
        dim = Dimension(
            name="dim_scd",
            columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
            slowly_changing_dimension=True,
            scd_type=5,
        )
        errors = dim.validate()
        assert len(errors) == 1

    def test_fact_table_creation(self):
        ft = FactTable(
            name="fact_sales",
            columns=[
                Column(name="sale_id", data_type=DataType.INTEGER, primary_key=True),
                Column(name="customer_id", data_type=DataType.INTEGER),
            ],
            dimension_keys={"dim_customer": "customer_id"},
            measures=["amount", "quantity"],
        )
        assert ft.name == "fact_sales"
        assert "dim_customer" in ft.dimension_keys
        assert "amount" in ft.measures

    def test_fact_table_validate_no_dimensions(self):
        ft = FactTable(
            name="fact_test",
            columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
            measures=["amount"],
        )
        errors = ft.validate()
        assert len(errors) == 1
        assert "no dimension links" in errors[0]

    def test_fact_table_validate_no_measures(self):
        ft = FactTable(
            name="fact_test",
            columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
            dimension_keys={"dim_customer": "customer_id"},
        )
        errors = ft.validate()
        assert len(errors) == 1
        assert "no measures" in errors[0]

    def test_relationship_creation(self):
        rel = Relationship(
            name="fk_customer",
            source_table="fact_sales",
            source_column="customer_id",
            target_table="dim_customer",
            target_column="customer_id",
        )
        assert rel.name == "fk_customer"
        assert rel.relationship_type == "many_to_one"

    def test_relationship_validate(self):
        rel = Relationship(
            name="fk_customer",
            source_table="fact_sales",
            source_column="customer_id",
            target_table="dim_customer",
            target_column="customer_id",
        )
        tables = {
            "fact_sales": FactTable(
                name="fact_sales",
                columns=[Column(name="customer_id", data_type=DataType.INTEGER)],
            ),
            "dim_customer": Dimension(
                name="dim_customer",
                columns=[Column(name="customer_id", data_type=DataType.INTEGER, primary_key=True)],
            ),
        }
        assert rel.validate(tables) is True

    def test_relationship_validate_missing_table(self):
        rel = Relationship(
            name="fk_test",
            source_table="missing_table",
            source_column="id",
            target_table="dim_customer",
            target_column="id",
        )
        tables = {
            "dim_customer": Dimension(
                name="dim_customer",
                columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
            ),
        }
        assert rel.validate(tables) is False

    def test_star_schema_creation(self):
        schema = StarSchema(name="sales_schema")
        assert schema.name == "sales_schema"
        assert schema.dimensions == []
        assert schema.fact_tables == []

    def test_star_schema_add_dimension(self):
        schema = StarSchema(name="sales_schema")
        dim = Dimension(
            name="dim_customer",
            columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
        )
        schema.add_dimension(dim)
        assert len(schema.dimensions) == 1
        assert schema.get_dimension("dim_customer") is not None

    def test_star_schema_add_fact_table(self):
        schema = StarSchema(name="sales_schema")
        ft = FactTable(
            name="fact_sales",
            columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
            dimension_keys={"dim_customer": "customer_id"},
            measures=["amount"],
        )
        schema.add_fact_table(ft)
        assert len(schema.fact_tables) == 1
        assert schema.get_fact_table("fact_sales") is not None

    def test_star_schema_validate(self):
        schema = StarSchema(name="sales_schema")
        dim = Dimension(
            name="dim_customer",
            columns=[Column(name="customer_id", data_type=DataType.INTEGER, primary_key=True)],
        )
        ft = FactTable(
            name="fact_sales",
            columns=[
                Column(name="sale_id", data_type=DataType.INTEGER, primary_key=True),
                Column(name="customer_id", data_type=DataType.INTEGER),
            ],
            dimension_keys={"dim_customer": "customer_id"},
            measures=["amount"],
        )
        schema.add_dimension(dim)
        schema.add_fact_table(ft)
        errors = schema.validate()
        assert len(errors) == 0

    def test_star_schema_to_dict(self):
        schema = StarSchema(name="test_schema", description="Test")
        dim = Dimension(
            name="dim_test",
            columns=[Column(name="id", data_type=DataType.INTEGER, primary_key=True)],
        )
        schema.add_dimension(dim)
        d = schema.to_dict()
        assert d["name"] == "test_schema"
        assert len(d["dimensions"]) == 1


# ============================================================================
# Data Quality Tests
# ============================================================================


class TestDataQuality:
    """Tests for data quality functionality."""

    def test_quality_rule_creation(self):
        rule = QualityRule(
            name="not_null",
            rule_type=RuleType.COMPLETENESS,
            column="email",
        )
        assert rule.name == "not_null"
        assert rule.rule_type == RuleType.COMPLETENESS
        assert rule.enabled is True

    def test_quality_rule_evaluate(self):
        rule = QualityRule(
            name="is_positive",
            rule_type=RuleType.VALIDITY,
            validator=lambda v: v > 0,
        )
        assert rule.evaluate(5) is True
        assert rule.evaluate(-1) is False

    def test_quality_rule_evaluate_batch(self):
        rule = QualityRule(
            name="is_positive",
            rule_type=RuleType.VALIDITY,
            validator=lambda v: v > 0,
        )
        passed, failed = rule.evaluate_batch([1, 2, -1, 3, -2])
        assert passed == 3
        assert failed == 2

    def test_quality_check_result(self):
        result = QualityCheckResult(
            rule_name="test_rule",
            rule_type=RuleType.COMPLETENESS,
            passed=True,
            total_records=100,
            passed_records=100,
            failed_records=0,
            severity="error",
        )
        assert result.pass_rate == 100.0
        assert result.failed is False

    def test_quality_check_result_fail(self):
        result = QualityCheckResult(
            rule_name="test_rule",
            rule_type=RuleType.COMPLETENESS,
            passed=False,
            total_records=100,
            passed_records=80,
            failed_records=20,
            severity="error",
        )
        assert result.pass_rate == 80.0
        assert result.failed is True

    def test_quality_report(self):
        report = QualityReport(
            dataset_name="test_dataset",
            results=[
                QualityCheckResult(
                    rule_name="rule1",
                    rule_type=RuleType.COMPLETENESS,
                    passed=True,
                    total_records=100,
                    passed_records=100,
                    failed_records=0,
                    severity="error",
                ),
                QualityCheckResult(
                    rule_name="rule2",
                    rule_type=RuleType.UNIQUENESS,
                    passed=False,
                    total_records=100,
                    passed_records=90,
                    failed_records=10,
                    severity="error",
                ),
            ],
        )
        assert report.total_checks == 2
        assert report.passed_checks == 1
        assert report.failed_checks == 1
        assert report.is_healthy is False

    def test_quality_report_healthy(self):
        report = QualityReport(
            dataset_name="test_dataset",
            results=[
                QualityCheckResult(
                    rule_name="rule1",
                    rule_type=RuleType.COMPLETENESS,
                    passed=True,
                    total_records=100,
                    passed_records=100,
                    failed_records=0,
                    severity="error",
                ),
            ],
        )
        assert report.is_healthy is True

    def test_quality_engine_check_completeness(self):
        engine = DataQualityEngine()
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": None},
            {"id": 3, "name": "Bob"},
        ]
        result = engine.check_completeness(data, "name")
        assert result.passed_records == 2
        assert result.failed_records == 1
        assert result.passed is False

    def test_quality_engine_check_uniqueness(self):
        engine = DataQualityEngine()
        data = [
            {"id": 1, "email": "a@test.com"},
            {"id": 2, "email": "b@test.com"},
            {"id": 3, "email": "a@test.com"},
        ]
        result = engine.check_uniqueness(data, "email")
        assert result.passed_records == 2
        assert result.failed_records == 1

    def test_quality_engine_check_validity(self):
        engine = DataQualityEngine()
        data = [
            {"id": 1, "age": 25},
            {"id": 2, "age": -5},
            {"id": 3, "age": 30},
        ]
        result = engine.check_validity(data, "age", lambda v: v >= 0)
        assert result.passed_records == 2
        assert result.failed_records == 1

    def test_quality_engine_check_range(self):
        engine = DataQualityEngine()
        data = [
            {"id": 1, "score": 85},
            {"id": 2, "score": 105},
            {"id": 3, "score": 50},
        ]
        result = engine.check_range(data, "score", min_val=0, max_val=100)
        assert result.passed_records == 2
        assert result.failed_records == 1

    def test_quality_engine_check_pattern(self):
        engine = DataQualityEngine()
        data = [
            {"id": 1, "email": "test@example.com"},
            {"id": 2, "email": "invalid"},
            {"id": 3, "email": "user@domain.org"},
        ]
        result = engine.check_pattern(data, "email", r"^[\w\.-]+@[\w\.-]+\.\w+$")
        assert result.passed_records == 2
        assert result.failed_records == 1

    def test_quality_engine_check_referential_integrity(self):
        engine = DataQualityEngine()
        data = [
            {"id": 1, "dept_id": 10},
            {"id": 2, "dept_id": 20},
            {"id": 3, "dept_id": 99},
        ]
        valid_ids = {10, 20, 30}
        result = engine.check_referential_integrity(data, "dept_id", valid_ids)
        assert result.passed_records == 2
        assert result.failed_records == 1

    def test_quality_engine_run_rules(self):
        engine = DataQualityEngine()
        engine.add_rule(QualityRule(
            name="not_null_id",
            rule_type=RuleType.COMPLETENESS,
            column="id",
            validator=lambda v: v is not None,
        ))
        data = [{"id": 1}, {"id": 2}, {"id": None}]
        report = engine.run_rules(data, "test_data")
        assert report.total_checks == 1
        assert report.results[0].failed_records == 1

    def test_quality_engine_run_all_checks(self):
        engine = DataQualityEngine()
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ]
        report = engine.run_all_checks(data, ["id", "name"], "test_data")
        assert report.total_checks == 4  # 2 columns x 2 checks each

    def test_quality_engine_add_remove_rule(self):
        engine = DataQualityEngine()
        rule = QualityRule(name="test", rule_type=RuleType.COMPLETENESS, column="col")
        engine.add_rule(rule)
        assert len(engine._rules) == 1
        assert engine.remove_rule("test") is True
        assert len(engine._rules) == 0
        assert engine.remove_rule("nonexistent") is False

    def test_quality_report_to_dict(self):
        report = QualityReport(
            dataset_name="test",
            results=[
                QualityCheckResult(
                    rule_name="r1",
                    rule_type=RuleType.COMPLETENESS,
                    passed=True,
                    total_records=10,
                    passed_records=10,
                    failed_records=0,
                    severity="error",
                ),
            ],
        )
        d = report.to_dict()
        assert d["dataset_name"] == "test"
        assert d["total_checks"] == 1
        assert d["is_healthy"] is True


# ============================================================================
# Data Governance Tests
# ============================================================================


class TestDataGovernance:
    """Tests for data governance functionality."""

    def test_governance_policy_creation(self):
        policy = GovernancePolicy(
            name="pii_policy",
            description="PII data policy",
            access_level=AccessLevel.RESTRICTED,
            sensitivity=SensitivityLevel.CONFIDENTIAL,
        )
        assert policy.name == "pii_policy"
        assert policy.access_level == AccessLevel.RESTRICTED

    def test_governance_policy_can_access(self):
        policy = GovernancePolicy(
            name="test_policy",
            allowed_roles=["admin", "analyst"],
            denied_roles=["guest"],
        )
        assert policy.can_access("user1", ["admin"]) is True
        assert policy.can_access("user2", ["analyst"]) is True
        assert policy.can_access("user3", ["guest"]) is False
        assert policy.can_access("user4", ["viewer"]) is False

    def test_governance_policy_can_access_users(self):
        policy = GovernancePolicy(
            name="test_policy",
            allowed_users=["alice", "bob"],
            denied_users=["eve"],
        )
        assert policy.can_access("alice", []) is True
        assert policy.can_access("bob", []) is True
        assert policy.can_access("eve", []) is False
        assert policy.can_access("charlie", []) is False

    def test_governance_policy_disabled(self):
        policy = GovernancePolicy(
            name="test_policy",
            enabled=False,
        )
        assert policy.can_access("user", ["admin"]) is False

    def test_data_lineage_creation(self):
        lineage = DataLineage(
            source="raw_orders",
            target="fact_orders",
            transformation="clean_and_aggregate",
        )
        assert lineage.source == "raw_orders"
        assert lineage.target == "fact_orders"

    def test_data_lineage_upstream_downstream(self):
        lineage = DataLineage(source="raw_orders", target="fact_orders")
        lineage.add_upstream("raw_customers")
        lineage.add_downstream("report_sales")
        assert "raw_customers" in lineage.upstream
        assert "report_sales" in lineage.downstream

    def test_audit_event_creation(self):
        event = AuditEvent(
            event_id="evt-001",
            event_type="access",
            user="alice",
            resource="fact_sales",
            action="read",
        )
        assert event.event_id == "evt-001"
        assert event.success is True

    def test_data_governance_add_policy(self):
        gov = DataGovernance()
        policy = GovernancePolicy(name="test_policy")
        gov.add_policy(policy)
        assert gov.get_policy("test_policy") is not None

    def test_data_governance_remove_policy(self):
        gov = DataGovernance()
        policy = GovernancePolicy(name="test_policy")
        gov.add_policy(policy)
        assert gov.remove_policy("test_policy") is True
        assert gov.get_policy("test_policy") is None

    def test_data_governance_check_access(self):
        gov = DataGovernance()
        policy = GovernancePolicy(
            name="sales_data",
            allowed_roles=["analyst"],
        )
        gov.add_policy(policy)
        assert gov.check_access("sales_data", "user1", ["analyst"]) is True
        assert gov.check_access("sales_data", "user2", ["guest"]) is False

    def test_data_governance_classify_data(self):
        gov = DataGovernance()
        gov.classify_data("fact_sales", SensitivityLevel.CONFIDENTIAL)
        assert gov.get_classification("fact_sales") == SensitivityLevel.CONFIDENTIAL

    def test_data_governance_add_lineage(self):
        gov = DataGovernance()
        lineage = DataLineage(source="raw_orders", target="fact_orders")
        gov.add_lineage(lineage)
        result = gov.get_lineage("raw_orders", "fact_orders")
        assert result is not None
        assert result.source == "raw_orders"

    def test_data_governance_get_upstream_lineage(self):
        gov = DataGovernance()
        lineage = DataLineage(source="raw_orders", target="fact_orders")
        gov.add_lineage(lineage)
        upstream = gov.get_upstream_lineage("fact_orders")
        assert len(upstream) == 1

    def test_data_governance_get_downstream_lineage(self):
        gov = DataGovernance()
        lineage = DataLineage(source="raw_orders", target="fact_orders")
        gov.add_lineage(lineage)
        downstream = gov.get_downstream_lineage("raw_orders")
        assert len(downstream) == 1

    def test_data_governance_log_audit_event(self):
        gov = DataGovernance()
        event = AuditEvent(
            event_id="evt-001",
            event_type="access",
            user="alice",
            resource="fact_sales",
            action="read",
        )
        gov.log_audit_event(event)
        events = gov.get_audit_log()
        assert len(events) == 1

    def test_data_governance_get_audit_log_filtered(self):
        gov = DataGovernance()
        gov.log_audit_event(AuditEvent(event_id="1", event_type="access", user="alice", resource="r1", action="read"))
        gov.log_audit_event(AuditEvent(event_id="2", event_type="access", user="bob", resource="r2", action="read"))
        events = gov.get_audit_log(user="alice")
        assert len(events) == 1
        assert events[0].user == "alice"

    def test_data_governance_role_hierarchy(self):
        gov = DataGovernance()
        gov.add_role_hierarchy("senior_analyst", ["analyst"])
        effective = gov.get_effective_roles(["senior_analyst"])
        assert "analyst" in effective
        assert "senior_analyst" in effective

    def test_data_governance_generate_audit_report(self):
        gov = DataGovernance()
        gov.log_audit_event(AuditEvent(event_id="1", event_type="access", user="alice", resource="r1", action="read"))
        gov.log_audit_event(AuditEvent(event_id="2", event_type="modify", user="bob", resource="r2", action="write"))
        report = gov.generate_audit_report()
        assert report["total_events"] == 2
        assert report["events_by_type"]["access"] == 1
        assert report["events_by_type"]["modify"] == 1

    def test_data_governance_validate_compliance(self):
        gov = DataGovernance()
        gov.classify_data("fact_sales", SensitivityLevel.CRITICAL)
        result = gov.validate_compliance("fact_sales")
        assert result["compliant"] is False
        assert len(result["issues"]) > 0

    def test_data_governance_validate_compliance_ok(self):
        gov = DataGovernance()
        gov.classify_data("fact_sales", SensitivityLevel.INTERNAL)
        result = gov.validate_compliance("fact_sales")
        assert result["compliant"] is True

    def test_governance_policy_to_dict(self):
        policy = GovernancePolicy(
            name="test",
            access_level=AccessLevel.CONFIDENTIAL,
            sensitivity=SensitivityLevel.CONFIDENTIAL,
        )
        d = policy.to_dict()
        assert d["name"] == "test"
        assert d["access_level"] == "confidential"


# ============================================================================
# Data Catalog Tests
# ============================================================================


class TestDataCatalog:
    """Tests for data catalog functionality."""

    def test_catalog_entry_creation(self):
        entry = CatalogEntry(
            id="entry-001",
            name="Sales Fact Table",
            asset_type=AssetType.TABLE,
            description="Fact table for sales data",
            owner="data_team",
        )
        assert entry.id == "entry-001"
        assert entry.name == "Sales Fact Table"
        assert entry.asset_type == AssetType.TABLE
        assert entry.status == AssetStatus.ACTIVE

    def test_catalog_entry_add_tag(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        tag = CatalogTag(name="department", value="sales")
        entry.add_tag(tag)
        assert len(entry.tags) == 1
        assert entry.tags[0].name == "department"

    def test_catalog_entry_remove_tag(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        entry.add_tag(CatalogTag(name="dept", value="sales"))
        assert entry.remove_tag("dept") is True
        assert len(entry.tags) == 0
        assert entry.remove_tag("nonexistent") is False

    def test_catalog_entry_update_metadata(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        entry.update_metadata("row_count", 10000)
        assert entry.metadata["row_count"] == 10000

    def test_catalog_entry_add_column(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        entry.add_column({"name": "id", "type": "integer"})
        assert len(entry.columns) == 1

    def test_catalog_entry_record_usage(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        entry.record_usage()
        entry.record_usage()
        assert entry.usage_count == 2

    def test_catalog_entry_add_rating(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        entry.add_rating(4.0)
        entry.add_rating(5.0)
        assert entry.rating == 4.5
        assert entry.rating_count == 2

    def test_catalog_entry_add_rating_invalid(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        with pytest.raises(ValueError):
            entry.add_rating(6.0)

    def test_catalog_add_entry(self):
        catalog = DataCatalog()
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        catalog.add_entry(entry)
        assert catalog.get_entry("e1") is not None

    def test_catalog_remove_entry(self):
        catalog = DataCatalog()
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        catalog.add_entry(entry)
        assert catalog.remove_entry("e1") is True
        assert catalog.get_entry("e1") is None

    def test_catalog_get_by_name(self):
        catalog = DataCatalog()
        entry = CatalogEntry(id="e1", name="sales_data", asset_type=AssetType.TABLE)
        catalog.add_entry(entry)
        results = catalog.get_by_name("sales_data")
        assert len(results) == 1

    def test_catalog_list_entries(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE))
        catalog.add_entry(CatalogEntry(id="e2", name="t2", asset_type=AssetType.VIEW))
        catalog.add_entry(CatalogEntry(id="e3", name="t3", asset_type=AssetType.TABLE))
        tables = catalog.list_entries(asset_type=AssetType.TABLE)
        assert len(tables) == 2

    def test_catalog_list_entries_by_status(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE, status=AssetStatus.ACTIVE))
        catalog.add_entry(CatalogEntry(id="e2", name="t2", asset_type=AssetType.TABLE, status=AssetStatus.DEPRECATED))
        active = catalog.list_entries(status=AssetStatus.ACTIVE)
        assert len(active) == 1

    def test_catalog_list_entries_by_owner(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE, owner="alice"))
        catalog.add_entry(CatalogEntry(id="e2", name="t2", asset_type=AssetType.TABLE, owner="bob"))
        alice_entries = catalog.list_entries(owner="alice")
        assert len(alice_entries) == 1

    def test_catalog_list_entries_by_tags(self):
        catalog = DataCatalog()
        entry = CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE)
        entry.add_tag(CatalogTag(name="dept", value="sales"))
        catalog.add_entry(entry)
        catalog.add_entry(CatalogEntry(id="e2", name="t2", asset_type=AssetType.TABLE))
        tagged = catalog.list_entries(tags=["dept"])
        assert len(tagged) == 1

    def test_catalog_search(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(
            id="e1",
            name="Sales Fact Table",
            asset_type=AssetType.TABLE,
            description="Fact table for sales data",
        ))
        catalog.add_entry(CatalogEntry(
            id="e2",
            name="Customer Dimension",
            asset_type=AssetType.TABLE,
            description="Customer dimension table",
        ))
        results = catalog.search("sales")
        assert len(results) >= 1
        assert results[0].entry.name == "Sales Fact Table"

    def test_catalog_search_by_description(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(
            id="e1",
            name="fact_table",
            asset_type=AssetType.TABLE,
            description="Contains revenue and sales metrics",
        ))
        results = catalog.search("revenue")
        assert len(results) == 1

    def test_catalog_search_by_tag(self):
        catalog = DataCatalog()
        entry = CatalogEntry(id="e1", name="test_table", asset_type=AssetType.TABLE)
        entry.add_tag(CatalogTag(name="department", value="finance"))
        catalog.add_entry(entry)
        results = catalog.search("finance")
        assert len(results) == 1

    def test_catalog_search_limit(self):
        catalog = DataCatalog()
        for i in range(30):
            catalog.add_entry(CatalogEntry(
                id=f"e{i}",
                name=f"test_table_{i}",
                asset_type=AssetType.TABLE,
            ))
        results = catalog.search("test", limit=5)
        assert len(results) == 5

    def test_catalog_advanced_search(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(
            id="e1",
            name="Sales Data",
            asset_type=AssetType.TABLE,
            status=AssetStatus.ACTIVE,
            owner="alice",
        ))
        catalog.add_entry(CatalogEntry(
            id="e2",
            name="Sales Report",
            asset_type=AssetType.REPORT,
            status=AssetStatus.ACTIVE,
            owner="bob",
        ))
        results = catalog.advanced_search(
            query="sales",
            asset_types=[AssetType.TABLE],
        )
        assert len(results) == 1
        assert results[0].entry.asset_type == AssetType.TABLE

    def test_catalog_get_statistics(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE, owner="alice"))
        catalog.add_entry(CatalogEntry(id="e2", name="t2", asset_type=AssetType.VIEW, owner="bob"))
        stats = catalog.get_statistics()
        assert stats["total_entries"] == 2
        assert stats["by_type"]["table"] == 1
        assert stats["by_type"]["view"] == 1

    def test_catalog_get_popular_entries(self):
        catalog = DataCatalog()
        e1 = CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE)
        e1.record_usage()
        e1.record_usage()
        e2 = CatalogEntry(id="e2", name="t2", asset_type=AssetType.TABLE)
        e2.record_usage()
        catalog.add_entry(e1)
        catalog.add_entry(e2)
        popular = catalog.get_popular_entries()
        assert popular[0].id == "e1"

    def test_catalog_get_recently_updated(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE))
        catalog.add_entry(CatalogEntry(id="e2", name="t2", asset_type=AssetType.TABLE))
        recent = catalog.get_recently_updated()
        assert len(recent) == 2

    def test_catalog_get_deprecated_entries(self):
        catalog = DataCatalog()
        catalog.add_entry(CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE, status=AssetStatus.ACTIVE))
        catalog.add_entry(CatalogEntry(id="e2", name="t2", asset_type=AssetType.TABLE, status=AssetStatus.DEPRECATED))
        deprecated = catalog.get_deprecated_entries()
        assert len(deprecated) == 1
        assert deprecated[0].id == "e2"

    def test_catalog_suggest_related(self):
        catalog = DataCatalog()
        e1 = CatalogEntry(id="e1", name="t1", asset_type=AssetType.TABLE, owner="alice")
        e1.add_tag(CatalogTag(name="dept", value="sales"))
        e2 = CatalogEntry(id="e2", name="t2", asset_type=AssetType.TABLE, owner="alice")
        e2.add_tag(CatalogTag(name="dept", value="sales"))
        catalog.add_entry(e1)
        catalog.add_entry(e2)
        related = catalog.suggest_related("e1")
        assert len(related) == 1
        assert related[0].id == "e2"

    def test_catalog_suggest_related_empty(self):
        catalog = DataCatalog()
        related = catalog.suggest_related("nonexistent")
        assert related == []

    def test_catalog_entry_to_dict(self):
        entry = CatalogEntry(
            id="e1",
            name="test",
            asset_type=AssetType.TABLE,
            description="test table",
            owner="alice",
        )
        d = entry.to_dict()
        assert d["id"] == "e1"
        assert d["name"] == "test"
        assert d["asset_type"] == "table"

    def test_search_result_to_dict(self):
        entry = CatalogEntry(id="e1", name="test", asset_type=AssetType.TABLE)
        result = SearchResult(entry=entry, score=10.0, matched_fields=["name"])
        d = result.to_dict()
        assert d["score"] == 10.0
        assert d["matched_fields"] == ["name"]

    def test_catalog_tag_to_dict(self):
        tag = CatalogTag(name="dept", value="sales", category="department")
        d = tag.to_dict()
        assert d["name"] == "dept"
        assert d["value"] == "sales"
        assert d["category"] == "department"

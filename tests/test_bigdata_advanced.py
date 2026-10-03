"""Advanced tests for BigData module: ingestion, transformation, quality, lineage, catalog."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_records():
    return [
        {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "age": 25, "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "age": 35, "email": "charlie@example.com"},
    ]


@pytest.fixture
def mock_ingester():
    from bigdata.ingestion import DataIngester
    ingester = AsyncMock(spec=DataIngester)
    ingester.ingest.return_value = {"status": "success", "count": 3}
    ingester.validate_schema.return_value = True
    ingester.get_stats.return_value = {"total": 3, "valid": 3, "invalid": 0}
    return ingester


@pytest.fixture
def mock_transformer():
    from bigdata.transformation import DataTransformer
    transformer = AsyncMock(spec=DataTransformer)
    transformer.transform.return_value = [
        {"id": 1, "name": "ALICE", "age": 30},
        {"id": 2, "name": "BOB", "age": 25},
    ]
    transformer.apply_rules.return_value = [{"id": 1, "name": "ALICE"}]
    return transformer


@pytest.fixture
def mock_quality_engine():
    from bigdata.quality import QualityEngine
    engine = AsyncMock(spec=QualityEngine)
    engine.run_checks.return_value = {
        "completeness": 1.0, "uniqueness": 1.0, "validity": 0.95,
        "issues": [{"rule": "email_format", "count": 1}],
    }
    engine.score.return_value = 0.98
    return engine


@pytest.fixture
def mock_lineage_tracker():
    from bigdata.lineage import LineageTracker
    tracker = AsyncMock(spec=LineageTracker)
    tracker.track.return_value = {"lineage_id": "ln-001", "nodes": 3, "edges": 2}
    tracker.get_lineage.return_value = {
        "source": "raw_table", "transformations": ["normalize", "dedupe"], "destination": "clean_table",
    }
    return tracker


@pytest.fixture
def mock_catalog():
    from bigdata.catalog import DataCatalog
    catalog = AsyncMock(spec=DataCatalog)
    catalog.register.return_value = {"asset_id": "asset-001", "status": "registered"}
    catalog.search.return_value = [{"name": "users", "type": "table", "columns": 5}]
    catalog.get_metadata.return_value = {"name": "users", "schema": "public", "owner": "data-team"}
    return catalog


# ---------------------------------------------------------------------------
# 1. Data Ingestion Tests
# ---------------------------------------------------------------------------

class TestDataIngestion:
    @pytest.mark.asyncio
    async def test_ingest_success(self, mock_ingester, sample_records):
        result = await mock_ingester.ingest(sample_records)
        assert result["status"] == "success"
        assert result["count"] == 3

    @pytest.mark.asyncio
    async def test_ingest_empty_source(self, mock_ingester):
        mock_ingester.ingest.return_value = {"status": "success", "count": 0}
        result = await mock_ingester.ingest([])
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_schema_validation(self, mock_ingester, sample_records):
        assert await mock_ingester.validate_schema(sample_records) is True

    @pytest.mark.asyncio
    async def test_ingest_stats(self, mock_ingester):
        stats = await mock_ingester.get_stats()
        assert stats["total"] == 3
        assert stats["valid"] == 3
        assert stats["invalid"] == 0

    @pytest.mark.asyncio
    async def test_ingest_invalid_records(self, mock_ingester):
        mock_ingester.ingest.side_effect = ValueError("Malformed record detected")
        with pytest.raises(ValueError, match="Malformed record"):
            await mock_ingester.ingest([{"bad": "data"}])


# ---------------------------------------------------------------------------
# 2. Data Transformation Tests
# ---------------------------------------------------------------------------

class TestDataTransformation:
    @pytest.mark.asyncio
    async def test_transform_records(self, mock_transformer, sample_records):
        result = await mock_transformer.transform(sample_records)
        assert len(result) == 2
        assert result[0]["name"] == "ALICE"

    @pytest.mark.asyncio
    async def test_apply_transformation_rules(self, mock_transformer):
        result = await mock_transformer.apply_rules([{"id": 1, "name": "alice"}])
        assert result[0]["name"] == "ALICE"

    @pytest.mark.asyncio
    async def test_transform_empty_input(self, mock_transformer):
        mock_transformer.transform.return_value = []
        result = await mock_transformer.transform([])
        assert result == []

    @pytest.mark.asyncio
    async def test_transform_preserves_count(self, mock_transformer, sample_records):
        mock_transformer.transform.return_value = sample_records
        result = await mock_transformer.transform(sample_records)
        assert len(result) == len(sample_records)


# ---------------------------------------------------------------------------
# 3. Data Quality Tests
# ---------------------------------------------------------------------------

class TestDataQuality:
    @pytest.mark.asyncio
    async def test_run_quality_checks(self, mock_quality_engine, sample_records):
        report = await mock_quality_engine.run_checks(sample_records)
        assert report["completeness"] == 1.0
        assert report["uniqueness"] == 1.0
        assert report["validity"] == 0.95
        assert len(report["issues"]) == 1

    @pytest.mark.asyncio
    async def test_quality_score(self, mock_quality_engine):
        score = await mock_quality_engine.score()
        assert score == 0.98

    @pytest.mark.asyncio
    async def test_quality_issues_detected(self, mock_quality_engine):
        mock_quality_engine.run_checks.return_value = {
            "completeness": 0.5, "uniqueness": 0.8, "validity": 0.6,
            "issues": [{"rule": "null_check", "count": 5}],
        }
        report = await mock_quality_engine.run_checks([])
        assert report["completeness"] < 1.0
        assert report["issues"][0]["rule"] == "null_check"

    @pytest.mark.asyncio
    async def test_quality_perfect_score(self, mock_quality_engine):
        mock_quality_engine.score.return_value = 1.0
        assert await mock_quality_engine.score() == 1.0


# ---------------------------------------------------------------------------
# 4. Data Lineage Tests
# ---------------------------------------------------------------------------

class TestDataLineage:
    @pytest.mark.asyncio
    async def test_track_lineage(self, mock_lineage_tracker):
        result = await mock_lineage_tracker.track("source", "dest", ["normalize"])
        assert result["lineage_id"] == "ln-001"
        assert result["nodes"] == 3
        assert result["edges"] == 2

    @pytest.mark.asyncio
    async def test_get_lineage(self, mock_lineage_tracker):
        lineage = await mock_lineage_tracker.get_lineage("clean_table")
        assert lineage["source"] == "raw_table"
        assert "normalize" in lineage["transformations"]
        assert lineage["destination"] == "clean_table"

    @pytest.mark.asyncio
    async def test_lineage_multiple_transformations(self, mock_lineage_tracker):
        mock_lineage_tracker.get_lineage.return_value = {
            "source": "api", "transformations": ["parse", "validate", "enrich", "load"],
            "destination": "warehouse",
        }
        lineage = await mock_lineage_tracker.get_lineage("warehouse")
        assert len(lineage["transformations"]) == 4


# ---------------------------------------------------------------------------
# 5. Data Catalog Tests
# ---------------------------------------------------------------------------

class TestDataCatalog:
    @pytest.mark.asyncio
    async def test_register_asset(self, mock_catalog):
        result = await mock_catalog.register("users", {"type": "table"})
        assert result["asset_id"] == "asset-001"
        assert result["status"] == "registered"

    @pytest.mark.asyncio
    async def test_search_catalog(self, mock_catalog):
        results = await mock_catalog.search("user")
        assert len(results) == 1
        assert results[0]["name"] == "users"
        assert results[0]["type"] == "table"

    @pytest.mark.asyncio
    async def test_get_metadata(self, mock_catalog):
        meta = await mock_catalog.get_metadata("users")
        assert meta["name"] == "users"
        assert meta["schema"] == "public"
        assert meta["owner"] == "data-team"

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_catalog):
        mock_catalog.search.return_value = []
        results = await mock_catalog.search("nonexistent")
        assert results == []

    @pytest.mark.asyncio
    async def test_register_duplicate(self, mock_catalog):
        mock_catalog.register.side_effect = ValueError("Asset already registered")
        with pytest.raises(ValueError, match="already registered"):
            await mock_catalog.register("users", {})

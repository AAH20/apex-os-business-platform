"""Tests for deepened CRM module."""
import pytest
from datetime import date, timedelta
from decimal import Decimal


class TestLeadScoring:
    @pytest.fixture
    def scorer(self):
        from apex_os_bp.crm.deepened import LeadScorer
        return LeadScorer()

    def test_high_score_lead(self, scorer):
        lead = {"email": "exec@bigcorp.com", "company_size": 500, "engagement": 90}
        assert scorer.score(lead) >= 80

    def test_low_score_lead(self, scorer):
        lead = {"email": "gmail@gmail.com", "company_size": 1, "engagement": 5}
        assert scorer.score(lead) < 30

    def test_score_range(self, scorer):
        lead = {"email": "test@test.com", "company_size": 50, "engagement": 50}
        score = scorer.score(lead)
        assert 0 <= score <= 100

    def test_missing_fields_default(self, scorer):
        assert scorer.score({}) >= 0


class TestPipelineAutomation:
    @pytest.fixture
    def pipeline(self):
        from apex_os_bp.crm.deepened import PipelineAutomator
        return PipelineAutomator()

    def test_stage_advance(self, pipeline):
        lead_id = pipeline.create_lead("Test", "test@test.com")
        pipeline.advance_stage(lead_id, "contacted")
        assert pipeline.get_stage(lead_id) == "contacted"

    def test_auto_email_on_stage(self, pipeline):
        lead_id = pipeline.create_lead("Test", "test@test.com")
        pipeline.advance_stage(lead_id, "qualified")
        actions = pipeline.get_actions(lead_id)
        assert any(a["type"] == "send_email" for a in actions)

    def test_no_invalid_stage(self, pipeline):
        lead_id = pipeline.create_lead("Test", "test@test.com")
        with pytest.raises(ValueError):
            pipeline.advance_stage(lead_id, "nonexistent_stage")


class TestEmailTracking:
    @pytest.fixture
    def tracker(self):
        from apex_os_bp.crm.deepened import EmailTracker
        return EmailTracker()

    def test_track_open(self, tracker):
        tracker.send("lead1", "Hello")
        tracker.track_open("lead1")
        assert tracker.get_opens("lead1") == 1

    def test_track_click(self, tracker):
        tracker.send("lead1", "Hello")
        tracker.track_click("lead1", "https://example.com")
        assert tracker.get_clicks("lead1") == 1

    def test_no_opens_initially(self, tracker):
        tracker.send("lead1", "Hello")
        assert tracker.get_opens("lead1") == 0


class TestSegmentation:
    @pytest.fixture
    def segmenter(self):
        from apex_os_bp.crm.deepened import Segmenter
        return Segmenter()

    def test_segment_by_size(self, segmenter):
        leads = [
            {"id": 1, "company_size": 5000},
            {"id": 2, "company_size": 10},
        ]
        segments = segmenter.segment(leads, "company_size")
        assert "enterprise" in segments
        assert "small" in segments

    def test_segment_by_engagement(self, segmenter):
        leads = [
            {"id": 1, "engagement": 90},
            {"id": 2, "engagement": 5},
        ]
        segments = segmenter.segment(leads, "engagement")
        assert len(segments) >= 2

    def test_empty_leads(self, segmenter):
        assert segmenter.segment([], "company_size") == {}


class TestChurnPrediction:
    @pytest.fixture
    def predictor(self):
        from apex_os_bp.crm.deepened import ChurnPredictor
        return ChurnPredictor()

    def test_high_churn_risk(self, predictor):
        customer = {"days_since_login": 90, "support_tickets": 10, "nps": 2}
        result = predictor.predict(customer)
        assert result["risk"] == "high"
        assert result["probability"] > 0.7

    def test_low_churn_risk(self, predictor):
        customer = {"days_since_login": 1, "support_tickets": 0, "nps": 9}
        result = predictor.predict(customer)
        assert result["risk"] == "low"
        assert result["probability"] < 0.3

    def test_medium_churn_risk(self, predictor):
        customer = {"days_since_login": 30, "support_tickets": 3, "nps": 6}
        result = predictor.predict(customer)
        assert result["risk"] in ("low", "medium", "high")

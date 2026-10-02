"""Tests for CRM deep features: lead scoring, email campaigns,
deduplication, forecasting, and segmentation."""

from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timedelta

# Ensure src is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.crm.lead_scoring import (
    LeadCategory,
    LeadScore,
    LeadScoringEngine,
    ScoringRule,
)
from apex_os_bp.crm.email_campaigns import (
    CampaignManager,
    CampaignStatus,
    EmailCampaign,
)
from apex_os_bp.crm.deduplication import (
    DeduplicationEngine,
    DuplicateGroup,
)
from apex_os_bp.crm.forecasting import (
    ForecastResult,
    SalesForecaster,
)
from apex_os_bp.crm.segmentation import (
    CustomerSegmentation,
    Segment,
    SegmentType,
)


# ── Lead Scoring Tests ──────────────────────────────────────────


class TestLeadScoring(unittest.TestCase):
    def setUp(self):
        self.engine = LeadScoringEngine()

    def test_score_hot_lead(self):
        lead = {
            "lead_id": "lead_1",
            "email_opens": 10,
            "email_clicks": 5,
            "website_visits": 8,
            "job_title": "VP of Engineering",
            "company_size": 5000,
            "days_since_last_activity": 1,
            "form_submissions": 2,
        }
        result = self.engine.score(lead)
        self.assertIsInstance(result, LeadScore)
        self.assertEqual(result.lead_id, "lead_1")
        self.assertGreaterEqual(result.total_score, 70)
        self.assertEqual(result.category, LeadCategory.HOT)
        self.assertGreater(result.percentage, 0)

    def test_score_cold_lead(self):
        lead = {
            "lead_id": "lead_2",
            "email_opens": 0,
            "email_clicks": 0,
            "website_visits": 0,
            "job_title": "intern",
            "company_size": 5,
            "days_since_last_activity": 90,
            "form_submissions": 0,
        }
        result = self.engine.score(lead)
        self.assertEqual(result.category, LeadCategory.COLD)
        self.assertLess(result.total_score, 40)

    def test_score_warm_lead(self):
        lead = {
            "lead_id": "lead_3",
            "email_opens": 3,
            "email_clicks": 1,
            "website_visits": 2,
            "job_title": "Manager",
            "company_size": 200,
            "days_since_last_activity": 10,
            "form_submissions": 1,
        }
        result = self.engine.score(lead)
        self.assertEqual(result.category, LeadCategory.WARM)
        self.assertGreaterEqual(result.total_score, 40)
        self.assertLess(result.total_score, 70)

    def test_score_many_sorts_descending(self):
        leads = [
            {"lead_id": "a", "email_opens": 0, "email_clicks": 0,
             "website_visits": 0, "job_title": "", "company_size": 0,
             "days_since_last_activity": 90, "form_submissions": 0},
            {"lead_id": "b", "email_opens": 10, "email_clicks": 5,
             "website_visits": 8, "job_title": "CEO", "company_size": 10000,
             "days_since_last_activity": 1, "form_submissions": 2},
            {"lead_id": "c", "email_opens": 3, "email_clicks": 1,
             "website_visits": 2, "job_title": "Manager", "company_size": 200,
             "days_since_last_activity": 10, "form_submissions": 1},
        ]
        results = self.engine.score_many(leads)
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].lead_id, "b")
        self.assertEqual(results[-1].lead_id, "a")

    def test_custom_rule(self):
        engine = LeadScoringEngine()
        engine.add_rule(ScoringRule(
            name="social_mentions",
            weight=10,
            evaluator=lambda lead: min(10.0, lead.get("social_mentions", 0) * 2.0),
            description="Social media mentions",
        ))
        lead = {
            "lead_id": "lead_4",
            "email_opens": 0,
            "email_clicks": 0,
            "website_visits": 0,
            "job_title": "",
            "company_size": 0,
            "days_since_last_activity": 90,
            "form_submissions": 0,
            "social_mentions": 5,
        }
        result = engine.score(lead)
        self.assertIn("social_mentions", result.factors)
        self.assertEqual(result.factors["social_mentions"], 10.0)

    def test_remove_rule(self):
        engine = LeadScoringEngine()
        self.assertTrue(engine.remove_rule("email_engagement"))
        self.assertFalse(engine.remove_rule("nonexistent_rule"))

    def test_score_to_dict(self):
        lead = {"lead_id": "x", "email_opens": 5, "email_clicks": 2,
                "website_visits": 3, "job_title": "Director",
                "company_size": 1000, "days_since_last_activity": 3,
                "form_submissions": 1}
        result = self.engine.score(lead)
        d = result.to_dict()
        self.assertIn("lead_id", d)
        self.assertIn("total_score", d)
        self.assertIn("category", d)
        self.assertIn("factors", d)
        self.assertIn("percentage", d)

    def test_percentage_calculation(self):
        lead = {"lead_id": "pct", "email_opens": 0, "email_clicks": 0,
                "website_visits": 0, "job_title": "", "company_size": 0,
                "days_since_last_activity": 90, "form_submissions": 0}
        result = self.engine.score(lead)
        self.assertGreaterEqual(result.percentage, 0)
        self.assertLessEqual(result.percentage, 100)

    def test_seniority_scoring(self):
        lead = {"lead_id": "sr", "email_opens": 0, "email_clicks": 0,
                "website_visits": 0, "job_title": "CEO",
                "company_size": 0, "days_since_last_activity": 90,
                "form_submissions": 0}
        result = self.engine.score(lead)
        self.assertEqual(result.factors["job_seniority"], 25.0)

    def test_company_size_scoring(self):
        lead = {"lead_id": "cs", "email_opens": 0, "email_clicks": 0,
                "website_visits": 0, "job_title": "",
                "company_size": 10000, "days_since_last_activity": 90,
                "form_submissions": 0}
        result = self.engine.score(lead)
        self.assertEqual(result.factors["company_size"], 20.0)

    def test_recency_scoring(self):
        lead = {"lead_id": "rec", "email_opens": 0, "email_clicks": 0,
                "website_visits": 0, "job_title": "",
                "company_size": 0, "days_since_last_activity": 1,
                "form_submissions": 0}
        result = self.engine.score(lead)
        self.assertEqual(result.factors["recency"], 15.0)

    def test_empty_lead_scores_zero(self):
        lead = {"lead_id": "empty"}
        result = self.engine.score(lead)
        self.assertEqual(result.total_score, 0.0)
        self.assertEqual(result.category, LeadCategory.COLD)


# ── Email Campaign Tests ────────────────────────────────────────


class TestEmailCampaign(unittest.TestCase):
    def test_create_campaign(self):
        cm = CampaignManager()
        campaign = cm.create_campaign(
            name="Welcome Series",
            subject="Welcome to APEX-OS",
            body_html="<h1>Welcome!</h1>",
            body_text="Welcome!",
            segment_ids=["seg_1", "seg_2"],
        )
        self.assertIsInstance(campaign, EmailCampaign)
        self.assertEqual(campaign.name, "Welcome Series")
        self.assertEqual(campaign.status, CampaignStatus.DRAFT)
        self.assertEqual(len(campaign.campaign_id), 36)  # UUID length

    def test_schedule_campaign(self):
        cm = CampaignManager()
        campaign = cm.create_campaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        future = datetime.utcnow() + timedelta(days=7)
        campaign.schedule(future)
        self.assertEqual(campaign.status, CampaignStatus.SCHEDULED)
        self.assertIsNotNone(campaign.scheduled_at)

    def test_send_campaign(self):
        cm = CampaignManager()
        campaign = cm.create_campaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        campaign.send(recipient_count=1000)
        self.assertEqual(campaign.status, CampaignStatus.SENT)
        self.assertEqual(campaign.recipients_count, 1000)
        self.assertIsNotNone(campaign.sent_at)

    def test_campaign_engagement_rates(self):
        campaign = EmailCampaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        campaign.recipients_count = 1000
        campaign.opens = 250
        campaign.clicks = 50
        campaign.bounces = 10
        campaign.unsubscribes = 5

        self.assertEqual(campaign.open_rate, 25.0)
        self.assertEqual(campaign.click_rate, 5.0)
        self.assertEqual(campaign.bounce_rate, 1.0)
        self.assertEqual(campaign.unsubscribe_rate, 0.5)
        self.assertEqual(campaign.click_to_open_rate, 20.0)

    def test_campaign_tracking(self):
        campaign = EmailCampaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        campaign.send(100)
        campaign.track_open()
        campaign.track_open()
        campaign.track_click()
        campaign.track_bounce()
        campaign.track_unsubscribe()
        campaign.track_reply()

        self.assertEqual(campaign.opens, 2)
        self.assertEqual(campaign.clicks, 1)
        self.assertEqual(campaign.bounces, 1)
        self.assertEqual(campaign.unsubscribes, 1)
        self.assertEqual(campaign.replies, 1)

    def test_campaign_pause(self):
        campaign = EmailCampaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        campaign.status = CampaignStatus.SENDING
        campaign.pause()
        self.assertEqual(campaign.status, CampaignStatus.PAUSED)

    def test_campaign_cancel(self):
        campaign = EmailCampaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        campaign.cancel()
        self.assertEqual(campaign.status, CampaignStatus.CANCELLED)

    def test_campaign_to_dict(self):
        campaign = EmailCampaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        d = campaign.to_dict()
        self.assertIn("campaign_id", d)
        self.assertIn("name", d)
        self.assertIn("status", d)
        self.assertIn("open_rate", d)
        self.assertIn("click_rate", d)

    def test_is_active(self):
        campaign = EmailCampaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        self.assertFalse(campaign.is_active)
        campaign.status = CampaignStatus.SENT
        self.assertTrue(campaign.is_active)

    def test_zero_recipients_rates(self):
        campaign = EmailCampaign(
            name="Test", subject="Test", body_html="<p>Test</p>"
        )
        self.assertEqual(campaign.open_rate, 0.0)
        self.assertEqual(campaign.click_rate, 0.0)
        self.assertEqual(campaign.bounce_rate, 0.0)


class TestCampaignManager(unittest.TestCase):
    def setUp(self):
        self.cm = CampaignManager()

    def test_create_and_get(self):
        c = self.cm.create_campaign("Test", "Subj", "<p>Body</p>")
        fetched = self.cm.get_campaign(c.campaign_id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Test")

    def test_list_campaigns(self):
        self.cm.create_campaign("A", "Subj", "<p>A</p>")
        self.cm.create_campaign("B", "Subj", "<p>B</p>")
        all_campaigns = self.cm.list_campaigns()
        self.assertEqual(len(all_campaigns), 2)

    def test_list_by_status(self):
        c1 = self.cm.create_campaign("A", "Subj", "<p>A</p>")
        c2 = self.cm.create_campaign("B", "Subj", "<p>B</p>")
        c2.send(100)
        sent = self.cm.list_campaigns(status=CampaignStatus.SENT)
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].name, "B")

    def test_delete_campaign(self):
        c = self.cm.create_campaign("Test", "Subj", "<p>Body</p>")
        self.assertTrue(self.cm.delete_campaign(c.campaign_id))
        self.assertIsNone(self.cm.get_campaign(c.campaign_id))

    def test_analytics_summary(self):
        c1 = self.cm.create_campaign("A", "Subj", "<p>A</p>")
        c1.send(1000)
        c1.opens = 200
        c1.clicks = 50
        c2 = self.cm.create_campaign("B", "Subj", "<p>B</p>")
        c2.send(500)
        c2.opens = 100
        c2.clicks = 25

        summary = self.cm.get_analytics_summary()
        self.assertEqual(summary["total_campaigns"], 2)
        self.assertEqual(summary["total_recipients"], 1500)
        self.assertEqual(summary["total_opens"], 300)
        self.assertEqual(summary["total_clicks"], 75)

    def test_top_performing(self):
        c1 = self.cm.create_campaign("A", "Subj", "<p>A</p>")
        c1.send(1000)
        c1.opens = 300
        c2 = self.cm.create_campaign("B", "Subj", "<p>B</p>")
        c2.send(1000)
        c2.opens = 500
        top = self.cm.get_top_performing(limit=1)
        self.assertEqual(len(top), 1)
        self.assertEqual(top[0].name, "B")

    def test_get_due_campaigns(self):
        c = self.cm.create_campaign("Test", "Subj", "<p>Body</p>")
        past = datetime.utcnow() - timedelta(hours=1)
        c.schedule(past)
        due = self.cm.get_due_campaigns()
        self.assertEqual(len(due), 1)

    def test_get_scheduled_campaigns(self):
        c = self.cm.create_campaign("Test", "Subj", "<p>Body</p>")
        future = datetime.utcnow() + timedelta(days=7)
        c.schedule(future)
        scheduled = self.cm.get_scheduled_campaigns()
        self.assertEqual(len(scheduled), 1)

    def test_empty_analytics(self):
        summary = self.cm.get_analytics_summary()
        self.assertEqual(summary["total_campaigns"], 0)
        self.assertEqual(summary["avg_open_rate"], 0.0)


# ── Deduplication Tests ─────────────────────────────────────────


class TestDeduplication(unittest.TestCase):
    def setUp(self):
        self.engine = DeduplicationEngine()

    def test_exact_email_match(self):
        contacts = [
            {"id": "c1", "name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"},
            {"id": "c2", "name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"},
        ]
        groups = self.engine.find_duplicates(contacts)
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0].contact_ids), 2)
        self.assertGreater(groups[0].confidence, 0.9)

    def test_fuzzy_name_match(self):
        contacts = [
            {"id": "c1", "name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"},
            {"id": "c2", "name": "Jon Doe", "email": "jon@example.com",
             "phone": "555-0100", "company": "Acme"},
        ]
        groups = self.engine.find_duplicates(contacts)
        self.assertGreaterEqual(len(groups), 1)

    def test_phone_match(self):
        contacts = [
            {"id": "c1", "name": "Alice", "email": "alice@example.com",
             "phone": "555-0100", "company": "Acme"},
            {"id": "c2", "name": "Bob", "email": "bob@example.com",
             "phone": "5550100", "company": "Beta"},
        ]
        groups = self.engine.find_duplicates(contacts)
        self.assertGreaterEqual(len(groups), 1)

    def test_no_duplicates(self):
        contacts = [
            {"id": "c1", "name": "Alice", "email": "alice@example.com",
             "phone": "555-0100", "company": "Acme"},
            {"id": "c2", "name": "Bob", "email": "bob@example.com",
             "phone": "555-0200", "company": "Beta"},
        ]
        groups = self.engine.find_duplicates(contacts)
        self.assertEqual(len(groups), 0)

    def test_merge_contacts(self):
        contacts = [
            {"id": "c1", "name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme", "notes": "VIP"},
            {"id": "c2", "name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme", "notes": ""},
        ]
        groups = self.engine.find_duplicates(contacts)
        merged = self.engine.merge_contacts(contacts, groups[0])
        self.assertEqual(merged["name"], "John Doe")
        self.assertEqual(merged["notes"], "VIP")
        self.assertIn("merged_from", merged)

    def test_full_deduplication(self):
        contacts = [
            {"id": "c1", "name": "John", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"},
            {"id": "c2", "name": "John", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"},
            {"id": "c3", "name": "Alice", "email": "alice@example.com",
             "phone": "555-0200", "company": "Beta"},
        ]
        unique, groups = self.engine.deduplicate(contacts)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(groups), 1)

    def test_similarity_computation(self):
        a = {"name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"}
        b = {"name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"}
        score, reasons = self.engine.compute_similarity(a, b)
        self.assertGreater(score, 0.9)
        self.assertIn("email_match", reasons)

    def test_custom_threshold(self):
        engine = DeduplicationEngine(threshold=0.95)
        contacts = [
            {"id": "c1", "name": "John Doe", "email": "john@example.com",
             "phone": "555-0100", "company": "Acme"},
            {"id": "c2", "name": "Jon Doe", "email": "jon@example.com",
             "phone": "555-0100", "company": "Acme"},
        ]
        groups = engine.find_duplicates(contacts)
        # With very high threshold, fuzzy matches may not qualify
        self.assertIsInstance(groups, list)

    def test_empty_contacts(self):
        groups = self.engine.find_duplicates([])
        self.assertEqual(len(groups), 0)

    def test_single_contact(self):
        groups = self.engine.find_duplicates([
            {"id": "c1", "name": "John", "email": "john@example.com"}
        ])
        self.assertEqual(len(groups), 0)

    def test_duplicate_group_to_dict(self):
        group = DuplicateGroup(
            group_id="dg_0",
            contact_ids=["c1", "c2"],
            confidence=0.92,
            match_reasons=["email_match", "phone_match"],
            canonical_id="c1",
        )
        d = group.to_dict()
        self.assertEqual(d["group_id"], "dg_0")
        self.assertEqual(d["confidence"], 0.92)
        self.assertEqual(len(d["contact_ids"]), 2)

    def test_phone_normalization(self):
        a = {"name": "A", "email": "a@test.com", "phone": "+1-555-0100",
             "company": "X"}
        b = {"name": "B", "email": "b@test.com", "phone": "15550100",
             "company": "Y"}
        score, reasons = self.engine.compute_similarity(a, b)
        self.assertIn("phone_match", reasons)

    def test_company_match(self):
        a = {"name": "A", "email": "a@test.com", "phone": "555-0100",
             "company": "Acme Corp"}
        b = {"name": "B", "email": "b@test.com", "phone": "555-0200",
             "company": "Acme Corp"}
        score, reasons = self.engine.compute_similarity(a, b)
        self.assertIn("company_match", reasons)


# ── Forecasting Tests ───────────────────────────────────────────


class TestSalesForecaster(unittest.TestCase):
    def setUp(self):
        self.forecaster = SalesForecaster()

    def test_forecast_basic(self):
        data = [
            {"date": "2024-01-01", "revenue": 10000},
            {"date": "2024-02-01", "revenue": 12000},
            {"date": "2024-03-01", "revenue": 11000},
            {"date": "2024-04-01", "revenue": 13000},
            {"date": "2024-05-01", "revenue": 15000},
        ]
        results = self.forecaster.forecast(data, periods=3)
        self.assertEqual(len(results), 3)
        for r in results:
            self.assertIsInstance(r, ForecastResult)
            self.assertGreater(r.predicted_revenue, 0)
            self.assertLessEqual(r.confidence_low, r.predicted_revenue)
            self.assertGreaterEqual(r.confidence_high, r.predicted_revenue)

    def test_forecast_trend_up(self):
        data = [
            {"date": "2024-01-01", "revenue": 10000},
            {"date": "2024-02-01", "revenue": 12000},
            {"date": "2024-03-01", "revenue": 14000},
            {"date": "2024-04-01", "revenue": 16000},
            {"date": "2024-05-01", "revenue": 18000},
        ]
        results = self.forecaster.forecast(data, periods=1)
        self.assertEqual(results[0].trend_direction, "up")
        self.assertGreater(results[0].trend_slope, 0)

    def test_forecast_trend_down(self):
        data = [
            {"date": "2024-01-01", "revenue": 18000},
            {"date": "2024-02-01", "revenue": 16000},
            {"date": "2024-03-01", "revenue": 14000},
            {"date": "2024-04-01", "revenue": 12000},
            {"date": "2024-05-01", "revenue": 10000},
        ]
        results = self.forecaster.forecast(data, periods=1)
        self.assertEqual(results[0].trend_direction, "down")
        self.assertLess(results[0].trend_slope, 0)

    def test_forecast_empty_data(self):
        results = self.forecaster.forecast([], periods=3)
        self.assertEqual(len(results), 0)

    def test_forecast_single_data_point(self):
        data = [{"date": "2024-01-01", "revenue": 10000}]
        results = self.forecaster.forecast(data, periods=2)
        self.assertEqual(len(results), 2)

    def test_forecast_from_pipeline(self):
        pipeline = [
            {"stage": "prospecting", "value": 50000, "probability": 0.1},
            {"stage": "qualification", "value": 30000, "probability": 0.3},
            {"stage": "proposal", "value": 20000, "probability": 0.6},
            {"stage": "negotiation", "value": 10000, "probability": 0.8},
            {"stage": "closed_won", "value": 5000, "probability": 1.0},
        ]
        results = self.forecaster.forecast_from_pipeline(pipeline, periods=3)
        self.assertEqual(len(results), 3)

    def test_forecast_summary(self):
        data = [
            {"date": "2024-01-01", "revenue": 10000},
            {"date": "2024-02-01", "revenue": 12000},
            {"date": "2024-03-01", "revenue": 11000},
        ]
        forecast = self.forecaster.forecast(data, periods=3)
        summary = self.forecaster.get_summary(forecast)
        self.assertIn("total_predicted", summary)
        self.assertIn("avg_predicted", summary)
        self.assertIn("trend", summary)
        self.assertIn("confidence_range", summary)
        self.assertEqual(summary["periods"], 3)

    def test_forecast_to_dict(self):
        data = [
            {"date": "2024-01-01", "revenue": 10000},
            {"date": "2024-02-01", "revenue": 12000},
        ]
        results = self.forecaster.forecast(data, periods=1)
        d = results[0].to_dict()
        self.assertIn("period", d)
        self.assertIn("predicted_revenue", d)
        self.assertIn("confidence_low", d)
        self.assertIn("confidence_high", d)
        self.assertIn("trend_direction", d)

    def test_confidence_level_validation(self):
        with self.assertRaises(ValueError):
            SalesForecaster(confidence_level=0)
        with self.assertRaises(ValueError):
            SalesForecaster(confidence_level=1.5)

    def test_forecast_flat_trend(self):
        data = [
            {"date": "2024-01-01", "revenue": 10000},
            {"date": "2024-02-01", "revenue": 10100},
            {"date": "2024-03-01", "revenue": 9900},
            {"date": "2024-04-01", "revenue": 10050},
        ]
        results = self.forecaster.forecast(data, periods=1)
        self.assertEqual(results[0].trend_direction, "flat")

    def test_forecast_period_labels(self):
        data = [
            {"date": "2024-01-01", "revenue": 10000},
            {"date": "2024-02-01", "revenue": 12000},
        ]
        results = self.forecaster.forecast(data, periods=3, period_days=30)
        # Periods should be future months
        self.assertTrue(results[0].period.startswith("2024"))

    def test_empty_pipeline_forecast(self):
        results = self.forecaster.forecast_from_pipeline([], periods=3)
        self.assertEqual(len(results), 0)


# ── Segmentation Tests ──────────────────────────────────────────


class TestCustomerSegmentation(unittest.TestCase):
    def setUp(self):
        self.seg = CustomerSegmentation()

    def test_rfm_scoring(self):
        customer = {
            "customer_id": "c1",
            "last_purchase_days": 5,
            "purchase_count": 12,
            "total_spent": 15000,
        }
        rfm = self.seg.compute_rfm(customer)
        self.assertEqual(rfm["r"], 5)
        self.assertEqual(rfm["f"], 5)
        self.assertEqual(rfm["m"], 5)

    def test_rfm_low_scores(self):
        customer = {
            "customer_id": "c2",
            "last_purchase_days": 120,
            "purchase_count": 1,
            "total_spent": 50,
        }
        rfm = self.seg.compute_rfm(customer)
        self.assertEqual(rfm["r"], 1)
        self.assertEqual(rfm["f"], 1)
        self.assertEqual(rfm["m"], 1)

    def test_segment_customers(self):
        customers = [
            {"customer_id": "c1", "last_purchase_days": 3,
             "purchase_count": 15, "total_spent": 20000},
            {"customer_id": "c2", "last_purchase_days": 100,
             "purchase_count": 1, "total_spent": 100},
            {"customer_id": "c3", "last_purchase_days": 5,
             "purchase_count": 8, "total_spent": 5000},
        ]
        segments = self.seg.segment_customers(customers)
        self.assertIn("champions", segments)
        self.assertIn("lost", segments)
        self.assertIn("loyal_customers", segments)

    def test_segment_distribution(self):
        customers = [
            {"customer_id": "c1", "last_purchase_days": 3,
             "purchase_count": 15, "total_spent": 20000},
            {"customer_id": "c2", "last_purchase_days": 100,
             "purchase_count": 1, "total_spent": 100},
        ]
        self.seg.segment_customers(customers)
        dist = self.seg.get_segment_distribution()
        self.assertIn("champions", dist)
        self.assertIn("lost", dist)
        self.assertEqual(sum(dist.values()), 2)

    def test_segment_stats(self):
        customers = [
            {"customer_id": "c1", "last_purchase_days": 3,
             "purchase_count": 15, "total_spent": 20000},
            {"customer_id": "c2", "last_purchase_days": 100,
             "purchase_count": 1, "total_spent": 100},
        ]
        self.seg.segment_customers(customers)
        stats = self.seg.get_segment_stats()
        self.assertIn("champions", stats)
        self.assertIn("percentage", stats["champions"])

    def test_custom_segment(self):
        seg = self.seg.create_custom_segment(
            name="VIP",
            member_ids=["c1", "c2", "c3"],
            description="High value customers",
        )
        self.assertEqual(seg.name, "VIP")
        self.assertEqual(seg.size, 3)
        self.assertEqual(seg.segment_type, SegmentType.CUSTOM)

    def test_behavioral_segment(self):
        customers = [
            {"customer_id": "c1", "page_views": 5},
            {"customer_id": "c2", "page_views": 50},
            {"customer_id": "c3", "page_views": 200},
        ]
        segments = self.seg.behavioral_segment(
            customers,
            activity_key="page_views",
            thresholds=[10, 100],
            labels=["low", "medium", "high"],
        )
        self.assertIn("low", segments)
        self.assertIn("medium", segments)
        self.assertIn("high", segments)
        self.assertEqual(segments["low"].size, 1)
        self.assertEqual(segments["medium"].size, 1)
        self.assertEqual(segments["high"].size, 1)

    def test_demographic_segment(self):
        customers = [
            {"customer_id": "c1", "country": "US"},
            {"customer_id": "c2", "country": "UK"},
            {"customer_id": "c3", "country": "US"},
        ]
        segments = self.seg.demographic_segment(customers, "country")
        self.assertIn("US", segments)
        self.assertIn("UK", segments)
        self.assertEqual(segments["US"].size, 2)
        self.assertEqual(segments["UK"].size, 1)

    def test_segment_to_dict(self):
        seg = Segment(
            name="Test",
            segment_type=SegmentType.RFM,
            criteria={"r": (4, 5)},
            member_ids=["c1"],
        )
        d = seg.to_dict()
        self.assertIn("segment_id", d)
        self.assertIn("name", d)
        self.assertIn("type", d)
        self.assertIn("size", d)

    def test_get_segment(self):
        customers = [
            {"customer_id": "c1", "last_purchase_days": 3,
             "purchase_count": 15, "total_spent": 20000},
        ]
        self.seg.segment_customers(customers)
        champions = self.seg.get_segment("champions")
        self.assertIsNotNone(champions)
        self.assertIn("c1", champions.member_ids)

    def test_get_all_segments(self):
        customers = [
            {"customer_id": "c1", "last_purchase_days": 3,
             "purchase_count": 15, "total_spent": 20000},
        ]
        self.seg.segment_customers(customers)
        all_segs = self.seg.get_all_segments()
        self.assertGreater(len(all_segs), 0)

    def test_empty_customers(self):
        segments = self.seg.segment_customers([])
        # Should still have segment definitions
        self.assertIn("champions", segments)

    def test_rfm_boundary_values(self):
        # Test exact threshold boundaries
        customer = {
            "customer_id": "c1",
            "last_purchase_days": 7,   # Exactly at threshold
            "purchase_count": 10,       # Exactly at threshold
            "total_spent": 10000,       # Exactly at threshold
        }
        rfm = self.seg.compute_rfm(customer)
        self.assertEqual(rfm["r"], 5)
        self.assertEqual(rfm["f"], 5)
        self.assertEqual(rfm["m"], 5)

    def test_new_customer_segment(self):
        customers = [
            {"customer_id": "c1", "last_purchase_days": 2,
             "purchase_count": 1, "total_spent": 500},
        ]
        segments = self.seg.segment_customers(customers)
        # Should be classified as new_customers or potential_loyalists
        new_or_potential = (
            segments["new_customers"].member_ids
            + segments["potential_loyalists"].member_ids
        )
        self.assertIn("c1", new_or_potential)

    def test_at_risk_segment(self):
        customers = [
            {"customer_id": "c1", "last_purchase_days": 45,
             "purchase_count": 8, "total_spent": 8000},
        ]
        segments = self.seg.segment_customers(customers)
        # Should be at_risk or cannot_lose
        at_risk_or_cannot_lose = (
            segments["at_risk"].member_ids
            + segments["cannot_lose"].member_ids
        )
        self.assertIn("c1", at_risk_or_cannot_lose)


if __name__ == "__main__":
    unittest.main()

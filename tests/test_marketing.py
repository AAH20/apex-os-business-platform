"""Tests for marketing automation module."""
import pytest
from apex_os_bp.marketing.models import (
    ABTest,
    ABVariant,
    CampaignMetrics,
    CampaignStatus,
    EmailCampaign,
    EmailTemplate,
    Lead,
    LeadEnrollment,
    LeadStatus,
    NurtureSequence,
    NurtureStep,
    ROIReport,
    TestStatus,
)
from apex_os_bp.marketing.email_campaigns import EmailCampaignManager
from apex_os_bp.marketing.lead_nurturing import LeadNurturingEngine
from apex_os_bp.marketing.ab_testing import ABTestingEngine
from apex_os_bp.marketing.analytics import MarketingAnalytics
from apex_os_bp.marketing.roi import ROICalculator


class TestEmailCampaignModels:
    """Test email campaign data models."""

    def test_email_template_creation(self):
        """Email template can be created."""
        template = EmailTemplate(id="t-1", name="Welcome", subject="Hello", body="Welcome!")
        assert template.id == "t-1"
        assert template.name == "Welcome"
        assert template.subject == "Hello"
        assert template.body == "Welcome!"

    def test_campaign_metrics_rates(self):
        """Campaign metrics calculate rates correctly."""
        metrics = CampaignMetrics(sent=100, delivered=95, opened=30, clicked=10, converted=5, bounced=5)
        assert metrics.open_rate == pytest.approx(30 / 95)
        assert metrics.click_rate == pytest.approx(10 / 95)
        assert metrics.conversion_rate == pytest.approx(5 / 95)
        assert metrics.bounce_rate == pytest.approx(5 / 100)

    def test_campaign_metrics_zero_division(self):
        """Campaign metrics handle zero division gracefully."""
        metrics = CampaignMetrics()
        assert metrics.open_rate == 0.0
        assert metrics.click_rate == 0.0
        assert metrics.conversion_rate == 0.0

    def test_email_campaign_creation(self):
        """Email campaign can be created."""
        campaign = EmailCampaign(id="c-1", name="Test", subject="Hi", body="Body")
        assert campaign.id == "c-1"
        assert campaign.name == "Test"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.segments == []

    def test_campaign_metrics_to_dict(self):
        """Campaign metrics can be converted to dict."""
        metrics = CampaignMetrics(sent=100, delivered=90, opened=45, clicked=20, converted=5)
        d = metrics.to_dict()
        assert d["sent"] == 100
        assert d["delivered"] == 90
        assert d["opened"] == 45
        assert d["clicked"] == 20
        assert d["converted"] == 5
        assert "open_rate" in d
        assert "click_rate" in d
        assert "conversion_rate" in d


class TestEmailCampaignManager:
    """Test email campaign manager."""

    def test_create_template(self):
        """Template can be created."""
        mgr = EmailCampaignManager()
        template = mgr.create_template("Welcome", "Hello", "Welcome body")
        assert template.name == "Welcome"
        assert template.subject == "Hello"
        assert template.body == "Welcome body"

    def test_get_template(self):
        """Template can be retrieved by ID."""
        mgr = EmailCampaignManager()
        template = mgr.create_template("Welcome", "Hello", "Body")
        retrieved = mgr.get_template(template.id)
        assert retrieved is not None
        assert retrieved.name == "Welcome"

    def test_get_template_not_found(self):
        """Non-existent template returns None."""
        mgr = EmailCampaignManager()
        assert mgr.get_template("nonexistent") is None

    def test_create_campaign(self):
        """Campaign can be created."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test Campaign", "Subject", "Body", segments=["all"])
        assert campaign.name == "Test Campaign"
        assert campaign.subject == "Subject"
        assert campaign.body == "Body"
        assert campaign.segments == ["all"]
        assert campaign.status == CampaignStatus.DRAFT

    def test_get_campaign(self):
        """Campaign can be retrieved by ID."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test", "Subject", "Body")
        retrieved = mgr.get_campaign(campaign.id)
        assert retrieved is not None
        assert retrieved.name == "Test"

    def test_send_campaign(self):
        """Campaign can be sent."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test", "Subject", "Body")
        metrics = mgr.send_campaign(campaign.id, recipient_count=200)
        assert metrics.sent == 200
        assert metrics.delivered == 200
        assert campaign.status == CampaignStatus.SENT

    def test_send_campaign_not_found(self):
        """Sending non-existent campaign raises error."""
        mgr = EmailCampaignManager()
        with pytest.raises(ValueError, match="Campaign not found"):
            mgr.send_campaign("nonexistent")

    def test_send_campaign_already_sent(self):
        """Sending already-sent campaign raises error."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test", "Subject", "Body")
        mgr.send_campaign(campaign.id)
        with pytest.raises(ValueError, match="already sent"):
            mgr.send_campaign(campaign.id)

    def test_track_event(self):
        """Events can be tracked."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test", "Subject", "Body")
        mgr.send_campaign(campaign.id)
        mgr.track_event(campaign.id, "open")
        mgr.track_event(campaign.id, "click")
        mgr.track_event(campaign.id, "conversion")
        assert campaign.metrics.opened == 1
        assert campaign.metrics.clicked == 1
        assert campaign.metrics.converted == 1

    def test_track_event_invalid(self):
        """Invalid event type raises error."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test", "Subject", "Body")
        mgr.send_campaign(campaign.id)
        with pytest.raises(ValueError, match="Unknown event type"):
            mgr.track_event(campaign.id, "invalid")

    def test_get_campaign_report(self):
        """Campaign report can be generated."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test", "Subject", "Body")
        mgr.send_campaign(campaign.id, recipient_count=100)
        mgr.track_event(campaign.id, "open")
        report = mgr.get_campaign_report(campaign.id)
        assert report["campaign_id"] == campaign.id
        assert report["name"] == "Test"
        assert report["metrics"]["sent"] == 100
        assert report["metrics"]["opened"] == 1

    def test_list_campaigns(self):
        """Campaigns can be listed."""
        mgr = EmailCampaignManager()
        mgr.create_campaign("Campaign 1", "S1", "B1")
        mgr.create_campaign("Campaign 2", "S2", "B2")
        campaigns = mgr.list_campaigns()
        assert len(campaigns) == 2

    def test_list_campaigns_by_status(self):
        """Campaigns can be filtered by status."""
        mgr = EmailCampaignManager()
        c1 = mgr.create_campaign("Campaign 1", "S1", "B1")
        mgr.create_campaign("Campaign 2", "S2", "B2")
        mgr.send_campaign(c1.id)
        sent = mgr.list_campaigns(status=CampaignStatus.SENT)
        assert len(sent) == 1
        assert sent[0].name == "Campaign 1"

    def test_delete_campaign(self):
        """Campaign can be deleted."""
        mgr = EmailCampaignManager()
        campaign = mgr.create_campaign("Test", "Subject", "Body")
        assert mgr.delete_campaign(campaign.id) is True
        assert mgr.get_campaign(campaign.id) is None

    def test_delete_campaign_not_found(self):
        """Deleting non-existent campaign returns False."""
        mgr = EmailCampaignManager()
        assert mgr.delete_campaign("nonexistent") is False

    def test_get_aggregate_metrics(self):
        """Aggregate metrics across all campaigns."""
        mgr = EmailCampaignManager()
        c1 = mgr.create_campaign("C1", "S1", "B1")
        c2 = mgr.create_campaign("C2", "S2", "B2")
        mgr.send_campaign(c1.id, recipient_count=100)
        mgr.send_campaign(c2.id, recipient_count=200)
        mgr.track_event(c1.id, "open")
        mgr.track_event(c2.id, "open")
        mgr.track_event(c2.id, "click")
        agg = mgr.get_aggregate_metrics()
        assert agg["sent"] == 300
        assert agg["delivered"] == 300
        assert agg["opened"] == 2
        assert agg["clicked"] == 1


class TestLeadNurturingModels:
    """Test lead nurturing data models."""

    def test_lead_creation(self):
        """Lead can be created."""
        lead = Lead(id="l-1", name="John", email="john@example.com")
        assert lead.id == "l-1"
        assert lead.name == "John"
        assert lead.email == "john@example.com"
        assert lead.score == 0.0
        assert lead.status == LeadStatus.NEW

    def test_nurture_sequence_creation(self):
        """Nurture sequence can be created."""
        seq = NurtureSequence(id="ns-1", name="Onboarding")
        assert seq.id == "ns-1"
        assert seq.name == "Onboarding"
        assert seq.steps == []

    def test_nurture_step_creation(self):
        """Nurture step can be created."""
        template = EmailTemplate(id="t-1", name="Welcome", subject="Hi", body="Body")
        step = NurtureStep(id="step-1", sequence_id="ns-1", email_template=template, delay_days=2)
        assert step.id == "step-1"
        assert step.sequence_id == "ns-1"
        assert step.delay_days == 2
        assert step.order == 0

    def test_lead_enrollment_creation(self):
        """Lead enrollment can be created."""
        enrollment = LeadEnrollment(id="e-1", lead_id="l-1", sequence_id="ns-1")
        assert enrollment.id == "e-1"
        assert enrollment.lead_id == "l-1"
        assert enrollment.sequence_id == "ns-1"
        assert enrollment.status == "active"
        assert enrollment.current_step == 0


class TestLeadNurturingEngine:
    """Test lead nurturing engine."""

    def test_create_lead(self):
        """Lead can be created."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com", source="web")
        assert lead.name == "John"
        assert lead.email == "john@example.com"
        assert lead.source == "web"
        assert lead.status == LeadStatus.NEW

    def test_get_lead(self):
        """Lead can be retrieved by ID."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        retrieved = engine.get_lead(lead.id)
        assert retrieved is not None
        assert retrieved.name == "John"

    def test_get_lead_not_found(self):
        """Non-existent lead returns None."""
        engine = LeadNurturingEngine()
        assert engine.get_lead("nonexistent") is None

    def test_update_lead_score(self):
        """Lead score can be updated."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.update_lead_score(lead.id, 5.0)
        assert lead.score == 5.0

    def test_track_engagement_open(self):
        """Opening email increases lead score."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.track_engagement(lead.id, "open")
        assert lead.score == pytest.approx(engine.SCORE_OPEN)

    def test_track_engagement_click(self):
        """Clicking increases lead score."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.track_engagement(lead.id, "click")
        assert lead.score == pytest.approx(engine.SCORE_CLICK)

    def test_track_engagement_conversion(self):
        """Conversion sets lead status to CONVERTED."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.track_engagement(lead.id, "conversion")
        assert lead.status == LeadStatus.CONVERTED
        assert lead.score == pytest.approx(engine.SCORE_CONVERSION)

    def test_track_engagement_unsubscribe(self):
        """Unsubscribe decreases lead score."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.track_engagement(lead.id, "unsubscribe")
        assert lead.score == pytest.approx(engine.SCORE_UNSUBSCRIBE)

    def test_lead_status_progression(self):
        """Lead status progresses with engagement."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        assert lead.status == LeadStatus.NEW
        for _ in range(10):
            engine.track_engagement(lead.id, "open")
        assert lead.status == LeadStatus.ENGAGED

    def test_create_sequence(self):
        """Nurture sequence can be created."""
        engine = LeadNurturingEngine()
        seq = engine.create_sequence("Onboarding")
        assert seq.name == "Onboarding"
        assert seq.steps == []

    def test_add_step_to_sequence(self):
        """Step can be added to sequence."""
        engine = LeadNurturingEngine()
        seq = engine.create_sequence("Onboarding")
        template = EmailTemplate(id="t-1", name="Welcome", subject="Hi", body="Body")
        step = engine.add_step_to_sequence(seq.id, template, delay_days=1)
        assert step.sequence_id == seq.id
        assert step.delay_days == 1
        assert step.order == 0
        assert len(seq.steps) == 1

    def test_enroll_lead(self):
        """Lead can be enrolled in a sequence."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        seq = engine.create_sequence("Onboarding")
        enrollment = engine.enroll_lead(lead.id, seq.id)
        assert enrollment.lead_id == lead.id
        assert enrollment.sequence_id == seq.id
        assert enrollment.status == "active"

    def test_enroll_lead_not_found(self):
        """Enrolling non-existent lead raises error."""
        engine = LeadNurturingEngine()
        seq = engine.create_sequence("Onboarding")
        with pytest.raises(ValueError, match="Lead not found"):
            engine.enroll_lead("nonexistent", seq.id)

    def test_process_enrollments(self):
        """Enrollments can be processed."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        seq = engine.create_sequence("Onboarding")
        template = EmailTemplate(id="t-1", name="Welcome", subject="Hi", body="Body")
        engine.add_step_to_sequence(seq.id, template, delay_days=0)
        engine.enroll_lead(lead.id, seq.id)
        results = engine.process_enrollments()
        assert len(results) == 1
        assert results[0]["lead_id"] == lead.id

    def test_get_lead_journey(self):
        """Lead journey can be retrieved."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        seq = engine.create_sequence("Onboarding")
        engine.enroll_lead(lead.id, seq.id)
        journey = engine.get_lead_journey(lead.id)
        assert len(journey) == 1
        assert journey[0]["sequence_name"] == "Onboarding"

    def test_list_leads(self):
        """Leads can be listed."""
        engine = LeadNurturingEngine()
        engine.create_lead("John", "john@example.com")
        engine.create_lead("Jane", "jane@example.com")
        leads = engine.list_leads()
        assert len(leads) == 2

    def test_list_leads_by_status(self):
        """Leads can be filtered by status."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.track_engagement(lead.id, "conversion")
        converted = engine.list_leads(status=LeadStatus.CONVERTED)
        assert len(converted) == 1
        assert converted[0].name == "John"

    def test_list_leads_by_min_score(self):
        """Leads can be filtered by minimum score."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.update_lead_score(lead.id, 15.0)
        engine.create_lead("Jane", "jane@example.com")
        qualified = engine.list_leads(min_score=10.0)
        assert len(qualified) == 1
        assert qualified[0].name == "John"

    def test_get_lead_score(self):
        """Lead score can be retrieved."""
        engine = LeadNurturingEngine()
        lead = engine.create_lead("John", "john@example.com")
        engine.update_lead_score(lead.id, 7.5)
        assert engine.get_lead_score(lead.id) == pytest.approx(7.5)


class TestABTestingModels:
    """Test A/B testing data models."""

    def test_ab_test_creation(self):
        """A/B test can be created."""
        test = ABTest(id="ab-1", name="Subject Line Test")
        assert test.id == "ab-1"
        assert test.name == "Subject Line Test"
        assert test.status == TestStatus.DRAFT
        assert test.variants == []

    def test_ab_variant_creation(self):
        """A/B variant can be created."""
        variant = ABVariant(id="v-1", test_id="ab-1", name="Control", subject="A", body="Body A")
        assert variant.id == "v-1"
        assert variant.name == "Control"
        assert variant.traffic_allocation == 0.5

    def test_roi_report_creation(self):
        """ROI report can be created."""
        report = ROIReport(
            campaign_id="c-1",
            campaign_name="Test",
            total_cost=1000.0,
            total_revenue=3000.0,
            roi=200.0,
            roas=3.0,
            cost_per_lead=10.0,
            cost_per_acquisition=100.0,
            leads_generated=100,
            conversions=10,
        )
        assert report.campaign_id == "c-1"
        assert report.roi == 200.0
        assert report.roas == 3.0


class TestABTestingEngine:
    """Test A/B testing engine."""

    def test_create_test(self):
        """A/B test can be created."""
        engine = ABTestingEngine()
        test = engine.create_test("Subject Line Test")
        assert test.name == "Subject Line Test"
        assert test.status == TestStatus.DRAFT

    def test_add_variant(self):
        """Variant can be added to test."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        variant = engine.add_variant(test.id, "Control", "Subject A", "Body A")
        assert variant.name == "Control"
        assert variant.traffic_allocation == 0.5
        assert len(test.variants) == 1

    def test_add_variant_to_running_test_fails(self):
        """Cannot add variants to a running test."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        engine.add_variant(test.id, "A", "S1", "B1")
        engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        with pytest.raises(ValueError, match="Cannot add variants"):
            engine.add_variant(test.id, "C", "S3", "B3")

    def test_start_test(self):
        """Test can be started."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        engine.add_variant(test.id, "A", "S1", "B1")
        engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        assert test.status == TestStatus.RUNNING
        assert test.start_date is not None

    def test_start_test_insufficient_variants(self):
        """Cannot start test with fewer than 2 variants."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        engine.add_variant(test.id, "A", "S1", "B1")
        with pytest.raises(ValueError, match="at least 2 variants"):
            engine.start_test(test.id)

    def test_stop_test(self):
        """Test can be stopped."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        engine.add_variant(test.id, "A", "S1", "B1")
        engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        engine.stop_test(test.id)
        assert test.status == TestStatus.COMPLETED
        assert test.end_date is not None

    def test_track_event(self):
        """Events can be tracked for a variant."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        v1 = engine.add_variant(test.id, "A", "S1", "B1")
        engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        engine.track_event(test.id, v1.id, "open")
        engine.track_event(test.id, v1.id, "click")
        engine.track_event(test.id, v1.id, "conversion")
        assert v1.metrics.opened == 1
        assert v1.metrics.clicked == 1
        assert v1.metrics.converted == 1

    def test_get_variant_performance(self):
        """Variant performance can be retrieved."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        v1 = engine.add_variant(test.id, "A", "S1", "B1")
        engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        engine.track_event(test.id, v1.id, "open")
        perf = engine.get_variant_performance(test.id, v1.id)
        assert perf["name"] == "A"
        assert perf["metrics"]["opened"] == 1

    def test_determine_winner(self):
        """Winner can be determined based on conversion rate."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        v1 = engine.add_variant(test.id, "A", "S1", "B1")
        v2 = engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        v1.metrics.delivered = 100
        v1.metrics.converted = 10
        v2.metrics.delivered = 100
        v2.metrics.converted = 5
        winner_id = engine.determine_winner(test.id)
        assert winner_id == v1.id
        assert test.winner_variant_id == v1.id

    def test_get_test_report(self):
        """Test report can be generated."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        engine.add_variant(test.id, "A", "S1", "B1")
        engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        report = engine.get_test_report(test.id)
        assert report["test_id"] == test.id
        assert report["name"] == "Test"
        assert len(report["variants"]) == 2
        assert "statistical_significance" in report

    def test_list_tests(self):
        """Tests can be listed."""
        engine = ABTestingEngine()
        engine.create_test("Test 1")
        engine.create_test("Test 2")
        tests = engine.list_tests()
        assert len(tests) == 2

    def test_list_tests_by_status(self):
        """Tests can be filtered by status."""
        engine = ABTestingEngine()
        t1 = engine.create_test("Test 1")
        engine.create_test("Test 2")
        engine.add_variant(t1.id, "A", "S1", "B1")
        engine.add_variant(t1.id, "B", "S2", "B2")
        engine.start_test(t1.id)
        running = engine.list_tests(status=TestStatus.RUNNING)
        assert len(running) == 1
        assert running[0].name == "Test 1"

    def test_is_statistically_significant(self):
        """Statistical significance can be checked."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        v1 = engine.add_variant(test.id, "A", "S1", "B1")
        v2 = engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        v1.metrics.delivered = 1000
        v1.metrics.converted = 100
        v2.metrics.delivered = 1000
        v2.metrics.converted = 50
        assert engine.is_statistically_significant(test.id) is True

    def test_is_not_statistically_significant(self):
        """Non-significant results are detected."""
        engine = ABTestingEngine()
        test = engine.create_test("Test")
        v1 = engine.add_variant(test.id, "A", "S1", "B1")
        v2 = engine.add_variant(test.id, "B", "S2", "B2")
        engine.start_test(test.id)
        v1.metrics.delivered = 100
        v1.metrics.converted = 10
        v2.metrics.delivered = 100
        v2.metrics.converted = 9
        assert engine.is_statistically_significant(test.id) is False


class TestMarketingAnalytics:
    """Test marketing analytics engine."""

    def test_track_event(self):
        """Event can be tracked."""
        analytics = MarketingAnalytics()
        event = analytics.track_event("open", campaign_id="c-1", lead_id="l-1")
        assert event["type"] == "open"
        assert event["campaign_id"] == "c-1"
        assert event["lead_id"] == "l-1"

    def test_get_events(self):
        """Events can be retrieved."""
        analytics = MarketingAnalytics()
        analytics.track_event("open", campaign_id="c-1")
        analytics.track_event("click", campaign_id="c-1")
        analytics.track_event("open", campaign_id="c-2")
        events = analytics.get_events()
        assert len(events) == 3

    def test_get_events_filtered_by_type(self):
        """Events can be filtered by type."""
        analytics = MarketingAnalytics()
        analytics.track_event("open", campaign_id="c-1")
        analytics.track_event("click", campaign_id="c-1")
        opens = analytics.get_events(event_type="open")
        assert len(opens) == 1

    def test_get_events_filtered_by_campaign(self):
        """Events can be filtered by campaign."""
        analytics = MarketingAnalytics()
        analytics.track_event("open", campaign_id="c-1")
        analytics.track_event("open", campaign_id="c-2")
        events = analytics.get_events(campaign_id="c-1")
        assert len(events) == 1

    def test_get_campaign_analytics(self):
        """Campaign analytics can be generated."""
        analytics = MarketingAnalytics()
        analytics.track_event("open", campaign_id="c-1")
        analytics.track_event("click", campaign_id="c-1")
        analytics.track_event("conversion", campaign_id="c-1")
        result = analytics.get_campaign_analytics("c-1")
        assert result["campaign_id"] == "c-1"
        assert result["total_events"] == 3
        assert result["metrics"]["opened"] == 1
        assert result["metrics"]["clicked"] == 1
        assert result["metrics"]["converted"] == 1

    def test_get_funnel_analysis(self):
        """Funnel analysis can be generated."""
        analytics = MarketingAnalytics()
        analytics.set_funnel_stage("visit", 1000)
        analytics.set_funnel_stage("signup", 500)
        analytics.set_funnel_stage("purchase", 100)
        result = analytics.get_funnel_analysis(["visit", "signup", "purchase"])
        assert result["stages"]["visit"]["count"] == 1000
        assert result["stages"]["signup"]["count"] == 500
        assert result["stages"]["purchase"]["count"] == 100
        assert result["overall_conversion"] == pytest.approx(0.1)

    def test_get_engagement_trends(self):
        """Engagement trends can be retrieved."""
        analytics = MarketingAnalytics()
        analytics.track_event("open")
        analytics.track_event("click")
        analytics.track_event("conversion")
        trends = analytics.get_engagement_trends(days=7)
        assert trends["period_days"] == 7
        assert trends["total_events"] == 3

    def test_get_channel_performance(self):
        """Channel performance can be retrieved."""
        analytics = MarketingAnalytics()
        analytics.track_event("open", metadata={"channel": "email"})
        analytics.track_event("click", metadata={"channel": "email"})
        analytics.track_event("open", metadata={"channel": "social"})
        result = analytics.get_channel_performance()
        assert "email" in result
        assert "social" in result
        assert result["email"]["total"] == 2
        assert result["social"]["total"] == 1

    def test_get_overview(self):
        """Marketing overview can be generated."""
        analytics = MarketingAnalytics()
        analytics.track_event("open")
        analytics.track_event("click")
        analytics.track_event("conversion")
        overview = analytics.get_overview()
        assert overview["total_events"] == 3
        assert overview["total_opens"] == 1
        assert overview["total_clicks"] == 1
        assert overview["total_conversions"] == 1


class TestROICalculator:
    """Test ROI calculator."""

    def test_set_campaign_cost(self):
        """Campaign cost can be set."""
        calc = ROICalculator()
        calc.set_campaign_cost("c-1", 1000.0)
        report = calc.calculate_roi("c-1")
        assert report.total_cost == 1000.0

    def test_set_campaign_cost_negative(self):
        """Negative cost raises error."""
        calc = ROICalculator()
        with pytest.raises(ValueError, match="Cost cannot be negative"):
            calc.set_campaign_cost("c-1", -100.0)

    def test_set_campaign_revenue(self):
        """Campaign revenue can be set."""
        calc = ROICalculator()
        calc.set_campaign_revenue("c-1", 3000.0)
        report = calc.calculate_roi("c-1")
        assert report.total_revenue == 3000.0

    def test_set_campaign_revenue_negative(self):
        """Negative revenue raises error."""
        calc = ROICalculator()
        with pytest.raises(ValueError, match="Revenue cannot be negative"):
            calc.set_campaign_revenue("c-1", -500.0)

    def test_calculate_roi(self):
        """ROI can be calculated."""
        calc = ROICalculator()
        calc.set_campaign_cost("c-1", 1000.0)
        calc.set_campaign_revenue("c-1", 3000.0)
        calc.set_leads_generated("c-1", 100)
        calc.set_conversions("c-1", 10)
        report = calc.calculate_roi("c-1")
        assert report.roi == pytest.approx(200.0)
        assert report.roas == pytest.approx(3.0)
        assert report.cost_per_lead == pytest.approx(10.0)
        assert report.cost_per_acquisition == pytest.approx(100.0)

    def test_calculate_roi_zero_cost(self):
        """ROI with zero cost returns zero."""
        calc = ROICalculator()
        calc.set_campaign_revenue("c-1", 1000.0)
        report = calc.calculate_roi("c-1")
        assert report.roi == 0.0
        assert report.roas == 0.0

    def test_get_roi_report(self):
        """ROI report can be generated."""
        calc = ROICalculator()
        calc.set_campaign_name("c-1", "Test Campaign")
        calc.set_campaign_cost("c-1", 500.0)
        calc.set_campaign_revenue("c-1", 2000.0)
        calc.set_leads_generated("c-1", 50)
        calc.set_conversions("c-1", 5)
        report = calc.get_roi_report("c-1")
        assert report["campaign_name"] == "Test Campaign"
        assert report["total_cost"] == 500.0
        assert report["total_revenue"] == 2000.0
        assert report["roi"] == pytest.approx(300.0)

    def test_get_portfolio_roi(self):
        """Portfolio ROI can be calculated."""
        calc = ROICalculator()
        calc.set_campaign_cost("c-1", 1000.0)
        calc.set_campaign_revenue("c-1", 3000.0)
        calc.set_campaign_cost("c-2", 2000.0)
        calc.set_campaign_revenue("c-2", 4000.0)
        calc.set_leads_generated("c-1", 100)
        calc.set_leads_generated("c-2", 200)
        calc.set_conversions("c-1", 10)
        calc.set_conversions("c-2", 20)
        portfolio = calc.get_portfolio_roi()
        assert portfolio["total_cost"] == 3000.0
        assert portfolio["total_revenue"] == 7000.0
        assert portfolio["roi"] == pytest.approx(133.33, rel=0.01)
        assert portfolio["campaign_count"] == 2

    def test_compare_campaigns(self):
        """Campaigns can be compared."""
        calc = ROICalculator()
        calc.set_campaign_name("c-1", "Campaign A")
        calc.set_campaign_name("c-2", "Campaign B")
        calc.set_campaign_cost("c-1", 1000.0)
        calc.set_campaign_revenue("c-1", 3000.0)
        calc.set_campaign_cost("c-2", 1000.0)
        calc.set_campaign_revenue("c-2", 2000.0)
        result = calc.compare_campaigns(["c-1", "c-2"])
        assert len(result["comparisons"]) == 2
        assert result["best_campaign"]["campaign_id"] == "c-1"
        assert result["worst_campaign"]["campaign_id"] == "c-2"

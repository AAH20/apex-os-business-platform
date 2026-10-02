"""Tests for CRM module."""
import pytest
from apex_os_bp.crm.models import Contact, Deal, DealStage, Pipeline
from apex_os_bp.crm.engine import CRMEngine


class TestContact:
    """Test contact data structure."""

    def test_contact_creation(self):
        """Contact can be created."""
        contact = Contact(id="c-1", name="John Doe", email="john@example.com")
        assert contact.id == "c-1"
        assert contact.name == "John Doe"
        assert contact.email == "john@example.com"

    def test_contact_with_company(self):
        """Contact supports company."""
        contact = Contact(id="c-1", name="John", email="john@example.com", company="Acme")
        assert contact.company == "Acme"


class TestDeal:
    """Test deal data structure."""

    def test_deal_creation(self):
        """Deal can be created."""
        deal = Deal(id="d-1", title="Big Deal", value=10000.0, stage=DealStage.LEAD)
        assert deal.id == "d-1"
        assert deal.title == "Big Deal"
        assert deal.value == 10000.0
        assert deal.stage == DealStage.LEAD

    def test_deal_stage_transition(self):
        """Deal can transition stages."""
        deal = Deal(id="d-1", title="Deal", value=1000.0, stage=DealStage.LEAD)
        deal.advance_stage()
        assert deal.stage == DealStage.QUALIFIED


class TestPipeline:
    """Test pipeline functionality."""

    def test_pipeline_creation(self):
        """Pipeline can be created."""
        pipeline = Pipeline(name="Sales Pipeline")
        assert pipeline.name == "Sales Pipeline"
        assert len(pipeline.deals) == 0

    def test_add_deal(self):
        """Deal can be added to pipeline."""
        pipeline = Pipeline(name="Sales Pipeline")
        deal = Deal(id="d-1", title="Deal", value=1000.0, stage=DealStage.LEAD)
        pipeline.add_deal(deal)
        assert len(pipeline.deals) == 1

    def test_pipeline_value(self):
        """Pipeline calculates total value."""
        pipeline = Pipeline(name="Sales Pipeline")
        pipeline.add_deal(Deal(id="d-1", title="Deal 1", value=1000.0, stage=DealStage.LEAD))
        pipeline.add_deal(Deal(id="d-2", title="Deal 2", value=2000.0, stage=DealStage.QUALIFIED))
        assert pipeline.total_value() == 3000.0


class TestCRMEngine:
    """Test CRM engine."""

    def test_create_contact(self):
        """Contact can be created."""
        engine = CRMEngine()
        contact = engine.create_contact(name="John", email="john@example.com")
        assert contact.name == "John"
        assert contact.email == "john@example.com"

    def test_create_deal(self):
        """Deal can be created."""
        engine = CRMEngine()
        deal = engine.create_deal(title="Deal", value=1000.0)
        assert deal.title == "Deal"
        assert deal.value == 1000.0

    def test_lead_to_cash_workflow(self):
        """Lead-to-cash workflow can be executed."""
        engine = CRMEngine()
        contact = engine.create_contact(name="John", email="john@example.com")
        deal = engine.create_deal(title="Deal", value=1000.0)
        engine.link_deal_to_contact(deal.id, contact.id)
        assert deal.contact_id == contact.id

    def test_pipeline_report(self):
        """Pipeline report can be generated."""
        engine = CRMEngine()
        engine.create_deal(title="Deal 1", value=1000.0)
        engine.create_deal(title="Deal 2", value=2000.0)
        report = engine.pipeline_report()
        assert report["total_deals"] == 2
        assert report["total_value"] == 3000.0

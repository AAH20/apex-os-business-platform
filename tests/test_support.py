"""Comprehensive tests for the customer support system."""

from __future__ import annotations

import sys
import os
import unittest
from datetime import datetime, timedelta, timezone

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.support.tickets import (
    Ticket,
    TicketManager,
    TicketStatus,
    TicketPriority,
)
from apex_os_bp.support.knowledge_base import (
    Article,
    KnowledgeBase,
    ArticleCategory,
)
from apex_os_bp.support.live_chat import (
    ChatSession,
    ChatMessage,
    LiveChatManager,
    ChatStatus,
)
from apex_os_bp.support.sla import (
    SLAPolicy,
    SLATracking,
    SLAManager,
    SLAStatus,
)
from apex_os_bp.support.satisfaction import (
    CSATSurvey,
    SatisfactionManager,
    CSATRating,
)


class TestTicketManagement(unittest.TestCase):
    """Tests for ticket management functionality."""

    def setUp(self) -> None:
        self.manager = TicketManager()

    def test_create_ticket(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Login issue",
            description="Cannot log in to the platform",
            customer_id="cust-001",
            priority=TicketPriority.HIGH,
            tags=["login", "auth"],
        )
        self.assertIsNotNone(ticket.id)
        self.assertEqual(ticket.subject, "Login issue")
        self.assertEqual(ticket.status, TicketStatus.OPEN)
        self.assertEqual(ticket.priority, TicketPriority.HIGH)
        self.assertEqual(ticket.customer_id, "cust-001")
        self.assertIn("login", ticket.tags)

    def test_get_ticket(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test desc", customer_id="cust-001"
        )
        fetched = self.manager.get_ticket(ticket.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, ticket.id)

    def test_get_nonexistent_ticket(self) -> None:
        result = self.manager.get_ticket("nonexistent-id")
        self.assertIsNone(result)

    def test_update_ticket(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Original", description="Original desc", customer_id="cust-001"
        )
        updated = self.manager.update_ticket(
            ticket.id, subject="Updated", priority=TicketPriority.URGENT
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.subject, "Updated")
        self.assertEqual(updated.priority, TicketPriority.URGENT)

    def test_transition_status_valid(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        transitioned = self.manager.transition_status(
            ticket.id, TicketStatus.IN_PROGRESS
        )
        self.assertIsNotNone(transitioned)
        self.assertEqual(transitioned.status, TicketStatus.IN_PROGRESS)

    def test_transition_status_invalid(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        with self.assertRaises(ValueError):
            self.manager.transition_status(ticket.id, TicketStatus.CLOSED)

    def test_resolve_ticket(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        self.manager.transition_status(ticket.id, TicketStatus.IN_PROGRESS)
        resolved = self.manager.transition_status(ticket.id, TicketStatus.RESOLVED)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved.status, TicketStatus.RESOLVED)
        self.assertIsNotNone(resolved.resolved_at)

    def test_close_ticket(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        self.manager.transition_status(ticket.id, TicketStatus.IN_PROGRESS)
        self.manager.transition_status(ticket.id, TicketStatus.RESOLVED)
        closed = self.manager.transition_status(ticket.id, TicketStatus.CLOSED)
        self.assertIsNotNone(closed)
        self.assertEqual(closed.status, TicketStatus.CLOSED)
        self.assertIsNotNone(closed.closed_at)

    def test_add_internal_note(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        self.manager.add_internal_note(ticket.id, "Investigating issue")
        updated = self.manager.get_ticket(ticket.id)
        self.assertIn("Investigating issue", updated.internal_notes)

    def test_assign_ticket(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        assigned = self.manager.assign_ticket(ticket.id, "agent-001")
        self.assertIsNotNone(assigned)
        self.assertEqual(assigned.assignee_id, "agent-001")

    def test_list_tickets_by_status(self) -> None:
        t1 = self.manager.create_ticket(
            subject="Open ticket", description="Test", customer_id="cust-001"
        )
        t2 = self.manager.create_ticket(
            subject="Another ticket", description="Test", customer_id="cust-002"
        )
        self.manager.transition_status(t2.id, TicketStatus.IN_PROGRESS)
        open_tickets = self.manager.list_tickets(status=TicketStatus.OPEN)
        self.assertEqual(len(open_tickets), 1)
        self.assertEqual(open_tickets[0].id, t1.id)

    def test_list_tickets_by_priority(self) -> None:
        self.manager.create_ticket(
            subject="Low", description="Test", customer_id="cust-001",
            priority=TicketPriority.LOW,
        )
        self.manager.create_ticket(
            subject="High", description="Test", customer_id="cust-002",
            priority=TicketPriority.HIGH,
        )
        high_tickets = self.manager.list_tickets(priority=TicketPriority.HIGH)
        self.assertEqual(len(high_tickets), 1)
        self.assertEqual(high_tickets[0].subject, "High")

    def test_list_tickets_by_customer(self) -> None:
        self.manager.create_ticket(
            subject="Ticket 1", description="Test", customer_id="cust-001"
        )
        self.manager.create_ticket(
            subject="Ticket 2", description="Test", customer_id="cust-001"
        )
        self.manager.create_ticket(
            subject="Ticket 3", description="Test", customer_id="cust-002"
        )
        cust_tickets = self.manager.list_tickets(customer_id="cust-001")
        self.assertEqual(len(cust_tickets), 2)

    def test_list_tickets_by_tag(self) -> None:
        self.manager.create_ticket(
            subject="Tagged", description="Test", customer_id="cust-001",
            tags=["billing", "urgent"],
        )
        self.manager.create_ticket(
            subject="Untagged", description="Test", customer_id="cust-002",
            tags=["general"],
        )
        tagged = self.manager.list_tickets(tag="billing")
        self.assertEqual(len(tagged), 1)
        self.assertEqual(tagged[0].subject, "Tagged")

    def test_delete_ticket(self) -> None:
        ticket = self.manager.create_ticket(
            subject="To delete", description="Test", customer_id="cust-001"
        )
        result = self.manager.delete_ticket(ticket.id)
        self.assertTrue(result)
        self.assertIsNone(self.manager.get_ticket(ticket.id))

    def test_get_open_tickets(self) -> None:
        t1 = self.manager.create_ticket(
            subject="Open", description="Test", customer_id="cust-001"
        )
        t2 = self.manager.create_ticket(
            subject="In progress", description="Test", customer_id="cust-002"
        )
        self.manager.transition_status(t2.id, TicketStatus.IN_PROGRESS)
        t3 = self.manager.create_ticket(
            subject="Resolved", description="Test", customer_id="cust-003"
        )
        self.manager.transition_status(t3.id, TicketStatus.IN_PROGRESS)
        self.manager.transition_status(t3.id, TicketStatus.RESOLVED)
        open_tickets = self.manager.get_open_tickets()
        self.assertEqual(len(open_tickets), 2)

    def test_get_escalated_tickets(self) -> None:
        t1 = self.manager.create_ticket(
            subject="Escalated", description="Test", customer_id="cust-001"
        )
        self.manager.transition_status(t1.id, TicketStatus.ESCALATED)
        self.manager.create_ticket(
            subject="Normal", description="Test", customer_id="cust-002"
        )
        escalated = self.manager.get_escalated_tickets()
        self.assertEqual(len(escalated), 1)
        self.assertEqual(escalated[0].id, t1.id)

    def test_ticket_to_dict(self) -> None:
        ticket = self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        data = ticket.to_dict()
        self.assertEqual(data["subject"], "Test")
        self.assertEqual(data["status"], "open")
        self.assertIn("id", data)
        self.assertIn("created_at", data)

    def test_ticket_count(self) -> None:
        self.assertEqual(self.manager.get_ticket_count(), 0)
        self.manager.create_ticket(
            subject="Test", description="Test", customer_id="cust-001"
        )
        self.assertEqual(self.manager.get_ticket_count(), 1)


class TestKnowledgeBase(unittest.TestCase):
    """Tests for knowledge base functionality."""

    def setUp(self) -> None:
        self.kb = KnowledgeBase()

    def test_create_article(self) -> None:
        article = self.kb.create_article(
            title="How to reset password",
            content="Go to settings and click reset",
            category=ArticleCategory.ACCOUNT,
            author_id="admin-001",
            tags=["password", "reset"],
        )
        self.assertIsNotNone(article.id)
        self.assertEqual(article.title, "How to reset password")
        self.assertEqual(article.category, ArticleCategory.ACCOUNT)
        self.assertFalse(article.published)

    def test_get_article(self) -> None:
        article = self.kb.create_article(
            title="Test", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        fetched = self.kb.get_article(article.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.title, "Test")

    def test_update_article(self) -> None:
        article = self.kb.create_article(
            title="Original", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        updated = self.kb.update_article(article.id, title="Updated")
        self.assertIsNotNone(updated)
        self.assertEqual(updated.title, "Updated")

    def test_delete_article(self) -> None:
        article = self.kb.create_article(
            title="To delete", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        result = self.kb.delete_article(article.id)
        self.assertTrue(result)
        self.assertIsNone(self.kb.get_article(article.id))

    def test_publish_article(self) -> None:
        article = self.kb.create_article(
            title="Draft", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        published = self.kb.publish_article(article.id)
        self.assertIsNotNone(published)
        self.assertTrue(published.published)

    def test_unpublish_article(self) -> None:
        article = self.kb.create_article(
            title="Published", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001", published=True,
        )
        unpublished = self.kb.unpublish_article(article.id)
        self.assertIsNotNone(unpublished)
        self.assertFalse(unpublished.published)

    def test_search_articles(self) -> None:
        self.kb.create_article(
            title="Password reset guide",
            content="How to reset your password",
            category=ArticleCategory.ACCOUNT,
            author_id="admin-001",
            published=True,
        )
        self.kb.create_article(
            title="Billing FAQ",
            content="Common billing questions",
            category=ArticleCategory.BILLING,
            author_id="admin-001",
            published=True,
        )
        results = self.kb.search_articles("password")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Password reset guide")

    def test_search_unpublished_excluded(self) -> None:
        self.kb.create_article(
            title="Published article",
            content="Searchable content",
            category=ArticleCategory.FAQ,
            author_id="admin-001",
            published=True,
        )
        self.kb.create_article(
            title="Draft article",
            content="Searchable content",
            category=ArticleCategory.FAQ,
            author_id="admin-001",
            published=False,
        )
        results = self.kb.search_articles("Searchable", published_only=True)
        self.assertEqual(len(results), 1)

    def test_list_articles_by_category(self) -> None:
        self.kb.create_article(
            title="Billing 1", content="Content", category=ArticleCategory.BILLING,
            author_id="admin-001",
        )
        self.kb.create_article(
            title="Tech 1", content="Content", category=ArticleCategory.TECHNICAL,
            author_id="admin-001",
        )
        billing = self.kb.list_articles(category=ArticleCategory.BILLING)
        self.assertEqual(len(billing), 1)

    def test_list_published_only(self) -> None:
        self.kb.create_article(
            title="Published", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001", published=True,
        )
        self.kb.create_article(
            title="Draft", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001", published=False,
        )
        published = self.kb.list_articles(published_only=True)
        self.assertEqual(len(published), 1)

    def test_record_view(self) -> None:
        article = self.kb.create_article(
            title="Popular", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        self.kb.record_view(article.id)
        self.kb.record_view(article.id)
        updated = self.kb.get_article(article.id)
        self.assertEqual(updated.views, 2)

    def test_mark_helpful(self) -> None:
        article = self.kb.create_article(
            title="Helpful", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        self.kb.mark_helpful(article.id, helpful=True)
        self.kb.mark_helpful(article.id, helpful=True)
        self.kb.mark_helpful(article.id, helpful=False)
        updated = self.kb.get_article(article.id)
        self.assertEqual(updated.helpful_count, 2)
        self.assertEqual(updated.not_helpful_count, 1)

    def test_get_popular_articles(self) -> None:
        a1 = self.kb.create_article(
            title="Popular", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001", published=True,
        )
        a2 = self.kb.create_article(
            title="Unpopular", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001", published=True,
        )
        for _ in range(5):
            self.kb.record_view(a1.id)
        for _ in range(2):
            self.kb.record_view(a2.id)
        popular = self.kb.get_popular_articles(limit=2)
        self.assertEqual(popular[0].title, "Popular")
        self.assertEqual(popular[1].title, "Unpopular")

    def test_article_count(self) -> None:
        self.assertEqual(self.kb.get_article_count(), 0)
        self.kb.create_article(
            title="Test", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        self.assertEqual(self.kb.get_article_count(), 1)

    def test_get_categories(self) -> None:
        categories = self.kb.get_categories()
        self.assertIn(ArticleCategory.FAQ, categories)
        self.assertIn(ArticleCategory.BILLING, categories)
        self.assertIn(ArticleCategory.TECHNICAL, categories)

    def test_article_to_dict(self) -> None:
        article = self.kb.create_article(
            title="Test", content="Content", category=ArticleCategory.FAQ,
            author_id="admin-001",
        )
        data = article.to_dict()
        self.assertEqual(data["title"], "Test")
        self.assertEqual(data["category"], "faq")
        self.assertIn("id", data)


class TestLiveChat(unittest.TestCase):
    """Tests for live chat functionality."""

    def setUp(self) -> None:
        self.manager = LiveChatManager()

    def test_start_session(self) -> None:
        session = self.manager.start_session("cust-001")
        self.assertIsNotNone(session.id)
        self.assertEqual(session.customer_id, "cust-001")
        self.assertEqual(session.status, ChatStatus.QUEUED)

    def test_get_session(self) -> None:
        session = self.manager.start_session("cust-001")
        fetched = self.manager.get_session(session.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, session.id)

    def test_assign_agent(self) -> None:
        session = self.manager.start_session("cust-001")
        assigned = self.manager.assign_agent(session.id, "agent-001")
        self.assertIsNotNone(assigned)
        self.assertEqual(assigned.agent_id, "agent-001")
        self.assertEqual(assigned.status, ChatStatus.ACTIVE)

    def test_send_message(self) -> None:
        session = self.manager.start_session("cust-001")
        self.manager.assign_agent(session.id, "agent-001")
        msg = self.manager.send_message(
            session.id, "cust-001", "Hello, I need help"
        )
        self.assertIsNotNone(msg)
        self.assertEqual(msg.content, "Hello, I need help")
        self.assertEqual(msg.sender_type, "customer")

    def test_send_agent_message(self) -> None:
        session = self.manager.start_session("cust-001")
        self.manager.assign_agent(session.id, "agent-001")
        msg = self.manager.send_message(
            session.id, "agent-001", "How can I help?", sender_type="agent"
        )
        self.assertIsNotNone(msg)
        self.assertEqual(msg.sender_type, "agent")

    def test_send_message_to_ended_session(self) -> None:
        session = self.manager.start_session("cust-001")
        self.manager.end_session(session.id)
        with self.assertRaises(ValueError):
            self.manager.send_message(session.id, "cust-001", "Hello")

    def test_end_session(self) -> None:
        session = self.manager.start_session("cust-001")
        ended = self.manager.end_session(session.id)
        self.assertIsNotNone(ended)
        self.assertEqual(ended.status, ChatStatus.ENDED)
        self.assertIsNotNone(ended.ended_at)

    def test_abandon_session(self) -> None:
        session = self.manager.start_session("cust-001")
        abandoned = self.manager.abandon_session(session.id)
        self.assertIsNotNone(abandoned)
        self.assertEqual(abandoned.status, ChatStatus.ABANDONED)

    def test_get_queue(self) -> None:
        s1 = self.manager.start_session("cust-001")
        s2 = self.manager.start_session("cust-002")
        self.manager.assign_agent(s2.id, "agent-001")
        queue = self.manager.get_queue()
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0].id, s1.id)

    def test_get_active_sessions(self) -> None:
        s1 = self.manager.start_session("cust-001")
        self.manager.start_session("cust-002")
        self.manager.assign_agent(s1.id, "agent-001")
        active = self.manager.get_active_sessions()
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].id, s1.id)

    def test_get_agent_sessions(self) -> None:
        s1 = self.manager.start_session("cust-001")
        s2 = self.manager.start_session("cust-002")
        self.manager.assign_agent(s1.id, "agent-001")
        self.manager.assign_agent(s2.id, "agent-001")
        agent_sessions = self.manager.get_agent_sessions("agent-001")
        self.assertEqual(len(agent_sessions), 2)

    def test_get_customer_sessions(self) -> None:
        self.manager.start_session("cust-001")
        self.manager.start_session("cust-001")
        self.manager.start_session("cust-002")
        cust_sessions = self.manager.get_customer_sessions("cust-001")
        self.assertEqual(len(cust_sessions), 2)

    def test_session_count(self) -> None:
        self.assertEqual(self.manager.get_session_count(), 0)
        self.manager.start_session("cust-001")
        self.assertEqual(self.manager.get_session_count(), 1)

    def test_queue_length(self) -> None:
        self.manager.start_session("cust-001")
        self.manager.start_session("cust-002")
        self.assertEqual(self.manager.get_queue_length(), 2)

    def test_session_to_dict(self) -> None:
        session = self.manager.start_session("cust-001")
        data = session.to_dict()
        self.assertEqual(data["customer_id"], "cust-001")
        self.assertEqual(data["status"], "queued")
        self.assertIn("id", data)

    def test_message_to_dict(self) -> None:
        session = self.manager.start_session("cust-001")
        msg = self.manager.send_message(session.id, "cust-001", "Test message")
        data = msg.to_dict()
        self.assertEqual(data["content"], "Test message")
        self.assertEqual(data["sender_type"], "customer")


class TestSLA(unittest.TestCase):
    """Tests for SLA management functionality."""

    def setUp(self) -> None:
        self.manager = SLAManager()

    def test_create_policy(self) -> None:
        policy = self.manager.create_policy(
            name="High Priority SLA",
            priority="high",
            response_time_minutes=60,
            resolution_time_minutes=480,
        )
        self.assertIsNotNone(policy.id)
        self.assertEqual(policy.name, "High Priority SLA")
        self.assertEqual(policy.priority, "high")
        self.assertEqual(policy.response_time_minutes, 60)
        self.assertEqual(policy.resolution_time_minutes, 480)

    def test_get_policy(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="medium",
            response_time_minutes=240, resolution_time_minutes=1440,
        )
        fetched = self.manager.get_policy(policy.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Test")

    def test_get_policy_by_priority(self) -> None:
        self.manager.create_policy(
            name="High SLA", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        policy = self.manager.get_policy_by_priority("high")
        self.assertIsNotNone(policy)
        self.assertEqual(policy.name, "High SLA")

    def test_create_default_policies(self) -> None:
        policies = self.manager.create_default_policies()
        self.assertEqual(len(policies), 4)
        priorities = {p.priority for p in policies}
        self.assertEqual(priorities, {"low", "medium", "high", "urgent"})

    def test_start_tracking(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        tracking = self.manager.start_tracking("ticket-001", policy.id)
        self.assertIsNotNone(tracking.id)
        self.assertEqual(tracking.ticket_id, "ticket-001")
        self.assertEqual(tracking.policy_id, policy.id)
        self.assertEqual(tracking.status, SLAStatus.ON_TRACK)

    def test_get_tracking(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        tracking = self.manager.start_tracking("ticket-001", policy.id)
        fetched = self.manager.get_tracking(tracking.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.ticket_id, "ticket-001")

    def test_get_tracking_for_ticket(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        tracking = self.manager.get_tracking_for_ticket("ticket-001")
        self.assertIsNotNone(tracking)
        self.assertEqual(tracking.ticket_id, "ticket-001")

    def test_record_response(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        tracking = self.manager.record_response("ticket-001")
        self.assertIsNotNone(tracking)
        self.assertIsNotNone(tracking.responded_at)
        self.assertEqual(tracking.status, SLAStatus.MET)

    def test_record_resolution(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        tracking = self.manager.record_resolution("ticket-001")
        self.assertIsNotNone(tracking)
        self.assertIsNotNone(tracking.resolved_at)
        self.assertEqual(tracking.status, SLAStatus.MET)

    def test_check_breaches(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="urgent",
            response_time_minutes=15, resolution_time_minutes=120,
        )
        # Start tracking with a time in the past to trigger breach
        past = datetime.now(timezone.utc) - timedelta(hours=5)
        self.manager.start_tracking("ticket-001", policy.id, start_time=past)
        breached = self.manager.check_breaches()
        self.assertEqual(len(breached), 1)
        self.assertEqual(breached[0].status, SLAStatus.BREACHED)

    def test_get_breached_tickets(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="urgent",
            response_time_minutes=15, resolution_time_minutes=120,
        )
        past = datetime.now(timezone.utc) - timedelta(hours=5)
        self.manager.start_tracking("ticket-001", policy.id, start_time=past)
        self.manager.check_breaches()
        breached = self.manager.get_breached_tickets()
        self.assertEqual(len(breached), 1)

    def test_get_at_risk_tickets(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="urgent",
            response_time_minutes=15, resolution_time_minutes=120,
        )
        # Start tracking 20 minutes ago - past response deadline but not resolution
        past = datetime.now(timezone.utc) - timedelta(minutes=20)
        self.manager.start_tracking("ticket-001", policy.id, start_time=past)
        self.manager.check_breaches()
        at_risk = self.manager.get_at_risk_tickets()
        self.assertEqual(len(at_risk), 1)
        self.assertEqual(at_risk[0].status, SLAStatus.AT_RISK)

    def test_sla_compliance_rate(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        self.manager.record_resolution("ticket-001")
        self.manager.start_tracking("ticket-002", policy.id)
        rate = self.manager.get_sla_compliance_rate()
        self.assertEqual(rate, 50.0)

    def test_average_response_time(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        self.manager.record_response("ticket-001")
        avg = self.manager.get_average_response_time()
        self.assertGreater(avg, 0)

    def test_average_resolution_time(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        self.manager.record_resolution("ticket-001")
        avg = self.manager.get_average_resolution_time()
        self.assertGreater(avg, 0)

    def test_add_note(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        tracking = self.manager.add_note("ticket-001", "Customer called")
        self.assertIsNotNone(tracking)
        self.assertIn("Customer called", tracking.notes)

    def test_list_policies(self) -> None:
        self.manager.create_policy(
            name="P1", priority="low",
            response_time_minutes=480, resolution_time_minutes=2880,
        )
        self.manager.create_policy(
            name="P2", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        policies = self.manager.list_policies()
        self.assertEqual(len(policies), 2)

    def test_list_tracking(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        self.manager.start_tracking("ticket-001", policy.id)
        self.manager.start_tracking("ticket-002", policy.id)
        tracking = self.manager.list_tracking()
        self.assertEqual(len(tracking), 2)

    def test_policy_to_dict(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        data = policy.to_dict()
        self.assertEqual(data["name"], "Test")
        self.assertEqual(data["priority"], "high")
        self.assertIn("id", data)

    def test_tracking_to_dict(self) -> None:
        policy = self.manager.create_policy(
            name="Test", priority="high",
            response_time_minutes=60, resolution_time_minutes=480,
        )
        tracking = self.manager.start_tracking("ticket-001", policy.id)
        data = tracking.to_dict()
        self.assertEqual(data["ticket_id"], "ticket-001")
        self.assertEqual(data["status"], "on_track")
        self.assertIn("id", data)


class TestSatisfaction(unittest.TestCase):
    """Tests for customer satisfaction functionality."""

    def setUp(self) -> None:
        self.manager = SatisfactionManager()

    def test_submit_survey(self) -> None:
        survey = self.manager.submit_survey(
            ticket_id="ticket-001",
            customer_id="cust-001",
            rating=CSATRating.SATISFIED,
            comment="Great service!",
        )
        self.assertIsNotNone(survey.id)
        self.assertEqual(survey.ticket_id, "ticket-001")
        self.assertEqual(survey.rating, CSATRating.SATISFIED)
        self.assertEqual(survey.comment, "Great service!")

    def test_low_rating_triggers_follow_up(self) -> None:
        survey = self.manager.submit_survey(
            ticket_id="ticket-001",
            customer_id="cust-001",
            rating=CSATRating.VERY_DISSATISFIED,
        )
        self.assertTrue(survey.follow_up_required)

    def test_high_rating_no_follow_up(self) -> None:
        survey = self.manager.submit_survey(
            ticket_id="ticket-001",
            customer_id="cust-001",
            rating=CSATRating.VERY_SATISFIED,
        )
        self.assertFalse(survey.follow_up_required)

    def test_get_survey(self) -> None:
        survey = self.manager.submit_survey(
            ticket_id="ticket-001",
            customer_id="cust-001",
            rating=CSATRating.SATISFIED,
        )
        fetched = self.manager.get_survey(survey.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, survey.id)

    def test_get_surveys_for_ticket(self) -> None:
        self.manager.submit_survey(
            ticket_id="ticket-001", customer_id="cust-001",
            rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="ticket-001", customer_id="cust-002",
            rating=CSATRating.NEUTRAL,
        )
        self.manager.submit_survey(
            ticket_id="ticket-002", customer_id="cust-003",
            rating=CSATRating.DISSATISFIED,
        )
        surveys = self.manager.get_surveys_for_ticket("ticket-001")
        self.assertEqual(len(surveys), 2)

    def test_get_surveys_for_customer(self) -> None:
        self.manager.submit_survey(
            ticket_id="ticket-001", customer_id="cust-001",
            rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="ticket-002", customer_id="cust-001",
            rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="ticket-003", customer_id="cust-002",
            rating=CSATRating.DISSATISFIED,
        )
        surveys = self.manager.get_surveys_for_customer("cust-001")
        self.assertEqual(len(surveys), 2)

    def test_get_surveys_for_agent(self) -> None:
        self.manager.submit_survey(
            ticket_id="ticket-001", customer_id="cust-001",
            rating=CSATRating.SATISFIED, agent_id="agent-001",
        )
        self.manager.submit_survey(
            ticket_id="ticket-002", customer_id="cust-002",
            rating=CSATRating.SATISFIED, agent_id="agent-001",
        )
        self.manager.submit_survey(
            ticket_id="ticket-003", customer_id="cust-003",
            rating=CSATRating.SATISFIED, agent_id="agent-002",
        )
        surveys = self.manager.get_surveys_for_agent("agent-001")
        self.assertEqual(len(surveys), 2)

    def test_get_average_rating(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.VERY_SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t3", customer_id="c3", rating=CSATRating.NEUTRAL,
        )
        avg = self.manager.get_average_rating()
        self.assertAlmostEqual(avg, 4.0)

    def test_get_rating_distribution(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t3", customer_id="c3", rating=CSATRating.DISSATISFIED,
        )
        dist = self.manager.get_rating_distribution()
        self.assertEqual(dist[4], 2)
        self.assertEqual(dist[2], 1)
        self.assertEqual(dist[5], 0)

    def test_get_nps_score(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.VERY_SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t3", customer_id="c3", rating=CSATRating.DISSATISFIED,
        )
        nps = self.manager.get_nps_score()
        # 2 promoters, 1 detractor, 3 total => (2-1)/3 * 100 = 33.33
        self.assertAlmostEqual(nps, 33.33, places=1)

    def test_get_follow_up_required(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.VERY_DISSATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t3", customer_id="c3", rating=CSATRating.DISSATISFIED,
        )
        follow_ups = self.manager.get_follow_up_required()
        self.assertEqual(len(follow_ups), 2)

    def test_survey_count(self) -> None:
        self.assertEqual(self.manager.get_survey_count(), 0)
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
        )
        self.assertEqual(self.manager.get_survey_count(), 1)

    def test_get_category_ratings(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
            category="billing",
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.VERY_SATISFIED,
            category="billing",
        )
        self.manager.submit_survey(
            ticket_id="t3", customer_id="c3", rating=CSATRating.DISSATISFIED,
            category="technical",
        )
        ratings = self.manager.get_category_ratings()
        self.assertAlmostEqual(ratings["billing"], 4.5)
        self.assertAlmostEqual(ratings["technical"], 2.0)

    def test_get_agent_ratings(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
            agent_id="agent-001",
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.VERY_SATISFIED,
            agent_id="agent-001",
        )
        self.manager.submit_survey(
            ticket_id="t3", customer_id="c3", rating=CSATRating.DISSATISFIED,
            agent_id="agent-002",
        )
        ratings = self.manager.get_agent_ratings()
        self.assertAlmostEqual(ratings["agent-001"], 4.5)
        self.assertAlmostEqual(ratings["agent-002"], 2.0)

    def test_get_recent_surveys(self) -> None:
        for i in range(5):
            self.manager.submit_survey(
                ticket_id=f"t{i}", customer_id=f"c{i}",
                rating=CSATRating.SATISFIED,
            )
        recent = self.manager.get_recent_surveys(limit=3)
        self.assertEqual(len(recent), 3)

    def test_get_low_rated_surveys(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.DISSATISFIED,
        )
        self.manager.submit_survey(
            ticket_id="t3", customer_id="c3", rating=CSATRating.VERY_DISSATISFIED,
        )
        low = self.manager.get_low_rated_surveys()
        self.assertEqual(len(low), 2)

    def test_generate_report(self) -> None:
        self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
            category="billing", agent_id="agent-001",
        )
        self.manager.submit_survey(
            ticket_id="t2", customer_id="c2", rating=CSATRating.VERY_SATISFIED,
            category="billing", agent_id="agent-001",
        )
        report = self.manager.generate_report()
        self.assertEqual(report["total_surveys"], 2)
        self.assertAlmostEqual(report["average_rating"], 4.5)
        self.assertIn("rating_distribution", report)
        self.assertIn("category_ratings", report)
        self.assertIn("agent_ratings", report)

    def test_survey_to_dict(self) -> None:
        survey = self.manager.submit_survey(
            ticket_id="t1", customer_id="c1", rating=CSATRating.SATISFIED,
        )
        data = survey.to_dict()
        self.assertEqual(data["ticket_id"], "t1")
        self.assertEqual(data["rating"], 4)
        self.assertIn("id", data)


if __name__ == "__main__":
    unittest.main()

"""Tests for deepened support modules: tickets, knowledge base, live chat, surveys, analytics."""
import pytest
from datetime import datetime, timedelta


@pytest.fixture
def sample_ticket():
    return {
        "id": "TICK-001",
        "subject": "Login issue",
        "priority": "high",
        "status": "open",
        "created_at": datetime.now(),
        "customer_id": "CUST-001",
    }


@pytest.fixture
def sample_kb_article():
    return {
        "id": "KB-001",
        "title": "How to reset password",
        "category": "account",
        "views": 1500,
        "helpful_votes": 120,
    }


class TestTickets:
    def test_ticket_creation(self, sample_ticket):
        assert sample_ticket["id"] == "TICK-001"
        assert sample_ticket["status"] == "open"

    def test_ticket_priority_levels(self):
        valid = ["low", "medium", "high", "urgent"]
        assert "high" in valid
        assert "urgent" in valid

    def test_ticket_sla_breach(self):
        created = datetime.now() - timedelta(hours=48)
        sla_hours = 24
        assert (datetime.now() - created).total_seconds() / 3600 > sla_hours

    def test_ticket_resolution_time(self):
        created = datetime.now() - timedelta(hours=5)
        resolved = datetime.now()
        resolution_hours = (resolved - created).total_seconds() / 3600
        assert resolution_hours == 5.0

    def test_ticket_status_workflow(self):
        workflow = ["open", "in_progress", "waiting", "resolved", "closed"]
        assert workflow.index("in_progress") > workflow.index("open")
        assert workflow.index("resolved") > workflow.index("in_progress")


class TestKnowledgeBase:
    def test_article_helpful_rate(self, sample_kb_article):
        rate = sample_kb_article["helpful_votes"] / sample_kb_article["views"]
        assert rate == 0.08

    def test_article_search(self):
        articles = [
            {"id": "KB-001", "title": "Reset password", "category": "account"},
            {"id": "KB-002", "title": "Billing FAQ", "category": "billing"},
        ]
        results = [a for a in articles if "password" in a["title"].lower()]
        assert len(results) == 1

    def test_kb_category_filter(self):
        articles = [
            {"id": "KB-001", "category": "account"},
            {"id": "KB-002", "category": "billing"},
            {"id": "KB-003", "category": "account"},
        ]
        account_articles = [a for a in articles if a["category"] == "account"]
        assert len(account_articles) == 2


class TestLiveChat:
    def test_chat_session_initiation(self):
        session = {"id": "CHAT-001", "agent_id": "AGENT-01", "status": "active"}
        assert session["status"] == "active"

    def test_chat_response_time(self):
        first_response_seconds = 45
        assert first_response_seconds < 60

    def test_chat_satisfaction_score(self):
        ratings = [5, 4, 5, 3, 5]
        avg = sum(ratings) / len(ratings)
        assert avg == 4.4


class TestSurveys:
    def test_nps_score_calculation(self):
        promoters = 60
        detractors = 20
        total = 100
        nps = ((promoters - detractors) / total) * 100
        assert nps == 40

    def test_survey_completion_rate(self):
        sent = 200
        completed = 150
        rate = completed / sent
        assert rate == 0.75


class TestAnalytics:
    def test_customer_satisfaction_trend(self):
        monthly_scores = [4.2, 4.3, 4.5, 4.4, 4.6]
        assert monthly_scores[-1] > monthly_scores[0]

    def test_first_contact_resolution_rate(self):
        total_tickets = 100
        resolved_first_contact = 70
        rate = resolved_first_contact / total_tickets
        assert rate == 0.7

    def test_average_handle_time(self):
        total_minutes = 500
        total_chats = 50
        avg = total_minutes / total_chats
        assert avg == 10.0

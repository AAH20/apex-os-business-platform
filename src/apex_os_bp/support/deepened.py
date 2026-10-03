"""Deepened support module: tickets, KB, chat, surveys, analytics."""
from __future__ import annotations
import time, uuid, statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Priority(Enum):
    LOW = 1; MEDIUM = 2; HIGH = 3; URGENT = 4


class TicketStatus(Enum):
    OPEN = "open"; IN_PROGRESS = "in_progress"; RESOLVED = "resolved"; CLOSED = "closed"


@dataclass
class Ticket:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    subject: str = ""
    customer: str = ""
    priority: Priority = Priority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    sla_hours: float = 24.0
    assignee: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    @property
    def age_hours(self) -> float:
        return (time.time() - self.created_at) / 3600

    @property
    def sla_breached(self) -> bool:
        return self.status not in (TicketStatus.RESOLVED, TicketStatus.CLOSED) and self.age_hours > self.sla_hours

    @property
    def resolution_time(self) -> Optional[float]:
        if self.resolved_at:
            return (self.resolved_at - self.created_at) / 3600
        return None


class TicketManager:
    def __init__(self):
        self._tickets: dict[str, Ticket] = {}

    def create(self, subject: str, customer: str, priority: Priority = Priority.MEDIUM,
               sla_hours: float = 24.0, tags: list[str] | None = None) -> Ticket:
        t = Ticket(subject=subject, customer=customer, priority=priority,
                   sla_hours=sla_hours, tags=tags or [])
        self._tickets[t.id] = t
        return t

    def get(self, tid: str) -> Optional[Ticket]:
        return self._tickets.get(tid)

    def resolve(self, tid: str) -> bool:
        t = self._tickets.get(tid)
        if t and t.status != TicketStatus.RESOLVED:
            t.status = TicketStatus.RESOLVED
            t.resolved_at = time.time()
            return True
        return False

    def list_open(self) -> list[Ticket]:
        return [t for t in self._tickets.values() if t.status == TicketStatus.OPEN]

    def sla_breached(self) -> list[Ticket]:
        return [t for t in self._tickets.values() if t.sla_breached]

    def avg_resolution_time(self) -> Optional[float]:
        times = [t.resolution_time for t in self._tickets.values() if t.resolution_time is not None]
        return statistics.mean(times) if times else None


@dataclass
class KBArticle:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    body: str = ""
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    views: int = 0
    helpful: int = 0


class KnowledgeBase:
    def __init__(self):
        self._articles: dict[str, KBArticle] = {}

    def add(self, title: str, body: str, category: str = "general",
            tags: list[str] | None = None) -> KBArticle:
        a = KBArticle(title=title, body=body, category=category, tags=tags or [])
        self._articles[a.id] = a
        return a

    def search(self, query: str, limit: int = 5) -> list[KBArticle]:
        q = query.lower()
        scored = []
        for a in self._articles.values():
            score = 0
            if q in a.title.lower(): score += 3
            if q in a.body.lower(): score += 2
            if any(q in t.lower() for t in a.tags): score += 2
            if q in a.category.lower(): score += 1
            if score > 0:
                scored.append((score, a))
        scored.sort(key=lambda x: -x[0])
        return [a for _, a in scored[:limit]]

    def mark_helpful(self, aid: str) -> bool:
        a = self._articles.get(aid)
        if a:
            a.helpful += 1
            return True
        return False

    def record_view(self, aid: str) -> None:
        a = self._articles.get(aid)
        if a:
            a.views += 1


@dataclass
class ChatMessage:
    sender: str  # "customer", "agent", "bot"
    text: str
    ts: float = field(default_factory=time.time)


class ChatSession:
    def __init__(self, customer: str):
        self.customer = customer
        self.messages: list[ChatMessage] = []
        self.active = True
        self.bot_enabled = True

    def send(self, sender: str, text: str) -> ChatMessage:
        msg = ChatMessage(sender=sender, text=text)
        self.messages.append(msg)
        if sender == "customer" and self.bot_enabled:
            reply = self._bot_reply(text)
            if reply:
                self.messages.append(ChatMessage(sender="bot", text=reply))
        return msg

    def _bot_reply(self, text: str) -> Optional[str]:
        t = text.lower()
        if "refund" in t:
            return "I can help with refunds. Please provide your order number."
        if "password" in t:
            return "You can reset your password at /reset-password."
        if "hours" in t or "open" in t:
            return "Our support hours are Mon–Fri 9AM–6PM EST."
        if "human" in t or "agent" in t:
            return "Connecting you to a live agent…"
        return None

    def escalate(self) -> None:
        self.bot_enabled = False
        self.messages.append(ChatMessage(sender="system", text="Escalated to human agent"))


@dataclass
class Survey:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    ticket_id: str = ""
    customer: str = ""
    csat: int = 0  # 1–5
    nps: int = 0  # 0–10
    comment: str = ""
    submitted_at: float = field(default_factory=time.time)


class SurveyManager:
    def __init__(self):
        self._surveys: dict[str, Survey] = {}

    def submit(self, ticket_id: str, customer: str, csat: int, nps: int = 0,
               comment: str = "") -> Survey:
        s = Survey(ticket_id=ticket_id, customer=customer, csat=csat, nps=nps, comment=comment)
        self._surveys[s.id] = s
        return s

    def avg_csat(self) -> Optional[float]:
        vals = [s.csat for s in self._surveys.values() if s.csat > 0]
        return statistics.mean(vals) if vals else None

    def avg_nps(self) -> Optional[float]:
        vals = [s.nps for s in self._surveys.values() if s.nps > 0]
        return statistics.mean(vals) if vals else None

    def promoters_pct(self) -> float:
        vals = [s.nps for s in self._surveys.values() if s.nps > 0]
        if not vals:
            return 0.0
        return sum(1 for v in vals if v >= 9) / len(vals) * 100

    def detractors_pct(self) -> float:
        vals = [s.nps for s in self._surveys.values() if s.nps > 0]
        if not vals:
            return 0.0
        return sum(1 for v in vals if v <= 6) / len(vals) * 100


class SupportAnalytics:
    def __init__(self, tickets: TicketManager, surveys: SurveyManager):
        self.tickets = tickets
        self.surveys = surveys

    def summary(self) -> dict:
        total = len(self.tickets._tickets)
        resolved = sum(1 for t in self.tickets._tickets.values()
                      if t.status in (TicketStatus.RESOLVED, TicketStatus.CLOSED))
        open_count = len(self.tickets.list_open())
        breached = len(self.tickets.sla_breached())
        avg_res = self.tickets.avg_resolution_time()
        csat = self.surveys.avg_csat()
        nps = self.surveys.avg_nps()
        return {
            "total_tickets": total,
            "resolved": resolved,
            "open": open_count,
            "sla_breached": breached,
            "avg_resolution_hours": round(avg_res, 2) if avg_res else None,
            "avg_csat": round(csat, 2) if csat else None,
            "avg_nps": round(nps, 2) if nps else None,
            "promoters_pct": round(self.surveys.promoters_pct(), 1),
            "detractors_pct": round(self.surveys.detractors_pct(), 1),
        }

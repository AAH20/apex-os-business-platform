"""Customer Support System for APEX-OS Business Platform.

Provides ticket management, knowledge base, live chat, SLA tracking,
and customer satisfaction measurement.
"""

from .tickets import Ticket, TicketManager, TicketStatus, TicketPriority
from .knowledge_base import Article, KnowledgeBase, ArticleCategory
from .live_chat import ChatSession, ChatMessage, LiveChatManager, ChatStatus
from .sla import SLAPolicy, SLATracking, SLAManager, SLAStatus
from .satisfaction import CSATSurvey, SatisfactionManager, CSATRating

__all__ = [
    "Ticket",
    "TicketManager",
    "TicketStatus",
    "TicketPriority",
    "Article",
    "KnowledgeBase",
    "ArticleCategory",
    "ChatSession",
    "ChatMessage",
    "LiveChatManager",
    "ChatStatus",
    "SLAPolicy",
    "SLATracking",
    "SLAManager",
    "SLAStatus",
    "CSATSurvey",
    "SatisfactionManager",
    "CSATRating",
]

"""Knowledge management data models."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set


class DocumentType(Enum):
    """Document types."""
    ARTICLE = "article"
    GUIDE = "guide"
    FAQ = "faq"
    POLICY = "policy"
    PROCEDURE = "procedure"
    NOTE = "note"


class ExpertiseLevel(Enum):
    """Expertise levels."""
    NOVICE = "novice"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class KnowledgeItem:
    """Knowledge base item."""
    id: str
    title: str
    content: str
    category: str
    tags: List[str] = field(default_factory=list)
    author_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Document:
    """Document for search."""
    id: str
    title: str
    content: str
    doc_type: DocumentType
    author_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Expert:
    """Expert profile."""
    id: str
    name: str
    email: str
    skills: List[str] = field(default_factory=list)
    expertise_level: ExpertiseLevel = ExpertiseLevel.INTERMEDIATE
    department: str = ""
    available: bool = True
    metadata: Dict = field(default_factory=dict)


@dataclass
class KnowledgeNode:
    """Knowledge graph node."""
    id: str
    label: str
    node_type: str
    properties: Dict = field(default_factory=dict)


@dataclass
class KnowledgeEdge:
    """Knowledge graph edge."""
    id: str
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    properties: Dict = field(default_factory=dict)


@dataclass
class Recommendation:
    """Recommendation result."""
    item_id: str
    item_type: str
    score: float
    reason: str = ""

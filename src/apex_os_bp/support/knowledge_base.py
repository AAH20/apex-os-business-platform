"""Knowledge base module for customer self-service support."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class ArticleCategory(str, Enum):
    """Categories for knowledge base articles."""

    GETTING_STARTED = "getting_started"
    BILLING = "billing"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    INTEGRATIONS = "integrations"
    TROUBLESHOOTING = "troubleshooting"
    FAQ = "faq"


@dataclass
class Article:
    """Represents a knowledge base article."""

    title: str
    content: str
    category: ArticleCategory
    author_id: str
    tags: list[str] = field(default_factory=list)
    published: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    views: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0

    def to_dict(self) -> dict:
        """Serialize article to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category.value,
            "author_id": self.author_id,
            "tags": self.tags,
            "published": self.published,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "views": self.views,
            "helpful_count": self.helpful_count,
            "not_helpful_count": self.not_helpful_count,
        }


class KnowledgeBase:
    """Manages knowledge base articles and search."""

    def __init__(self) -> None:
        self._articles: dict[str, Article] = {}

    def create_article(
        self,
        title: str,
        content: str,
        category: ArticleCategory,
        author_id: str,
        tags: Optional[list[str]] = None,
        published: bool = False,
    ) -> Article:
        """Create a new knowledge base article."""
        article = Article(
            title=title,
            content=content,
            category=category,
            author_id=author_id,
            tags=tags or [],
            published=published,
        )
        self._articles[article.id] = article
        return article

    def get_article(self, article_id: str) -> Optional[Article]:
        """Retrieve an article by ID."""
        return self._articles.get(article_id)

    def update_article(
        self,
        article_id: str,
        *,
        title: Optional[str] = None,
        content: Optional[str] = None,
        category: Optional[ArticleCategory] = None,
        tags: Optional[list[str]] = None,
        published: Optional[bool] = None,
    ) -> Optional[Article]:
        """Update article fields."""
        article = self._articles.get(article_id)
        if article is None:
            return None
        if title is not None:
            article.title = title
        if content is not None:
            article.content = content
        if category is not None:
            article.category = category
        if tags is not None:
            article.tags = tags
        if published is not None:
            article.published = published
        article.updated_at = datetime.now(timezone.utc)
        return article

    def delete_article(self, article_id: str) -> bool:
        """Delete an article by ID."""
        if article_id in self._articles:
            del self._articles[article_id]
            return True
        return False

    def publish_article(self, article_id: str) -> Optional[Article]:
        """Publish an article to make it visible to customers."""
        return self.update_article(article_id, published=True)

    def unpublish_article(self, article_id: str) -> Optional[Article]:
        """Unpublish an article."""
        return self.update_article(article_id, published=False)

    def search_articles(
        self,
        query: str,
        *,
        category: Optional[ArticleCategory] = None,
        published_only: bool = True,
    ) -> list[Article]:
        """Search articles by keyword in title and content."""
        query_lower = query.lower()
        results = []
        for article in self._articles.values():
            if published_only and not article.published:
                continue
            if category is not None and article.category != category:
                continue
            if (
                query_lower in article.title.lower()
                or query_lower in article.content.lower()
                or any(query_lower in tag.lower() for tag in article.tags)
            ):
                results.append(article)
        return results

    def list_articles(
        self,
        *,
        category: Optional[ArticleCategory] = None,
        published_only: bool = False,
        author_id: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> list[Article]:
        """List articles with optional filters."""
        results = list(self._articles.values())
        if category is not None:
            results = [a for a in results if a.category == category]
        if published_only:
            results = [a for a in results if a.published]
        if author_id is not None:
            results = [a for a in results if a.author_id == author_id]
        if tag is not None:
            results = [a for a in results if tag in a.tags]
        return results

    def record_view(self, article_id: str) -> Optional[Article]:
        """Increment the view count for an article."""
        article = self._articles.get(article_id)
        if article is None:
            return None
        article.views += 1
        return article

    def mark_helpful(self, article_id: str, helpful: bool = True) -> Optional[Article]:
        """Record helpfulness feedback for an article."""
        article = self._articles.get(article_id)
        if article is None:
            return None
        if helpful:
            article.helpful_count += 1
        else:
            article.not_helpful_count += 1
        return article

    def get_popular_articles(self, limit: int = 10) -> list[Article]:
        """Return most viewed published articles."""
        published = [a for a in self._articles.values() if a.published]
        return sorted(published, key=lambda a: a.views, reverse=True)[:limit]

    def get_article_count(self) -> int:
        """Return total number of articles."""
        return len(self._articles)

    def get_categories(self) -> list[ArticleCategory]:
        """Return all available categories."""
        return list(ArticleCategory)

"""Recommendation engine."""
from __future__ import annotations

from typing import Dict, List, Optional

from apex_os_bp.knowledge.models import Recommendation
from apex_os_bp.knowledge.knowledge_base import KnowledgeBase
from apex_os_bp.knowledge.document_search import DocumentSearch
from apex_os_bp.knowledge.expert_finder import ExpertFinder
from apex_os_bp.knowledge.knowledge_graph import KnowledgeGraph


class RecommendationEngine:
    """Recommendation engine for knowledge content and experts."""

    def __init__(
        self,
        knowledge_base: Optional[KnowledgeBase] = None,
        document_search: Optional[DocumentSearch] = None,
        expert_finder: Optional[ExpertFinder] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
    ):
        self._kb = knowledge_base
        self._ds = document_search
        self._ef = expert_finder
        self._kg = knowledge_graph
        self._user_interactions: Dict[str, List[str]] = {}

    def record_interaction(self, user_id: str, item_id: str) -> None:
        """Record a user interaction with an item."""
        if user_id not in self._user_interactions:
            self._user_interactions[user_id] = []
        self._user_interactions[user_id].append(item_id)

    def get_user_history(self, user_id: str) -> List[str]:
        """Get user interaction history."""
        return self._user_interactions.get(user_id, [])

    def recommend_for_user(self, user_id: str, limit: int = 5) -> List[Recommendation]:
        """Generate recommendations for a user based on their history."""
        history = self.get_user_history(user_id)
        if not history:
            return []

        # Collect tags and categories from user history
        user_tags: set = set()
        user_categories: set = set()

        if self._kb:
            for item_id in history:
                item = self._kb.get_item(item_id)
                if item:
                    user_tags.update(item.tags)
                    user_categories.add(item.category)

        recommendations: List[Recommendation] = []
        seen_ids: set = set(history)

        # Recommend items with similar tags
        if self._kb:
            for item in self._kb.get_all_items():
                if item.id in seen_ids:
                    continue
                score = 0.0
                reasons: List[str] = []

                # Tag overlap
                tag_overlap = len(set(item.tags) & user_tags)
                if tag_overlap > 0:
                    score += tag_overlap * 2.0
                    reasons.append(f"Shared tags: {tag_overlap}")

                # Same category
                if item.category in user_categories:
                    score += 3.0
                    reasons.append(f"Same category: {item.category}")

                if score > 0:
                    recommendations.append(Recommendation(
                        item_id=item.id,
                        item_type="knowledge_item",
                        score=score,
                        reason="; ".join(reasons),
                    ))
                    seen_ids.add(item.id)

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:limit]

    def recommend_documents(self, query: str, limit: int = 5) -> List[Recommendation]:
        """Recommend documents based on a query."""
        if not self._ds:
            return []

        results = self._ds.search(query, limit=limit)
        return [
            Recommendation(
                item_id=r.document.id,
                item_type="document",
                score=r.score,
                reason=f"Matches query: {query}",
            )
            for r in results
        ]

    def recommend_experts(self, skills: List[str], limit: int = 5) -> List[Recommendation]:
        """Recommend experts based on required skills."""
        if not self._ef:
            return []

        experts = self._ef.find_by_skills(skills, match_all=False)
        recommendations: List[Recommendation] = []

        for expert in experts:
            # Score based on skill match count and expertise level
            expert_skills = set(s.lower() for s in expert.skills)
            query_skills = set(s.lower() for s in skills)
            match_count = len(expert_skills & query_skills)

            level_scores = {
                "novice": 1.0,
                "intermediate": 2.0,
                "advanced": 3.0,
                "expert": 4.0,
            }
            level_score = level_scores.get(expert.expertise_level.value, 1.0)

            score = match_count * level_score
            if expert.available:
                score *= 1.5

            recommendations.append(Recommendation(
                item_id=expert.id,
                item_type="expert",
                score=score,
                reason=f"Skills match: {match_count}, Level: {expert.expertise_level.value}",
            ))

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:limit]

    def recommend_related(self, item_id: str, limit: int = 5) -> List[Recommendation]:
        """Recommend related items based on knowledge graph connections."""
        if not self._kg:
            return []

        node = self._kg.get_node(item_id)
        if not node:
            return []

        neighbors = self._kg.get_neighbors(item_id)
        recommendations: List[Recommendation] = []

        for neighbor in neighbors:
            # Find the edge to get weight
            edges = self._kg.get_edges_from(item_id)
            weight = 1.0
            for edge in edges:
                if edge.target_id == neighbor.id:
                    weight = edge.weight
                    break

            recommendations.append(Recommendation(
                item_id=neighbor.id,
                item_type="knowledge_node",
                score=weight,
                reason=f"Connected via graph: {neighbor.label}",
            ))

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:limit]

    def recommend_trending(self, limit: int = 5) -> List[Recommendation]:
        """Recommend trending items based on interaction frequency."""
        if not self._kb:
            return []

        # Count interactions per item
        item_counts: Dict[str, int] = {}
        for interactions in self._user_interactions.values():
            for item_id in interactions:
                item_counts[item_id] = item_counts.get(item_id, 0) + 1

        recommendations: List[Recommendation] = []
        for item_id, count in item_counts.items():
            item = self._kb.get_item(item_id)
            if item:
                recommendations.append(Recommendation(
                    item_id=item_id,
                    item_type="knowledge_item",
                    score=float(count),
                    reason=f"Interacted {count} times",
                ))

        recommendations.sort(key=lambda r: r.score, reverse=True)
        return recommendations[:limit]

    def clear_history(self, user_id: str) -> bool:
        """Clear user interaction history."""
        if user_id in self._user_interactions:
            del self._user_interactions[user_id]
            return True
        return False

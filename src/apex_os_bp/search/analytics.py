"""Search analytics engine for tracking queries, clicks, and performance."""
from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from apex_os_bp.search.models import SearchAnalyticsEvent


@dataclass
class SearchAnalyticsSummary:
    """Aggregated search analytics summary."""
    total_searches: int = 0
    unique_queries: int = 0
    total_clicks: int = 0
    avg_results_per_search: float = 0.0
    avg_latency_ms: float = 0.0
    click_through_rate: float = 0.0
    top_queries: List[Tuple[str, int]] = field(default_factory=list)
    top_clicked_results: List[Tuple[str, int]] = field(default_factory=list)
    zero_result_queries: List[Tuple[str, int]] = field(default_factory=list)
    searches_over_time: List[Tuple[str, int]] = field(default_factory=list)


class SearchAnalyticsEngine:
    """Search analytics engine for tracking and reporting search behavior.

    Tracks:
    - Search queries with timestamps and result counts
    - Click-through events (which results were clicked)
    - Search latency
    - Zero-result queries
    - Popular queries and trending searches
    - Per-user search history
    """

    def __init__(self) -> None:
        self._events: List[SearchAnalyticsEvent] = []
        self._query_counts: Counter = Counter()
        self._click_counts: Counter = Counter()
        self._user_events: Dict[str, List[SearchAnalyticsEvent]] = defaultdict(list)
        self._session_events: Dict[str, List[SearchAnalyticsEvent]] = defaultdict(list)

    def record_search(
        self,
        query: str,
        user_id: Optional[str] = None,
        result_count: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> SearchAnalyticsEvent:
        """Record a search event."""
        event = SearchAnalyticsEvent(
            id=str(uuid.uuid4()),
            query=query,
            user_id=user_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            result_count=result_count,
            filters=filters or {},
            session_id=session_id,
            latency_ms=latency_ms,
        )
        self._events.append(event)
        self._query_counts[query] += 1
        if user_id:
            self._user_events[user_id].append(event)
        if session_id:
            self._session_events[session_id].append(event)
        return event

    def record_click(
        self,
        query: str,
        result_id: str,
        position: int,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Record a click event on a search result."""
        self._click_counts[result_id] += 1
        # Update the most recent matching event
        for event in reversed(self._events):
            if event.query == query and event.user_id == user_id:
                event.clicked_result_id = result_id
                event.clicked_position = position
                break

    def record_impression(
        self,
        query: str,
        result_ids: List[str],
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Record an impression event (results shown to user)."""
        # Impressions are tracked implicitly via record_search

    def get_summary(self) -> SearchAnalyticsSummary:
        """Get aggregated analytics summary."""
        total = len(self._events)
        unique = len(self._query_counts)
        total_clicks = sum(self._click_counts.values())
        avg_results = (
            sum(e.result_count for e in self._events) / total if total > 0 else 0.0
        )
        latencies = [e.latency_ms for e in self._events if e.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        ctr = total_clicks / total if total > 0 else 0.0

        top_queries = self._query_counts.most_common(10)
        top_clicked = self._click_counts.most_common(10)

        zero_result = [
            (query, count) for query, count in self._query_counts.most_common()
            if any(e.query == query and e.result_count == 0 for e in self._events)
        ]
        # Deduplicate: only include queries that ALWAYS return zero results
        zero_result_queries: List[Tuple[str, int]] = []
        for query, count in self._query_counts.most_common():
            events_for_query = [e for e in self._events if e.query == query]
            if all(e.result_count == 0 for e in events_for_query):
                zero_result_queries.append((query, count))

        # Searches over time (by day)
        day_counts: Counter = Counter()
        for event in self._events:
            if event.timestamp:
                day = event.timestamp[:10]  # YYYY-MM-DD
                day_counts[day] += 1
        searches_over_time = sorted(day_counts.items())

        return SearchAnalyticsSummary(
            total_searches=total,
            unique_queries=unique,
            total_clicks=total_clicks,
            avg_results_per_search=round(avg_results, 2),
            avg_latency_ms=round(avg_latency, 2),
            click_through_rate=round(ctr, 4),
            top_queries=top_queries,
            top_clicked_results=top_clicked,
            zero_result_queries=zero_result_queries,
            searches_over_time=searches_over_time,
        )

    def get_top_queries(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get the most popular search queries."""
        return self._query_counts.most_common(limit)

    def get_zero_result_queries(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get queries that returned zero results."""
        zero_queries: List[Tuple[str, int]] = []
        for query, count in self._query_counts.most_common():
            events_for_query = [e for e in self._events if e.query == query]
            if all(e.result_count == 0 for e in events_for_query):
                zero_queries.append((query, count))
            if len(zero_queries) >= limit:
                break
        return zero_queries

    def get_user_history(self, user_id: str, limit: int = 20) -> List[SearchAnalyticsEvent]:
        """Get search history for a specific user."""
        events = self._user_events.get(user_id, [])
        return events[-limit:]

    def get_session_history(self, session_id: str) -> List[SearchAnalyticsEvent]:
        """Get search events for a specific session."""
        return self._session_events.get(session_id, [])

    def get_click_through_rate(self) -> float:
        """Get overall click-through rate."""
        total = len(self._events)
        if total == 0:
            return 0.0
        clicks = sum(1 for e in self._events if e.clicked_result_id is not None)
        return round(clicks / total, 4)

    def get_avg_latency(self) -> float:
        """Get average search latency in milliseconds."""
        latencies = [e.latency_ms for e in self._events if e.latency_ms is not None]
        if not latencies:
            return 0.0
        return round(sum(latencies) / len(latencies), 2)

    def clear(self) -> None:
        """Clear all analytics data."""
        self._events.clear()
        self._query_counts.clear()
        self._click_counts.clear()
        self._user_events.clear()
        self._session_events.clear()

    @property
    def event_count(self) -> int:
        return len(self._events)

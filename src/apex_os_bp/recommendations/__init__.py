"""Recommendation engine for APEX-OS Business Platform.

Provides collaborative filtering, content-based filtering, hybrid
recommendations, real-time recommendations, and A/B testing.
"""

from .collaborative_filtering import CollaborativeFilter
from .content_based import ContentBasedFilter
from .hybrid import HybridRecommender
from .real_time import RealTimeRecommender
from .ab_testing import ABTestManager, Experiment
from .engine import RecommendationEngine

__all__ = [
    "CollaborativeFilter",
    "ContentBasedFilter",
    "HybridRecommender",
    "RealTimeRecommender",
    "ABTestManager",
    "Experiment",
    "RecommendationEngine",
]

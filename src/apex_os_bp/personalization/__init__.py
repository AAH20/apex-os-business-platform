"""Personalization system for APEX-OS Business Platform.

Provides user profiles, behavior tracking, personalization rules,
A/B testing, and personalization analytics.
"""

from apex_os_bp.personalization.profiles import UserProfile, ProfileStore
from apex_os_bp.personalization.behavior import BehaviorEvent, BehaviorTracker
from apex_os_bp.personalization.rules import PersonalizationRule, RuleEngine
from apex_os_bp.personalization.ab_testing import Experiment, Variant, ABTestManager
from apex_os_bp.personalization.analytics import PersonalizationAnalytics

__all__ = [
    "UserProfile",
    "ProfileStore",
    "BehaviorEvent",
    "BehaviorTracker",
    "PersonalizationRule",
    "RuleEngine",
    "Experiment",
    "Variant",
    "ABTestManager",
    "PersonalizationAnalytics",
]

"""Tests for the gamification system."""

import pytest
from datetime import datetime, timezone, timedelta

from apex_os_bp.gamification.points import PointsSystem, PointsTransaction, PointsTransactionType
from apex_os_bp.gamification.badges import Badge, BadgeManager, BadgeTier, UserBadge
from apex_os_bp.gamification.leaderboards import (
    Leaderboard,
    LeaderboardManager,
    LeaderboardCategory,
    LeaderboardTimeWindow,
    LeaderboardEntry,
)
from apex_os_bp.gamification.challenges import (
    Challenge,
    ChallengeManager,
    ChallengeStatus,
    ChallengeDifficulty,
    UserChallenge,
)
from apex_os_bp.gamification.rewards import (
    Reward,
    RewardManager,
    RewardRarity,
    RewardType,
    RewardRedemption,
)


# ===========================================================================
# Points System Tests
# ===========================================================================


class TestPointsSystem:
    """Tests for the PointsSystem."""

    def setup_method(self):
        self.points = PointsSystem()

    def test_initial_balance_is_zero(self):
        assert self.points.get_balance("user1") == 0

    def test_award_points(self):
        tx = self.points.award_points("user1", 100, "Test reward")
        assert self.points.get_balance("user1") == 100
        assert tx.amount == 100
        assert tx.user_id == "user1"
        assert tx.transaction_type == PointsTransactionType.EARNED

    def test_award_bonus_points(self):
        tx = self.points.award_points(
            "user1", 50, "Bonus", transaction_type=PointsTransactionType.BONUS
        )
        assert tx.transaction_type == PointsTransactionType.BONUS
        assert self.points.get_balance("user1") == 50

    def test_spend_points(self):
        self.points.award_points("user1", 100, "Initial")
        tx = self.points.spend_points("user1", 30, "Purchase")
        assert self.points.get_balance("user1") == 70
        assert tx.amount == -30
        assert tx.transaction_type == PointsTransactionType.SPENT

    def test_spend_points_insufficient_balance(self):
        self.points.award_points("user1", 50, "Initial")
        with pytest.raises(ValueError, match="Insufficient points"):
            self.points.spend_points("user1", 100, "Purchase")

    def test_spend_points_zero_amount(self):
        with pytest.raises(ValueError, match="must be positive"):
            self.points.spend_points("user1", 0, "Nothing")

    def test_award_zero_points_raises(self):
        with pytest.raises(ValueError, match="zero"):
            self.points.award_points("user1", 0, "Nothing")

    def test_negative_spend_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            self.points.spend_points("user1", -10, "Negative")

    def test_adjust_points_positive(self):
        self.points.award_points("user1", 100, "Initial")
        self.points.adjust_points("user1", 50, "Admin bonus")
        assert self.points.get_balance("user1") == 150

    def test_adjust_points_negative(self):
        self.points.award_points("user1", 100, "Initial")
        self.points.adjust_points("user1", -30, "Admin penalty")
        assert self.points.get_balance("user1") == 70

    def test_get_transactions(self):
        self.points.award_points("user1", 100, "First")
        self.points.award_points("user1", 50, "Second")
        self.points.spend_points("user1", 30, "Spent")
        txs = self.points.get_transactions("user1")
        assert len(txs) == 3

    def test_get_transactions_filtered(self):
        self.points.award_points("user1", 100, "First")
        self.points.spend_points("user1", 30, "Spent")
        earned = self.points.get_transactions("user1", PointsTransactionType.EARNED)
        spent = self.points.get_transactions("user1", PointsTransactionType.SPENT)
        assert len(earned) == 1
        assert len(spent) == 1

    def test_transaction_history_sorted(self):
        self.points.award_points("user1", 100, "First")
        self.points.award_points("user1", 200, "Second")
        history = self.points.get_transaction_history("user1")
        assert len(history) == 2
        # Most recent first
        assert history[0].amount == 200

    def test_total_earned(self):
        self.points.award_points("user1", 100, "First")
        self.points.award_points("user1", 50, "Second")
        self.points.spend_points("user1", 30, "Spent")
        assert self.points.get_total_earned("user1") == 150

    def test_total_spent(self):
        self.points.award_points("user1", 100, "First")
        self.points.spend_points("user1", 30, "Spent")
        self.points.spend_points("user1", 20, "Spent2")
        assert self.points.get_total_spent("user1") == 50

    def test_reset_user(self):
        self.points.award_points("user1", 100, "First")
        self.points.reset_user("user1")
        assert self.points.get_balance("user1") == 0
        assert self.points.get_transactions("user1") == []

    def test_multiple_users(self):
        self.points.award_points("user1", 100, "First")
        self.points.award_points("user2", 200, "Second")
        assert self.points.get_balance("user1") == 100
        assert self.points.get_balance("user2") == 200

    def test_get_all_balances(self):
        self.points.award_points("user1", 100, "First")
        self.points.award_points("user2", 200, "Second")
        balances = self.points.get_all_balances()
        assert balances == {"user1": 100, "user2": 200}

    def test_transaction_with_metadata(self):
        tx = self.points.award_points(
            "user1", 100, "Test", metadata={"source": "test", "level": "5"}
        )
        assert tx.metadata["source"] == "test"
        assert tx.metadata["level"] == "5"

    def test_transaction_auto_id(self):
        tx = self.points.award_points("user1", 100, "Test")
        assert tx.transaction_id is not None
        assert len(tx.transaction_id) > 0

    def test_transaction_auto_timestamp(self):
        tx = self.points.award_points("user1", 100, "Test")
        assert tx.timestamp is not None


# ===========================================================================
# Badge System Tests
# ===========================================================================


class TestBadgeManager:
    """Tests for the BadgeManager."""

    def setup_method(self):
        self.manager = BadgeManager()
        self.badge = Badge(
            name="First Steps",
            description="Complete your first task",
            tier=BadgeTier.BRONZE,
            points_bonus=10,
        )

    def test_register_badge(self):
        result = self.manager.register_badge(self.badge)
        assert result.badge_id == self.badge.badge_id
        assert self.manager.get_badge(self.badge.badge_id) is not None

    def test_register_duplicate_badge_raises(self):
        self.manager.register_badge(self.badge)
        with pytest.raises(ValueError, match="already exists"):
            self.manager.register_badge(self.badge)

    def test_get_badge_not_found(self):
        assert self.manager.get_badge("nonexistent") is None

    def test_get_all_badges(self):
        self.manager.register_badge(self.badge)
        badge2 = Badge(name="Second", description="Test", tier=BadgeTier.SILVER)
        self.manager.register_badge(badge2)
        assert len(self.manager.get_all_badges()) == 2

    def test_get_badges_by_tier(self):
        self.manager.register_badge(self.badge)
        silver = Badge(name="Silver Badge", description="Test", tier=BadgeTier.SILVER)
        self.manager.register_badge(silver)
        bronze_badges = self.manager.get_badges_by_tier(BadgeTier.BRONZE)
        assert len(bronze_badges) == 1
        assert bronze_badges[0].name == "First Steps"

    def test_get_badges_by_tag(self):
        tagged = Badge(
            name="Tagged",
            description="Test",
            tier=BadgeTier.BRONZE,
            tags={"onboarding", "beginner"},
        )
        self.manager.register_badge(tagged)
        self.manager.register_badge(self.badge)
        result = self.manager.get_badges_by_tag("onboarding")
        assert len(result) == 1
        assert result[0].name == "Tagged"

    def test_award_badge(self):
        self.manager.register_badge(self.badge)
        user_badge = self.manager.award_badge("user1", self.badge.badge_id)
        assert user_badge.user_id == "user1"
        assert user_badge.badge.badge_id == self.badge.badge_id

    def test_award_badge_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            self.manager.award_badge("user1", "nonexistent")

    def test_award_duplicate_badge_raises(self):
        self.manager.register_badge(self.badge)
        self.manager.award_badge("user1", self.badge.badge_id)
        with pytest.raises(ValueError, match="already has"):
            self.manager.award_badge("user1", self.badge.badge_id)

    def test_award_badge_max_reached(self):
        limited = Badge(
            name="Limited",
            description="Test",
            tier=BadgeTier.BRONZE,
            max_awards=1,
        )
        self.manager.register_badge(limited)
        self.manager.award_badge("user1", limited.badge_id)
        with pytest.raises(ValueError, match="max awards"):
            self.manager.award_badge("user2", limited.badge_id)

    def test_get_user_badges(self):
        self.manager.register_badge(self.badge)
        self.manager.award_badge("user1", self.badge.badge_id)
        badges = self.manager.get_user_badges("user1")
        assert len(badges) == 1

    def test_has_badge(self):
        self.manager.register_badge(self.badge)
        assert not self.manager.has_badge("user1", self.badge.badge_id)
        self.manager.award_badge("user1", self.badge.badge_id)
        assert self.manager.has_badge("user1", self.badge.badge_id)

    def test_get_badge_count(self):
        self.manager.register_badge(self.badge)
        assert self.manager.get_badge_count(self.badge.badge_id) == 0
        self.manager.award_badge("user1", self.badge.badge_id)
        assert self.manager.get_badge_count(self.badge.badge_id) == 1

    def test_get_user_badge_count(self):
        self.manager.register_badge(self.badge)
        badge2 = Badge(name="Second", description="Test", tier=BadgeTier.SILVER)
        self.manager.register_badge(badge2)
        self.manager.award_badge("user1", self.badge.badge_id)
        self.manager.award_badge("user1", badge2.badge_id)
        assert self.manager.get_user_badge_count("user1") == 2

    def test_get_user_badges_by_tier(self):
        self.manager.register_badge(self.badge)
        silver = Badge(name="Silver", description="Test", tier=BadgeTier.SILVER)
        self.manager.register_badge(silver)
        self.manager.award_badge("user1", self.badge.badge_id)
        self.manager.award_badge("user1", silver.badge_id)
        bronze = self.manager.get_user_badges_by_tier("user1", BadgeTier.BRONZE)
        assert len(bronze) == 1

    def test_get_recent_badges(self):
        self.manager.register_badge(self.badge)
        badge2 = Badge(name="Second", description="Test", tier=BadgeTier.SILVER)
        self.manager.register_badge(badge2)
        self.manager.award_badge("user1", self.badge.badge_id)
        self.manager.award_badge("user1", badge2.badge_id)
        recent = self.manager.get_recent_badges("user1", limit=1)
        assert len(recent) == 1

    def test_remove_badge(self):
        self.manager.register_badge(self.badge)
        self.manager.award_badge("user1", self.badge.badge_id)
        assert self.manager.remove_badge("user1", self.badge.badge_id)
        assert not self.manager.has_badge("user1", self.badge.badge_id)

    def test_remove_badge_not_found(self):
        assert not self.manager.remove_badge("user1", "nonexistent")

    def test_get_leaderboard_badges(self):
        self.manager.register_badge(self.badge)
        badge2 = Badge(name="Popular", description="Test", tier=BadgeTier.SILVER)
        self.manager.register_badge(badge2)
        self.manager.award_badge("user1", badge2.badge_id)
        self.manager.award_badge("user2", badge2.badge_id)
        top = self.manager.get_leaderboard_badges(limit=1)
        assert top[0].name == "Popular"

    def test_badge_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Badge(name="", description="Test", tier=BadgeTier.BRONZE)

    def test_badge_negative_points_bonus_raises(self):
        with pytest.raises(ValueError, match="negative"):
            Badge(name="Test", description="Test", tier=BadgeTier.BRONZE, points_bonus=-5)

    def test_award_badge_with_awarded_by(self):
        self.manager.register_badge(self.badge)
        ub = self.manager.award_badge("user1", self.badge.badge_id, awarded_by="admin")
        assert ub.awarded_by == "admin"


# ===========================================================================
# Leaderboard Tests
# ===========================================================================


class TestLeaderboardManager:
    """Tests for the LeaderboardManager."""

    def setup_method(self):
        self.manager = LeaderboardManager()
        self.lb = self.manager.create_leaderboard(
            name="Test Leaderboard",
            category=LeaderboardCategory.POINTS,
            time_window=LeaderboardTimeWindow.ALL_TIME,
        )

    def test_create_leaderboard(self):
        assert self.lb.leaderboard_id is not None
        assert self.lb.name == "Test Leaderboard"
        assert self.lb.is_active is True

    def test_get_leaderboard(self):
        result = self.manager.get_leaderboard(self.lb.leaderboard_id)
        assert result is not None
        assert result.name == "Test Leaderboard"

    def test_get_leaderboard_not_found(self):
        assert self.manager.get_leaderboard("nonexistent") is None

    def test_get_all_leaderboards(self):
        self.manager.create_leaderboard(
            name="Second",
            category=LeaderboardCategory.BADGES,
            time_window=LeaderboardTimeWindow.WEEKLY,
        )
        assert len(self.manager.get_all_leaderboards()) == 2

    def test_get_leaderboards_by_category(self):
        self.manager.create_leaderboard(
            name="Badge LB",
            category=LeaderboardCategory.BADGES,
            time_window=LeaderboardTimeWindow.ALL_TIME,
        )
        points_lbs = self.manager.get_leaderboards_by_category(LeaderboardCategory.POINTS)
        assert len(points_lbs) == 1
        assert points_lbs[0].name == "Test Leaderboard"

    def test_get_leaderboards_by_time_window(self):
        self.manager.create_leaderboard(
            name="Weekly LB",
            category=LeaderboardCategory.POINTS,
            time_window=LeaderboardTimeWindow.WEEKLY,
        )
        weekly = self.manager.get_leaderboards_by_time_window(LeaderboardTimeWindow.WEEKLY)
        assert len(weekly) == 1

    def test_submit_score(self):
        entry = self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        assert entry.user_id == "user1"
        assert entry.score == 100
        assert entry.rank == 1

    def test_submit_score_multiple_users(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        self.manager.submit_score(self.lb.leaderboard_id, "user2", 200)
        self.manager.submit_score(self.lb.leaderboard_id, "user3", 150)

        rankings = self.manager.get_rankings(self.lb.leaderboard_id)
        assert len(rankings) == 3
        assert rankings[0].user_id == "user2"  # 200
        assert rankings[1].user_id == "user3"  # 150
        assert rankings[2].user_id == "user1"  # 100

    def test_submit_score_updates_existing(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 200)
        entry = self.manager.get_user_rank(self.lb.leaderboard_id, "user1")
        assert entry.score == 200

    def test_submit_score_inactive_leaderboard(self):
        self.manager.deactivate_leaderboard(self.lb.leaderboard_id)
        with pytest.raises(ValueError, match="not active"):
            self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)

    def test_submit_score_nonexistent_leaderboard(self):
        with pytest.raises(ValueError, match="not found"):
            self.manager.submit_score("nonexistent", "user1", 100)

    def test_get_rankings(self):
        for i in range(5):
            self.manager.submit_score(self.lb.leaderboard_id, f"user{i}", (5 - i) * 100)
        rankings = self.manager.get_rankings(self.lb.leaderboard_id)
        assert len(rankings) == 5
        assert rankings[0].score == 500

    def test_get_rankings_with_limit(self):
        for i in range(5):
            self.manager.submit_score(self.lb.leaderboard_id, f"user{i}", (5 - i) * 100)
        rankings = self.manager.get_rankings(self.lb.leaderboard_id, limit=3)
        assert len(rankings) == 3

    def test_get_user_rank(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        entry = self.manager.get_user_rank(self.lb.leaderboard_id, "user1")
        assert entry is not None
        assert entry.rank == 1

    def test_get_user_rank_not_found(self):
        assert self.manager.get_user_rank(self.lb.leaderboard_id, "nonexistent") is None

    def test_get_user_rank_number(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        self.manager.submit_score(self.lb.leaderboard_id, "user2", 200)
        assert self.manager.get_user_rank_number(self.lb.leaderboard_id, "user1") == 2
        assert self.manager.get_user_rank_number(self.lb.leaderboard_id, "user2") == 1

    def test_get_top_users(self):
        for i in range(5):
            self.manager.submit_score(self.lb.leaderboard_id, f"user{i}", (5 - i) * 100)
        top = self.manager.get_top_users(self.lb.leaderboard_id, count=3)
        assert len(top) == 3
        assert top[0].user_id == "user0"

    def test_get_user_percentile(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        self.manager.submit_score(self.lb.leaderboard_id, "user2", 200)
        self.manager.submit_score(self.lb.leaderboard_id, "user3", 300)
        self.manager.submit_score(self.lb.leaderboard_id, "user4", 400)
        # user4 is rank 1 out of 4 -> percentile = (1 - 0/3) * 100 = 100
        assert self.manager.get_user_percentile(self.lb.leaderboard_id, "user4") == 100.0
        # user1 is rank 4 out of 4 -> percentile = (1 - 3/3) * 100 = 0
        assert self.manager.get_user_percentile(self.lb.leaderboard_id, "user1") == 0.0

    def test_remove_entry(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        assert self.manager.remove_entry(self.lb.leaderboard_id, "user1")
        assert self.manager.get_user_rank(self.lb.leaderboard_id, "user1") is None

    def test_remove_entry_not_found(self):
        assert not self.manager.remove_entry(self.lb.leaderboard_id, "nonexistent")

    def test_reset_leaderboard(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        self.manager.reset_leaderboard(self.lb.leaderboard_id)
        assert self.manager.get_rankings(self.lb.leaderboard_id) == []

    def test_deactivate_leaderboard(self):
        self.manager.deactivate_leaderboard(self.lb.leaderboard_id)
        assert not self.lb.is_active

    def test_activate_leaderboard(self):
        self.manager.deactivate_leaderboard(self.lb.leaderboard_id)
        self.manager.activate_leaderboard(self.lb.leaderboard_id)
        assert self.lb.is_active

    def test_rank_change_tracking(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        self.manager.submit_score(self.lb.leaderboard_id, "user2", 200)
        # user1 resubmits with higher score -> rank improves
        entry = self.manager.submit_score(self.lb.leaderboard_id, "user1", 300)
        # user1 was rank 2, now rank 1 -> rank_change = 2 - 1 = 1
        assert entry.rank_change == 1

    def test_get_rank_changes(self):
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 100)
        self.manager.submit_score(self.lb.leaderboard_id, "user2", 200)
        # user1 resubmits with higher score -> rank changes
        self.manager.submit_score(self.lb.leaderboard_id, "user1", 300)
        changes = self.manager.get_rank_changes(self.lb.leaderboard_id)
        assert len(changes) == 1
        assert changes[0].user_id == "user1"

    def test_leaderboard_max_entries(self):
        lb = self.manager.create_leaderboard(
            name="Limited LB",
            category=LeaderboardCategory.POINTS,
            time_window=LeaderboardTimeWindow.ALL_TIME,
            max_entries=3,
        )
        for i in range(5):
            self.manager.submit_score(lb.leaderboard_id, f"user{i}", (5 - i) * 100)
        rankings = self.manager.get_rankings(lb.leaderboard_id)
        assert len(rankings) == 3

    def test_leaderboard_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            self.manager.create_leaderboard(
                name="",
                category=LeaderboardCategory.POINTS,
                time_window=LeaderboardTimeWindow.ALL_TIME,
            )

    def test_leaderboard_invalid_max_entries(self):
        with pytest.raises(ValueError, match="at least 1"):
            self.manager.create_leaderboard(
                name="Test",
                category=LeaderboardCategory.POINTS,
                time_window=LeaderboardTimeWindow.ALL_TIME,
                max_entries=0,
            )


# ===========================================================================
# Challenge Tests
# ===========================================================================


class TestChallengeManager:
    """Tests for the ChallengeManager."""

    def setup_method(self):
        self.manager = ChallengeManager()
        self.challenge = self.manager.create_challenge(
            name="Daily Login",
            description="Log in every day",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            required_actions=1,
        )

    def test_create_challenge(self):
        assert self.challenge.challenge_id is not None
        assert self.challenge.name == "Daily Login"
        assert self.challenge.is_active is True

    def test_get_challenge(self):
        result = self.manager.get_challenge(self.challenge.challenge_id)
        assert result is not None
        assert result.name == "Daily Login"

    def test_get_challenge_not_found(self):
        assert self.manager.get_challenge("nonexistent") is None

    def test_get_all_challenges(self):
        self.manager.create_challenge(
            name="Second",
            description="Test",
            difficulty=ChallengeDifficulty.MEDIUM,
            points_reward=20,
        )
        assert len(self.manager.get_all_challenges()) == 2

    def test_get_active_challenges(self):
        self.manager.create_challenge(
            name="Future",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
        )
        active = self.manager.get_active_challenges()
        assert len(active) == 1
        assert active[0].name == "Daily Login"

    def test_get_challenges_by_difficulty(self):
        self.manager.create_challenge(
            name="Hard Challenge",
            description="Test",
            difficulty=ChallengeDifficulty.HARD,
            points_reward=50,
        )
        easy = self.manager.get_challenges_by_difficulty(ChallengeDifficulty.EASY)
        assert len(easy) == 1

    def test_get_challenges_by_tag(self):
        self.manager.create_challenge(
            name="Tagged Challenge",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            tags={"daily", "login"},
        )
        result = self.manager.get_challenges_by_tag("daily")
        assert len(result) == 1

    def test_get_upcoming_challenges(self):
        self.manager.create_challenge(
            name="Future",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        upcoming = self.manager.get_upcoming_challenges()
        assert len(upcoming) == 1
        assert upcoming[0].name == "Future"

    def test_get_expired_challenges(self):
        self.manager.create_challenge(
            name="Past",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            start_time=datetime.now(timezone.utc) - timedelta(days=2),
            end_time=datetime.now(timezone.utc) - timedelta(days=1),
        )
        expired = self.manager.get_expired_challenges()
        assert len(expired) == 1

    def test_start_challenge(self):
        uc = self.manager.start_challenge("user1", self.challenge.challenge_id)
        assert uc.user_id == "user1"
        assert uc.status == ChallengeStatus.ACTIVE
        assert uc.progress == 0

    def test_start_challenge_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            self.manager.start_challenge("user1", "nonexistent")

    def test_start_challenge_not_active(self):
        future = self.manager.create_challenge(
            name="Future",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            start_time=datetime.now(timezone.utc) + timedelta(days=1),
        )
        with pytest.raises(ValueError, match="not active"):
            self.manager.start_challenge("user1", future.challenge_id)

    def test_start_challenge_already_active(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        with pytest.raises(ValueError, match="already has an active"):
            self.manager.start_challenge("user1", self.challenge.challenge_id)

    def test_start_challenge_already_completed(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        self.manager.complete_challenge("user1", self.challenge.challenge_id)
        with pytest.raises(ValueError, match="already completed"):
            self.manager.start_challenge("user1", self.challenge.challenge_id)

    def test_start_challenge_max_completions(self):
        limited = self.manager.create_challenge(
            name="Limited",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            max_completions=1,
        )
        self.manager.start_challenge("user1", limited.challenge_id)
        self.manager.complete_challenge("user1", limited.challenge_id)
        with pytest.raises(ValueError, match="max completions"):
            self.manager.start_challenge("user2", limited.challenge_id)

    def test_update_progress(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        uc = self.manager.update_progress("user1", self.challenge.challenge_id, 1)
        assert uc.progress == 1
        assert uc.status == ChallengeStatus.COMPLETED

    def test_update_progress_not_found(self):
        with pytest.raises(ValueError, match="no challenge"):
            self.manager.update_progress("user1", "nonexistent")

    def test_update_progress_not_active(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        self.manager.complete_challenge("user1", self.challenge.challenge_id)
        with pytest.raises(ValueError, match="not active"):
            self.manager.update_progress("user1", self.challenge.challenge_id)

    def test_complete_challenge(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        uc = self.manager.complete_challenge("user1", self.challenge.challenge_id)
        assert uc.status == ChallengeStatus.COMPLETED
        assert uc.completed_at is not None

    def test_fail_challenge(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        uc = self.manager.fail_challenge("user1", self.challenge.challenge_id)
        assert uc.status == ChallengeStatus.FAILED

    def test_get_user_challenges(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        challenges = self.manager.get_user_challenges("user1")
        assert len(challenges) == 1

    def test_get_user_challenges_filtered(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        self.manager.complete_challenge("user1", self.challenge.challenge_id)
        completed = self.manager.get_user_challenges("user1", ChallengeStatus.COMPLETED)
        assert len(completed) == 1
        active = self.manager.get_user_challenges("user1", ChallengeStatus.ACTIVE)
        assert len(active) == 0

    def test_get_user_active_challenges(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        active = self.manager.get_user_active_challenges("user1")
        assert len(active) == 1

    def test_get_user_completed_challenges(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        self.manager.complete_challenge("user1", self.challenge.challenge_id)
        completed = self.manager.get_user_completed_challenges("user1")
        assert len(completed) == 1

    def test_get_user_challenge_count(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        assert self.manager.get_user_challenge_count("user1") == 1

    def test_get_challenge_completion_count(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        self.manager.complete_challenge("user1", self.challenge.challenge_id)
        assert self.manager.get_challenge_completion_count(self.challenge.challenge_id) == 1

    def test_get_challenge_leaderboard(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        self.manager.complete_challenge("user1", self.challenge.challenge_id)
        self.manager.start_challenge("user2", self.challenge.challenge_id)
        self.manager.complete_challenge("user2", self.challenge.challenge_id)
        lb = self.manager.get_challenge_leaderboard(self.challenge.challenge_id)
        assert len(lb) == 2

    def test_cancel_challenge(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        assert self.manager.cancel_challenge("user1", self.challenge.challenge_id)
        uc = self.manager.get_user_challenges("user1")[0]
        assert uc.status == ChallengeStatus.CANCELLED

    def test_cancel_challenge_not_active(self):
        assert not self.manager.cancel_challenge("user1", self.challenge.challenge_id)

    def test_get_available_challenges(self):
        self.manager.start_challenge("user1", self.challenge.challenge_id)
        available = self.manager.get_available_challenges("user1")
        assert len(available) == 0

    def test_challenge_with_time_window(self):
        ch = self.manager.create_challenge(
            name="Timed",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            start_time=datetime.now(timezone.utc) - timedelta(hours=1),
            end_time=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert ch.is_active is True
        assert ch.duration is not None
        assert ch.time_remaining is not None

    def test_challenge_invalid_time_range(self):
        with pytest.raises(ValueError, match="Start time must be before end time"):
            self.manager.create_challenge(
                name="Invalid",
                description="Test",
                difficulty=ChallengeDifficulty.EASY,
                points_reward=10,
                start_time=datetime.now(timezone.utc) + timedelta(hours=2),
                end_time=datetime.now(timezone.utc) + timedelta(hours=1),
            )

    def test_challenge_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            self.manager.create_challenge(
                name="",
                description="Test",
                difficulty=ChallengeDifficulty.EASY,
                points_reward=10,
            )

    def test_challenge_negative_points_raises(self):
        with pytest.raises(ValueError, match="negative"):
            self.manager.create_challenge(
                name="Test",
                description="Test",
                difficulty=ChallengeDifficulty.EASY,
                points_reward=-10,
            )

    def test_challenge_zero_required_actions_raises(self):
        with pytest.raises(ValueError, match="at least 1"):
            self.manager.create_challenge(
                name="Test",
                description="Test",
                difficulty=ChallengeDifficulty.EASY,
                points_reward=10,
                required_actions=0,
            )

    def test_progress_percentage(self):
        ch = self.manager.create_challenge(
            name="Multi",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            required_actions=4,
        )
        self.manager.start_challenge("user1", ch.challenge_id)
        uc = self.manager.update_progress("user1", ch.challenge_id, 2)
        assert uc.progress_percentage == 50.0

    def test_is_complete(self):
        ch = self.manager.create_challenge(
            name="Multi",
            description="Test",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=10,
            required_actions=2,
        )
        self.manager.start_challenge("user1", ch.challenge_id)
        uc = self.manager.update_progress("user1", ch.challenge_id, 1)
        assert not uc.is_complete
        uc = self.manager.update_progress("user1", ch.challenge_id, 1)
        assert uc.is_complete


# ===========================================================================
# Reward Tests
# ===========================================================================


class TestRewardManager:
    """Tests for the RewardManager."""

    def setup_method(self):
        self.manager = RewardManager()
        self.points = PointsSystem()
        self.reward = self.manager.create_reward(
            name="Test Reward",
            description="A test reward",
            cost=100,
            rarity=RewardRarity.COMMON,
        )

    def test_create_reward(self):
        assert self.reward.reward_id is not None
        assert self.reward.name == "Test Reward"
        assert self.reward.is_active is True

    def test_get_reward(self):
        result = self.manager.get_reward(self.reward.reward_id)
        assert result is not None
        assert result.name == "Test Reward"

    def test_get_reward_not_found(self):
        assert self.manager.get_reward("nonexistent") is None

    def test_get_all_rewards(self):
        self.manager.create_reward(
            name="Second",
            description="Test",
            cost=200,
            rarity=RewardRarity.RARE,
        )
        assert len(self.manager.get_all_rewards()) == 2

    def test_get_available_rewards(self):
        self.manager.create_reward(
            name="Unavailable",
            description="Test",
            cost=100,
            rarity=RewardRarity.COMMON,
            stock=0,
        )
        available = self.manager.get_available_rewards()
        assert len(available) == 1
        assert available[0].name == "Test Reward"

    def test_get_rewards_by_rarity(self):
        self.manager.create_reward(
            name="Rare Reward",
            description="Test",
            cost=500,
            rarity=RewardRarity.RARE,
        )
        common = self.manager.get_rewards_by_rarity(RewardRarity.COMMON)
        assert len(common) == 1

    def test_get_rewards_by_type(self):
        self.manager.create_reward(
            name="Physical Reward",
            description="Test",
            cost=200,
            rarity=RewardRarity.UNCOMMON,
            reward_type=RewardType.PHYSICAL,
        )
        digital = self.manager.get_rewards_by_type(RewardType.DIGITAL)
        assert len(digital) == 1

    def test_get_rewards_by_tag(self):
        self.manager.create_reward(
            name="Tagged Reward",
            description="Test",
            cost=100,
            rarity=RewardRarity.COMMON,
            tags={"special", "limited"},
        )
        result = self.manager.get_rewards_by_tag("special")
        assert len(result) == 1

    def test_get_affordable_rewards(self):
        self.points.award_points("user1", 150, "Initial")
        self.manager.create_reward(
            name="Expensive",
            description="Test",
            cost=500,
            rarity=RewardRarity.EPIC,
        )
        affordable = self.manager.get_affordable_rewards(150)
        assert len(affordable) == 1
        assert affordable[0].name == "Test Reward"

    def test_redeem_reward(self):
        self.points.award_points("user1", 200, "Initial")
        redemption = self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        assert redemption.user_id == "user1"
        assert redemption.points_spent == 100
        assert self.points.get_balance("user1") == 100

    def test_redeem_reward_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            self.manager.redeem_reward("user1", "nonexistent", self.points)

    def test_redeem_reward_not_available(self):
        sold_out = self.manager.create_reward(
            name="Sold Out",
            description="Test",
            cost=100,
            rarity=RewardRarity.COMMON,
            stock=0,
        )
        self.points.award_points("user1", 200, "Initial")
        with pytest.raises(ValueError, match="not available"):
            self.manager.redeem_reward("user1", sold_out.reward_id, self.points)

    def test_redeem_reward_insufficient_points(self):
        self.points.award_points("user1", 50, "Initial")
        with pytest.raises(ValueError, match="Insufficient points"):
            self.manager.redeem_reward("user1", self.reward.reward_id, self.points)

    def test_redeem_reward_max_per_user(self):
        limited = self.manager.create_reward(
            name="Limited",
            description="Test",
            cost=50,
            rarity=RewardRarity.COMMON,
            max_per_user=1,
        )
        self.points.award_points("user1", 200, "Initial")
        self.manager.redeem_reward("user1", limited.reward_id, self.points)
        with pytest.raises(ValueError, match="max redemptions"):
            self.manager.redeem_reward("user1", limited.reward_id, self.points)

    def test_redeem_reward_decreases_stock(self):
        stocked = self.manager.create_reward(
            name="Stocked",
            description="Test",
            cost=50,
            rarity=RewardRarity.COMMON,
            stock=2,
        )
        self.points.award_points("user1", 200, "Initial")
        self.manager.redeem_reward("user1", stocked.reward_id, self.points)
        assert stocked.stock == 1

    def test_get_user_redemptions(self):
        self.points.award_points("user1", 200, "Initial")
        self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        redemptions = self.manager.get_user_redemptions("user1")
        assert len(redemptions) == 1

    def test_get_user_redemptions_filtered(self):
        self.points.award_points("user1", 200, "Initial")
        self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        pending = self.manager.get_user_redemptions("user1", status="pending")
        assert len(pending) == 1
        fulfilled = self.manager.get_user_redemptions("user1", status="fulfilled")
        assert len(fulfilled) == 0

    def test_get_user_redemption_count(self):
        self.points.award_points("user1", 200, "Initial")
        self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        assert self.manager.get_user_redemption_count("user1", self.reward.reward_id) == 1

    def test_get_total_redemptions(self):
        self.points.award_points("user1", 200, "Initial")
        self.points.award_points("user2", 200, "Initial")
        self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        self.manager.redeem_reward("user2", self.reward.reward_id, self.points)
        assert self.manager.get_total_redemptions(self.reward.reward_id) == 2

    def test_update_redemption_status(self):
        self.points.award_points("user1", 200, "Initial")
        redemption = self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        updated = self.manager.update_redemption_status(redemption.redemption_id, "fulfilled")
        assert updated is not None
        assert updated.status == "fulfilled"

    def test_update_redemption_status_not_found(self):
        assert self.manager.update_redemption_status("nonexistent", "fulfilled") is None

    def test_cancel_redemption(self):
        self.points.award_points("user1", 200, "Initial")
        redemption = self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        assert self.points.get_balance("user1") == 100

        cancelled = self.manager.cancel_redemption(redemption.redemption_id, self.points)
        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert self.points.get_balance("user1") == 200

    def test_cancel_redemption_restores_stock(self):
        stocked = self.manager.create_reward(
            name="Stocked",
            description="Test",
            cost=50,
            rarity=RewardRarity.COMMON,
            stock=1,
        )
        self.points.award_points("user1", 200, "Initial")
        redemption = self.manager.redeem_reward("user1", stocked.reward_id, self.points)
        assert stocked.stock == 0
        self.manager.cancel_redemption(redemption.redemption_id, self.points)
        assert stocked.stock == 1

    def test_cancel_redemption_not_pending(self):
        self.points.award_points("user1", 200, "Initial")
        redemption = self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        self.manager.update_redemption_status(redemption.redemption_id, "fulfilled")
        with pytest.raises(ValueError, match="Cannot cancel"):
            self.manager.cancel_redemption(redemption.redemption_id, self.points)

    def test_cancel_redemption_not_found(self):
        assert self.manager.cancel_redemption("nonexistent", self.points) is None

    def test_get_popular_rewards(self):
        self.points.award_points("user1", 500, "Initial")
        self.points.award_points("user2", 500, "Initial")
        self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        self.manager.redeem_reward("user2", self.reward.reward_id, self.points)
        popular = self.manager.get_popular_rewards(limit=1)
        assert popular[0].name == "Test Reward"

    def test_get_user_reward_history(self):
        self.points.award_points("user1", 500, "Initial")
        self.manager.redeem_reward("user1", self.reward.reward_id, self.points)
        history = self.manager.get_user_reward_history("user1")
        assert len(history) == 1

    def test_deactivate_reward(self):
        self.manager.deactivate_reward(self.reward.reward_id)
        assert not self.reward.is_active

    def test_activate_reward(self):
        self.manager.deactivate_reward(self.reward.reward_id)
        self.manager.activate_reward(self.reward.reward_id)
        assert self.reward.is_active

    def test_restock_reward(self):
        stocked = self.manager.create_reward(
            name="Stocked",
            description="Test",
            cost=50,
            rarity=RewardRarity.COMMON,
            stock=5,
        )
        self.manager.restock_reward(stocked.reward_id, 3)
        assert stocked.stock == 8

    def test_restock_reward_not_found(self):
        with pytest.raises(ValueError, match="not found"):
            self.manager.restock_reward("nonexistent", 5)

    def test_restock_reward_negative_amount(self):
        with pytest.raises(ValueError, match="negative"):
            self.manager.restock_reward(self.reward.reward_id, -5)

    def test_reward_empty_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            self.manager.create_reward(
                name="",
                description="Test",
                cost=100,
                rarity=RewardRarity.COMMON,
            )

    def test_reward_negative_cost_raises(self):
        with pytest.raises(ValueError, match="negative"):
            self.manager.create_reward(
                name="Test",
                description="Test",
                cost=-100,
                rarity=RewardRarity.COMMON,
            )

    def test_reward_negative_stock_raises(self):
        with pytest.raises(ValueError, match="negative"):
            self.manager.create_reward(
                name="Test",
                description="Test",
                cost=100,
                rarity=RewardRarity.COMMON,
                stock=-1,
            )

    def test_reward_is_available(self):
        assert self.reward.is_available is True
        self.reward.stock = 0
        assert self.reward.is_available is False
        self.reward.stock = 5
        self.reward.is_active = False
        assert self.reward.is_available is False

    def test_reward_remaining_stock(self):
        assert self.reward.remaining_stock is None
        self.reward.stock = 10
        assert self.reward.remaining_stock == 10


# ===========================================================================
# Integration Tests
# ===========================================================================


class TestGamificationIntegration:
    """Integration tests across multiple gamification components."""

    def setup_method(self):
        self.points = PointsSystem()
        self.badges = BadgeManager()
        self.challenges = ChallengeManager()
        self.rewards = RewardManager()
        self.leaderboards = LeaderboardManager()

    def test_full_challenge_flow(self):
        """Test a complete challenge flow: create, start, complete, earn points."""
        # Create a challenge
        challenge = self.challenges.create_challenge(
            name="Complete Profile",
            description="Fill in all profile fields",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=50,
            required_actions=3,
        )

        # Start the challenge
        self.challenges.start_challenge("user1", challenge.challenge_id)

        # Update progress
        self.challenges.update_progress("user1", challenge.challenge_id, 1)
        self.challenges.update_progress("user1", challenge.challenge_id, 1)
        uc = self.challenges.update_progress("user1", challenge.challenge_id, 1)

        assert uc.status == ChallengeStatus.COMPLETED

        # Award points
        self.points.award_points("user1", challenge.points_reward, f"Completed: {challenge.name}")
        assert self.points.get_balance("user1") == 50

    def test_challenge_with_badge_reward(self):
        """Test completing a challenge awards a badge."""
        badge = self.badges.register_badge(
            Badge(
                name="Challenger",
                description="Complete a challenge",
                tier=BadgeTier.BRONZE,
            )
        )

        challenge = self.challenges.create_challenge(
            name="First Challenge",
            description="Complete this challenge",
            difficulty=ChallengeDifficulty.EASY,
            points_reward=25,
            badge_reward_id=badge.badge_id,
        )

        self.challenges.start_challenge("user1", challenge.challenge_id)
        self.challenges.complete_challenge("user1", challenge.challenge_id)

        # Award badge
        self.badges.award_badge("user1", badge.badge_id)
        assert self.badges.has_badge("user1", badge.badge_id)

    def test_points_to_reward_flow(self):
        """Test earning points and redeeming a reward."""
        # Earn points
        self.points.award_points("user1", 500, "Initial grant")

        # Create and redeem reward
        reward = self.rewards.create_reward(
            name="Premium Theme",
            description="Unlock premium theme",
            cost=200,
            rarity=RewardRarity.UNCOMMON,
        )

        redemption = self.rewards.redeem_reward("user1", reward.reward_id, self.points)
        assert redemption.points_spent == 200
        assert self.points.get_balance("user1") == 300

    def test_leaderboard_with_points(self):
        """Test leaderboard reflects user points."""
        lb = self.leaderboards.create_leaderboard(
            name="Points Leaderboard",
            category=LeaderboardCategory.POINTS,
            time_window=LeaderboardTimeWindow.ALL_TIME,
        )

        self.points.award_points("user1", 100, "Test")
        self.points.award_points("user2", 200, "Test")
        self.points.award_points("user3", 150, "Test")

        self.leaderboards.submit_score(lb.leaderboard_id, "user1", self.points.get_balance("user1"))
        self.leaderboards.submit_score(lb.leaderboard_id, "user2", self.points.get_balance("user2"))
        self.leaderboards.submit_score(lb.leaderboard_id, "user3", self.points.get_balance("user3"))

        top = self.leaderboards.get_top_users(lb.leaderboard_id, count=1)
        assert top[0].user_id == "user2"

    def test_badge_tiers_progression(self):
        """Test earning badges across different tiers."""
        bronze = self.badges.register_badge(
            Badge(name="Bronze", description="Test", tier=BadgeTier.BRONZE)
        )
        silver = self.badges.register_badge(
            Badge(name="Silver", description="Test", tier=BadgeTier.SILVER)
        )
        gold = self.badges.register_badge(
            Badge(name="Gold", description="Test", tier=BadgeTier.GOLD)
        )

        self.badges.award_badge("user1", bronze.badge_id)
        self.badges.award_badge("user1", silver.badge_id)
        self.badges.award_badge("user1", gold.badge_id)

        assert self.badges.get_user_badge_count("user1") == 3
        assert len(self.badges.get_user_badges_by_tier("user1", BadgeTier.BRONZE)) == 1
        assert len(self.badges.get_user_badges_by_tier("user1", BadgeTier.SILVER)) == 1
        assert len(self.badges.get_user_badges_by_tier("user1", BadgeTier.GOLD)) == 1

    def test_multiple_users_competition(self):
        """Test multiple users competing on challenges and leaderboards."""
        lb = self.leaderboards.create_leaderboard(
            name="Competition",
            category=LeaderboardCategory.POINTS,
            time_window=LeaderboardTimeWindow.WEEKLY,
        )

        challenge = self.challenges.create_challenge(
            name="Speed Run",
            description="Complete tasks quickly",
            difficulty=ChallengeDifficulty.MEDIUM,
            points_reward=100,
        )

        # User 1 completes challenge
        self.challenges.start_challenge("user1", challenge.challenge_id)
        self.challenges.complete_challenge("user1", challenge.challenge_id)
        self.points.award_points("user1", 100, "Challenge complete")

        # User 2 completes challenge
        self.challenges.start_challenge("user2", challenge.challenge_id)
        self.challenges.complete_challenge("user2", challenge.challenge_id)
        self.points.award_points("user2", 100, "Challenge complete")

        # Submit to leaderboard
        self.leaderboards.submit_score(lb.leaderboard_id, "user1", 100)
        self.leaderboards.submit_score(lb.leaderboard_id, "user2", 100)

        rankings = self.leaderboards.get_rankings(lb.leaderboard_id)
        assert len(rankings) == 2
        assert rankings[0].score == 100
        assert rankings[1].score == 100

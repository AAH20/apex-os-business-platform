"""Reward system for gamification.

Rewards are items users can redeem with their points.
They have different rarities, costs, and availability.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Set


class RewardRarity(str, Enum):
    """Reward rarity levels."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


class RewardType(str, Enum):
    """Types of rewards."""

    DIGITAL = "digital"
    PHYSICAL = "physical"
    EXPERIENCE = "experience"
    DISCOUNT = "discount"
    CUSTOM = "custom"


@dataclass
class Reward:
    """Represents a reward that can be redeemed with points."""

    name: str
    description: str
    cost: int
    rarity: RewardRarity
    reward_type: RewardType = RewardType.DIGITAL
    reward_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    icon: str = "🎁"
    stock: Optional[int] = None  # None means unlimited
    max_per_user: Optional[int] = None  # None means unlimited
    is_active: bool = True
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Reward name cannot be empty")
        if self.cost < 0:
            raise ValueError("Reward cost cannot be negative")
        if self.stock is not None and self.stock < 0:
            raise ValueError("Reward stock cannot be negative")

    @property
    def is_available(self) -> bool:
        """Check if the reward is available for redemption."""
        if not self.is_active:
            return False
        if self.stock is not None and self.stock <= 0:
            return False
        return True

    @property
    def remaining_stock(self) -> Optional[int]:
        """Get remaining stock, None if unlimited."""
        return self.stock


@dataclass
class RewardRedemption:
    """A record of a reward being redeemed by a user."""

    user_id: str
    reward: Reward
    points_spent: int
    redemption_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    redeemed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"  # pending, fulfilled, cancelled, expired
    metadata: Dict[str, str] = field(default_factory=dict)


class RewardManager:
    """Manages rewards and redemptions."""

    def __init__(self) -> None:
        self._rewards: Dict[str, Reward] = {}
        self._redemptions: Dict[str, List[RewardRedemption]] = {}
        self._user_redemption_counts: Dict[str, Dict[str, int]] = {}  # user_id -> {reward_id -> count}

    def create_reward(
        self,
        name: str,
        description: str,
        cost: int,
        rarity: RewardRarity,
        reward_type: RewardType = RewardType.DIGITAL,
        icon: str = "🎁",
        stock: Optional[int] = None,
        max_per_user: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Reward:
        """Create a new reward."""
        reward = Reward(
            name=name,
            description=description,
            cost=cost,
            rarity=rarity,
            reward_type=reward_type,
            icon=icon,
            stock=stock,
            max_per_user=max_per_user,
            tags=tags or set(),
            metadata=metadata or {},
        )
        self._rewards[reward.reward_id] = reward
        return reward

    def get_reward(self, reward_id: str) -> Optional[Reward]:
        """Get a reward by ID."""
        return self._rewards.get(reward_id)

    def get_all_rewards(self) -> List[Reward]:
        """Get all rewards."""
        return list(self._rewards.values())

    def get_available_rewards(self) -> List[Reward]:
        """Get all currently available rewards."""
        return [r for r in self._rewards.values() if r.is_available]

    def get_rewards_by_rarity(self, rarity: RewardRarity) -> List[Reward]:
        """Get rewards filtered by rarity."""
        return [r for r in self._rewards.values() if r.rarity == rarity]

    def get_rewards_by_type(self, reward_type: RewardType) -> List[Reward]:
        """Get rewards filtered by type."""
        return [r for r in self._rewards.values() if r.reward_type == reward_type]

    def get_rewards_by_tag(self, tag: str) -> List[Reward]:
        """Get rewards filtered by tag."""
        return [r for r in self._rewards.values() if tag in r.tags]

    def get_affordable_rewards(self, points: int) -> List[Reward]:
        """Get rewards a user can afford with given points."""
        return [r for r in self.get_available_rewards() if r.cost <= points]

    def redeem_reward(
        self,
        user_id: str,
        reward_id: str,
        points_system,  # PointsSystem instance
    ) -> RewardRedemption:
        """Redeem a reward for a user.

        Args:
            user_id: The user redeeming the reward.
            reward_id: The reward to redeem.
            points_system: The PointsSystem to deduct points from.

        Returns:
            The RewardRedemption record.

        Raises:
            ValueError: If reward doesn't exist, is unavailable, user can't afford it,
                       or user has exceeded max redemptions.
        """
        reward = self._rewards.get(reward_id)
        if reward is None:
            raise ValueError(f"Reward {reward_id} not found")
        if not reward.is_available:
            raise ValueError(f"Reward {reward_id} is not available")

        # Check user's redemption count for this reward
        user_counts = self._user_redemption_counts.get(user_id, {})
        user_count = user_counts.get(reward_id, 0)
        if reward.max_per_user is not None and user_count >= reward.max_per_user:
            raise ValueError(
                f"User {user_id} has reached max redemptions for reward {reward_id}"
            )

        # Deduct points
        points_system.spend_points(
            user_id=user_id,
            amount=reward.cost,
            reason=f"Redeemed reward: {reward.name}",
            metadata={"reward_id": reward_id, "reward_name": reward.name},
        )

        # Decrease stock
        if reward.stock is not None:
            reward.stock -= 1

        # Track user redemption count
        if user_id not in self._user_redemption_counts:
            self._user_redemption_counts[user_id] = {}
        self._user_redemption_counts[user_id][reward_id] = user_count + 1

        # Create redemption record
        redemption = RewardRedemption(
            user_id=user_id,
            reward=reward,
            points_spent=reward.cost,
        )
        if user_id not in self._redemptions:
            self._redemptions[user_id] = []
        self._redemptions[user_id].append(redemption)

        return redemption

    def get_user_redemptions(
        self,
        user_id: str,
        status: Optional[str] = None,
    ) -> List[RewardRedemption]:
        """Get redemptions for a user, optionally filtered by status."""
        redemptions = self._redemptions.get(user_id, [])
        if status is not None:
            redemptions = [r for r in redemptions if r.status == status]
        return list(redemptions)

    def get_user_redemption_count(self, user_id: str, reward_id: str) -> int:
        """Get how many times a user has redeemed a specific reward."""
        user_counts = self._user_redemption_counts.get(user_id, {})
        return user_counts.get(reward_id, 0)

    def get_total_redemptions(self, reward_id: str) -> int:
        """Get total redemptions for a reward across all users."""
        total = 0
        for user_counts in self._user_redemption_counts.values():
            total += user_counts.get(reward_id, 0)
        return total

    def update_redemption_status(
        self,
        redemption_id: str,
        status: str,
    ) -> Optional[RewardRedemption]:
        """Update the status of a redemption."""
        for user_redemptions in self._redemptions.values():
            for redemption in user_redemptions:
                if redemption.redemption_id == redemption_id:
                    redemption.status = status
                    return redemption
        return None

    def cancel_redemption(
        self,
        redemption_id: str,
        points_system,  # PointsSystem instance
    ) -> Optional[RewardRedemption]:
        """Cancel a redemption and refund points.

        Returns:
            The updated redemption, or None if not found.
        """
        for user_id, user_redemptions in self._redemptions.items():
            for redemption in user_redemptions:
                if redemption.redemption_id == redemption_id:
                    if redemption.status != "pending":
                        raise ValueError(
                            f"Cannot cancel redemption with status {redemption.status}"
                        )

                    # Refund points
                    from apex_os_bp.gamification.points import PointsTransactionType
                    points_system.award_points(
                        user_id=user_id,
                        amount=redemption.points_spent,
                        reason=f"Refund for cancelled redemption: {redemption.reward.name}",
                        transaction_type=PointsTransactionType.ADJUSTMENT,
                        metadata={"redemption_id": redemption_id},
                    )

                    # Restore stock
                    if redemption.reward.stock is not None:
                        redemption.reward.stock += 1

                    # Decrement user redemption count
                    user_counts = self._user_redemption_counts.get(user_id, {})
                    reward_id = redemption.reward.reward_id
                    if reward_id in user_counts:
                        user_counts[reward_id] = max(0, user_counts[reward_id] - 1)

                    redemption.status = "cancelled"
                    return redemption
        return None

    def get_popular_rewards(self, limit: int = 10) -> List[Reward]:
        """Get the most redeemed rewards."""
        rewards_with_counts = [
            (r, self.get_total_redemptions(r.reward_id)) for r in self._rewards.values()
        ]
        rewards_with_counts.sort(key=lambda x: x[1], reverse=True)
        return [r for r, _ in rewards_with_counts[:limit]]

    def get_user_reward_history(self, user_id: str) -> List[RewardRedemption]:
        """Get all redemptions for a user, sorted by date descending."""
        redemptions = self._redemptions.get(user_id, [])
        return sorted(redemptions, key=lambda r: r.redeemed_at, reverse=True)

    def deactivate_reward(self, reward_id: str) -> None:
        """Deactivate a reward (stops new redemptions)."""
        reward = self._rewards.get(reward_id)
        if reward:
            reward.is_active = False

    def activate_reward(self, reward_id: str) -> None:
        """Activate a reward."""
        reward = self._rewards.get(reward_id)
        if reward:
            reward.is_active = True

    def restock_reward(self, reward_id: str, amount: int) -> None:
        """Add stock to a reward."""
        reward = self._rewards.get(reward_id)
        if reward is None:
            raise ValueError(f"Reward {reward_id} not found")
        if amount < 0:
            raise ValueError("Restock amount cannot be negative")
        if reward.stock is not None:
            reward.stock += amount

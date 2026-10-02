"""Points system for gamification.

Users earn points through actions, challenges, and achievements.
Points can be spent on rewards or tracked for leaderboards.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional


class PointsTransactionType(str, Enum):
    """Types of point transactions."""

    EARNED = "earned"
    SPENT = "spent"
    BONUS = "bonus"
    PENALTY = "penalty"
    ADJUSTMENT = "adjustment"


@dataclass
class PointsTransaction:
    """A single points transaction record."""

    user_id: str
    amount: int
    transaction_type: PointsTransactionType
    reason: str
    transaction_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount == 0:
            raise ValueError("Transaction amount cannot be zero")
        if self.transaction_type == PointsTransactionType.SPENT and self.amount > 0:
            raise ValueError("Spent transactions must have negative amount")
        if self.transaction_type == PointsTransactionType.EARNED and self.amount < 0:
            raise ValueError("Earned transactions must have positive amount")


class PointsSystem:
    """Manages user points: earning, spending, and tracking balances."""

    def __init__(self) -> None:
        self._balances: Dict[str, int] = {}
        self._transactions: Dict[str, List[PointsTransaction]] = {}

    def get_balance(self, user_id: str) -> int:
        """Get current points balance for a user."""
        return self._balances.get(user_id, 0)

    def award_points(
        self,
        user_id: str,
        amount: int,
        reason: str,
        transaction_type: PointsTransactionType = PointsTransactionType.EARNED,
        metadata: Optional[Dict[str, str]] = None,
    ) -> PointsTransaction:
        """Award points to a user.

        Args:
            user_id: The user to award points to.
            amount: Number of points (positive for earning, negative for spending).
            reason: Human-readable reason for the transaction.
            transaction_type: Type of transaction.
            metadata: Optional additional data.

        Returns:
            The created transaction record.

        Raises:
            ValueError: If amount is zero or user has insufficient points for spending.
        """
        if amount == 0:
            raise ValueError("Cannot award zero points")

        if transaction_type == PointsTransactionType.SPENT:
            current = self.get_balance(user_id)
            if current + amount < 0:
                raise ValueError(
                    f"Insufficient points: user has {current}, needs {abs(amount)}"
                )

        transaction = PointsTransaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type,
            reason=reason,
            metadata=metadata or {},
        )

        self._balances[user_id] = self.get_balance(user_id) + amount
        if user_id not in self._transactions:
            self._transactions[user_id] = []
        self._transactions[user_id].append(transaction)

        return transaction

    def spend_points(
        self,
        user_id: str,
        amount: int,
        reason: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> PointsTransaction:
        """Spend points from a user's balance.

        Args:
            user_id: The user spending points.
            amount: Number of points to spend (must be positive).
            reason: Human-readable reason for spending.
            metadata: Optional additional data.

        Returns:
            The created transaction record.

        Raises:
            ValueError: If amount is not positive or user has insufficient points.
        """
        if amount <= 0:
            raise ValueError("Spend amount must be positive")

        return self.award_points(
            user_id=user_id,
            amount=-amount,
            reason=reason,
            transaction_type=PointsTransactionType.SPENT,
            metadata=metadata,
        )

    def get_transactions(
        self,
        user_id: str,
        transaction_type: Optional[PointsTransactionType] = None,
    ) -> List[PointsTransaction]:
        """Get transaction history for a user, optionally filtered by type."""
        transactions = self._transactions.get(user_id, [])
        if transaction_type is not None:
            transactions = [t for t in transactions if t.transaction_type == transaction_type]
        return list(transactions)

    def get_transaction_history(self, user_id: str) -> List[PointsTransaction]:
        """Get all transactions for a user, sorted by timestamp descending."""
        transactions = self.get_transactions(user_id)
        return sorted(transactions, key=lambda t: t.timestamp, reverse=True)

    def adjust_points(
        self,
        user_id: str,
        amount: int,
        reason: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> PointsTransaction:
        """Admin adjustment to a user's points (can be positive or negative)."""
        return self.award_points(
            user_id=user_id,
            amount=amount,
            reason=reason,
            transaction_type=PointsTransactionType.ADJUSTMENT,
            metadata=metadata,
        )

    def get_total_earned(self, user_id: str) -> int:
        """Get total points ever earned by a user (excluding spent/adjustments)."""
        transactions = self.get_transactions(user_id, PointsTransactionType.EARNED)
        return sum(t.amount for t in transactions)

    def get_total_spent(self, user_id: str) -> int:
        """Get total points ever spent by a user."""
        transactions = self.get_transactions(user_id, PointsTransactionType.SPENT)
        return abs(sum(t.amount for t in transactions))

    def reset_user(self, user_id: str) -> None:
        """Reset a user's balance and clear their transaction history."""
        self._balances.pop(user_id, None)
        self._transactions.pop(user_id, None)

    def get_all_balances(self) -> Dict[str, int]:
        """Get all user balances."""
        return dict(self._balances)

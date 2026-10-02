#!/usr/bin/env python3
"""Demo: Gamification system — users, points, badges, leaderboards, rewards."""

from dataclasses import dataclass, field


@dataclass
class User:
    id: int
    name: str
    points: int = 0
    badges: list = field(default_factory=list)


@dataclass
class Badge:
    id: int
    name: str
    description: str


@dataclass
class Reward:
    id: int
    name: str
    cost: int


class GamificationEngine:
    def __init__(self):
        self.users: dict[int, User] = {}
        self.badges: dict[int, Badge] = {}
        self.rewards: dict[int, Reward] = {}
        self.leaderboard: list[tuple[str, int]] = []

    def create_user(self, user_id: int, name: str) -> User:
        user = User(id=user_id, name=name)
        self.users[user_id] = user
        print(f"[CREATE USER] Created user #{user_id}: {name}")
        return user

    def award_points(self, user_id: int, points: int, reason: str = "") -> None:
        user = self.users[user_id]
        user.points += points
        msg = f"[AWARD POINTS] {user.name} earned {points} pts"
        if reason:
            msg += f" — {reason}"
        msg += f" (total: {user.points})"
        print(msg)

    def assign_badge(self, user_id: int, badge_id: int) -> None:
        user = self.users[user_id]
        badge = self.badges[badge_id]
        user.badges.append(badge)
        print(f"[ASSIGN BADGE] {user.name} earned badge '{badge.name}' — {badge.description}")

    def update_leaderboard(self) -> None:
        self.leaderboard = sorted(
            ((u.name, u.points) for u in self.users.values()),
            key=lambda x: x[1],
            reverse=True,
        )
        print("[LEADERBOARD]")
        for rank, (name, pts) in enumerate(self.leaderboard, 1):
            print(f"  {rank}. {name} — {pts} pts")

    def grant_reward(self, user_id: int, reward_id: int) -> None:
        user = self.users[user_id]
        reward = self.rewards[reward_id]
        if user.points < reward.cost:
            print(f"[GRANT REWARD] {user.name} cannot afford '{reward.name}' "
                  f"(needs {reward.cost}, has {user.points})")
            return
        user.points -= reward.cost
        print(f"[GRANT REWARD] {user.name} redeemed '{reward.name}' for {reward.cost} pts "
              f"(remaining: {user.points})")


def main():
    engine = GamificationEngine()

    # Setup badges and rewards
    engine.badges[1] = Badge(1, "First Steps", "Completed your first task")
    engine.badges[2] = Badge(2, "High Achiever", "Reached 100 points")
    engine.rewards[1] = Reward(1, "Coffee Voucher", 50)
    engine.rewards[2] = Reward(2, "Extra Day Off", 200)

    print("=" * 50)
    print("  GAMIFICATION DEMO")
    print("=" * 50)

    # 1. Create users
    engine.create_user(1, "Alice")
    engine.create_user(2, "Bob")
    engine.create_user(3, "Carol")
    print()

    # 2. Award points
    engine.award_points(1, 30, "completed onboarding")
    engine.award_points(1, 75, "finished project milestone")
    engine.award_points(2, 50, "submitted weekly report")
    engine.award_points(3, 20, "attended training session")
    print()

    # 3. Assign badges
    engine.assign_badge(1, 1)
    engine.assign_badge(1, 2)
    engine.assign_badge(2, 1)
    print()

    # 4. Update leaderboard
    engine.update_leaderboard()
    print()

    # 5. Grant rewards
    engine.grant_reward(1, 1)
    engine.grant_reward(2, 2)
    engine.grant_reward(3, 1)
    print()

    print("=" * 50)
    print("  DEMO COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main()

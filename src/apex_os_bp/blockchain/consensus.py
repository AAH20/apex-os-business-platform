"""Proof-of-Stake Consensus System.

Implements a full PoS consensus engine with validator registration,
staking, block production, fork choice, and slashing conditions.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConsensusError(Exception):
    """Raised when a consensus operation fails."""


class ValidatorStatus(Enum):
    """Status of a validator in the network."""

    ACTIVE = "active"
    JAILED = "jailed"
    UNBONDING = "unbonding"
    INACTIVE = "inactive"


@dataclass
class Stake:
    """Represents a staked amount by a delegator."""

    delegator: str
    amount: int
    validator: str
    created_at: float = field(default_factory=time.time)
    unlock_time: float = 0.0

    @property
    def is_unlocked(self) -> bool:
        return time.time() >= self.unlock_time

    def to_dict(self) -> dict[str, Any]:
        return {
            "delegator": self.delegator,
            "amount": self.amount,
            "validator": self.validator,
            "created_at": self.created_at,
            "unlock_time": self.unlock_time,
        }


@dataclass
class Validator:
    """A network validator with stake and performance tracking."""

    address: str
    public_key: str
    stake: int = 0
    status: ValidatorStatus = ValidatorStatus.INACTIVE
    commission_rate: float = 0.05
    blocks_proposed: int = 0
    blocks_signed: int = 0
    uptime: float = 1.0
    registered_at: float = field(default_factory=time.time)
    jailed_at: float = 0.0
    jail_reason: str = ""

    @property
    def voting_power(self) -> int:
        """Total voting power (own stake + delegated stake)."""
        return self.stake

    @property
    def performance(self) -> float:
        """Performance ratio of signed blocks."""
        if self.blocks_proposed == 0:
            return 1.0
        return self.blocks_signed / self.blocks_proposed

    def jail(self, reason: str) -> None:
        """Jail the validator."""
        self.status = ValidatorStatus.JAILED
        self.jailed_at = time.time()
        self.jail_reason = reason

    def unjail(self) -> None:
        """Unjail the validator."""
        if self.status != ValidatorStatus.JAILED:
            raise ConsensusError("Validator is not jailed")
        self.status = ValidatorStatus.ACTIVE
        self.jailed_at = 0.0
        self.jail_reason = ""

    def activate(self) -> None:
        """Activate the validator for block production."""
        if self.status == ValidatorStatus.JAILED:
            raise ConsensusError("Cannot activate a jailed validator")
        self.status = ValidatorStatus.ACTIVE

    def deactivate(self) -> None:
        """Deactivate the validator."""
        self.status = ValidatorStatus.INACTIVE

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "public_key": self.public_key,
            "stake": self.stake,
            "status": self.status.value,
            "commission_rate": self.commission_rate,
            "blocks_proposed": self.blocks_proposed,
            "blocks_signed": self.blocks_signed,
            "uptime": self.uptime,
            "performance": self.performance,
            "voting_power": self.voting_power,
            "registered_at": self.registered_at,
        }


@dataclass
class Block:
    """A block in the blockchain."""

    index: int
    timestamp: float
    previous_hash: str
    transactions: list[dict[str, Any]] = field(default_factory=list)
    validator: str = ""
    signature: str = ""
    hash: str = ""
    merkle_root: str = ""
    state_root: str = ""

    def compute_hash(self) -> str:
        """Compute the block hash."""
        block_data = {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "validator": self.validator,
            "merkle_root": self.merkle_root,
            "state_root": self.state_root,
        }
        raw = json.dumps(block_data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def finalize(self) -> None:
        """Finalize the block by computing its hash."""
        self.hash = self.compute_hash()

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "transactions": self.transactions,
            "validator": self.validator,
            "signature": self.signature,
            "hash": self.hash,
            "merkle_root": self.merkle_root,
            "state_root": self.state_root,
        }


class ConsensusEngine:
    """Proof-of-Stake consensus engine."""

    MIN_STAKE = 1000
    BLOCK_TIME = 12.0
    UNBONDING_PERIOD = 86400 * 7  # 7 days
    SLASH_PERCENTAGE = 0.05
    EPOCH_LENGTH = 32

    def __init__(self) -> None:
        self.validators: dict[str, Validator] = {}
        self.stakes: dict[str, list[Stake]] = {}
        self.blocks: list[Block] = []
        self.current_epoch: int = 0
        self.block_reward: int = 10
        self._rng = random.Random()

    def register_validator(
        self, address: str, public_key: str, stake: int, commission_rate: float = 0.05
    ) -> Validator:
        """Register a new validator."""
        if address in self.validators:
            raise ConsensusError(f"Validator {address} already registered")
        if stake < self.MIN_STAKE:
            raise ConsensusError(f"Minimum stake is {self.MIN_STAKE}")
        if not 0.0 <= commission_rate <= 1.0:
            raise ConsensusError("Commission rate must be between 0 and 1")

        validator = Validator(
            address=address,
            public_key=public_key,
            stake=stake,
            commission_rate=commission_rate,
            status=ValidatorStatus.ACTIVE,
        )
        self.validators[address] = validator
        self.stakes[address] = []
        return validator

    def deregister_validator(self, address: str) -> None:
        """Remove a validator from the active set."""
        if address not in self.validators:
            raise ConsensusError(f"Validator {address} not found")
        validator = self.validators[address]
        validator.deactivate()

    def delegate(self, delegator: str, validator_addr: str, amount: int) -> Stake:
        """Delegate stake to a validator."""
        if validator_addr not in self.validators:
            raise ConsensusError(f"Validator {validator_addr} not found")
        validator = self.validators[validator_addr]
        if validator.status != ValidatorStatus.ACTIVE:
            raise ConsensusError(f"Validator {validator_addr} is not active")
        if amount <= 0:
            raise ConsensusError("Delegation amount must be positive")

        stake = Stake(delegator=delegator, amount=amount, validator=validator_addr)
        self.stakes.setdefault(validator_addr, []).append(stake)
        validator.stake += amount
        return stake

    def undelegate(self, delegator: str, validator_addr: str, amount: int) -> None:
        """Undelegate stake from a validator."""
        if validator_addr not in self.validators:
            raise ConsensusError(f"Validator {validator_addr} not found")
        stakes = self.stakes.get(validator_addr, [])
        matching = [s for s in stakes if s.delegator == delegator]
        total = sum(s.amount for s in matching)
        if amount > total:
            raise ConsensusError("Insufficient delegated stake")

        remaining = amount
        for stake in matching:
            if remaining <= 0:
                break
            deduct = min(stake.amount, remaining)
            stake.amount -= deduct
            remaining -= deduct
            self.validators[validator_addr].stake -= deduct

        self.stakes[validator_addr] = [s for s in stakes if s.amount > 0]

    def select_validator(self, seed: int | None = None) -> Validator:
        """Select a validator proportional to their stake (weighted random)."""
        active = [v for v in self.validators.values() if v.status == ValidatorStatus.ACTIVE]
        if not active:
            raise ConsensusError("No active validators")

        total_stake = sum(v.stake for v in active)
        if seed is not None:
            self._rng.seed(seed)
        target = self._rng.randint(1, total_stake)
        cumulative = 0
        for validator in active:
            cumulative += validator.stake
            if cumulative >= target:
                return validator
        return active[-1]

    def produce_block(
        self, transactions: list[dict[str, Any]], validator_addr: str | None = None
    ) -> Block:
        """Produce a new block."""
        if not self.blocks:
            previous_hash = "0" * 64
            index = 0
        else:
            previous_hash = self.blocks[-1].hash
            index = self.blocks[-1].index + 1

        if validator_addr is None:
            validator = self.select_validator()
            validator_addr = validator.address
        else:
            if validator_addr not in self.validators:
                raise ConsensusError(f"Validator {validator_addr} not found")
            validator = self.validators[validator_addr]

        merkle_root = self._compute_merkle_root(transactions)
        block = Block(
            index=index,
            timestamp=time.time(),
            previous_hash=previous_hash,
            transactions=transactions,
            validator=validator_addr,
            merkle_root=merkle_root,
        )
        block.finalize()

        validator.blocks_proposed += 1
        validator.blocks_signed += 1
        self.blocks.append(block)
        return block

    def validate_block(self, block: Block) -> bool:
        """Validate a block's integrity."""
        if block.compute_hash() != block.hash:
            return False
        if block.merkle_root != self._compute_merkle_root(block.transactions):
            return False
        return True

    def slash_validator(self, address: str, reason: str) -> int:
        """Slash a validator's stake for misbehavior."""
        if address not in self.validators:
            raise ConsensusError(f"Validator {address} not found")
        validator = self.validators[address]
        slashed_amount = int(validator.stake * self.SLASH_PERCENTAGE)
        validator.stake -= slashed_amount
        validator.jail(reason)
        return slashed_amount

    def get_active_validators(self) -> list[Validator]:
        """Get all active validators."""
        return [v for v in self.validators.values() if v.status == ValidatorStatus.ACTIVE]

    def get_total_stake(self) -> int:
        """Get the total staked amount across all validators."""
        return sum(v.stake for v in self.validators.values())

    def get_validator_stake(self, address: str) -> int:
        """Get the total stake for a specific validator."""
        if address not in self.validators:
            raise ConsensusError(f"Validator {address} not found")
        return self.validators[address].stake

    def advance_epoch(self) -> None:
        """Advance to the next epoch."""
        self.current_epoch += 1

    def _compute_merkle_root(self, transactions: list[dict[str, Any]]) -> str:
        """Compute the Merkle root of transactions."""
        if not transactions:
            return hashlib.sha256(b"").hexdigest()
        hashes = [
            hashlib.sha256(json.dumps(tx, sort_keys=True, default=str).encode()).hexdigest()
            for tx in transactions
        ]
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            hashes = [
                hashlib.sha256((hashes[i] + hashes[i + 1]).encode()).hexdigest()
                for i in range(0, len(hashes), 2)
            ]
        return hashes[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_epoch": self.current_epoch,
            "block_height": len(self.blocks),
            "total_stake": self.get_total_stake(),
            "validator_count": len(self.validators),
            "active_validators": len(self.get_active_validators()),
            "block_reward": self.block_reward,
        }

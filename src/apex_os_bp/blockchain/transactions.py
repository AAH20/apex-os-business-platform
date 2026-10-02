"""Transaction Tracking System.

Provides a full transaction lifecycle: creation, signing, validation,
mempool management, execution, and historical tracking with indexing.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TransactionError(Exception):
    """Raised when a transaction operation fails."""


class TransactionStatus(Enum):
    """Lifecycle status of a transaction."""

    PENDING = "pending"
    VALIDATED = "validated"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERTED = "reverted"


class TransactionType(Enum):
    """Types of transactions."""

    TRANSFER = "transfer"
    CONTRACT_CALL = "contract_call"
    CONTRACT_DEPLOY = "contract_deploy"
    TOKEN_MINT = "token_mint"
    TOKEN_BURN = "token_burn"
    TOKEN_TRANSFER = "token_transfer"
    STAKE = "stake"
    UNSTAKE = "unstake"
    GOVERNANCE = "governance"


@dataclass
class Transaction:
    """A blockchain transaction."""

    sender: str
    receiver: str
    amount: int
    tx_type: TransactionType = TransactionType.TRANSFER
    nonce: int = 0
    gas_price: int = 1
    gas_limit: int = 21000
    data: dict[str, Any] = field(default_factory=dict)
    signature: str = ""
    hash: str = ""
    status: TransactionStatus = TransactionStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    block_number: int = 0
    gas_used: int = 0
    fee: int = 0
    logs: list[dict[str, Any]] = field(default_factory=list)
    error: str = ""

    def compute_hash(self) -> str:
        """Compute the transaction hash."""
        tx_data = {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "tx_type": self.tx_type.value,
            "nonce": self.nonce,
            "gas_price": self.gas_price,
            "gas_limit": self.gas_limit,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        raw = json.dumps(tx_data, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def finalize(self) -> None:
        """Finalize the transaction by computing its hash."""
        self.hash = self.compute_hash()

    def sign(self, private_key: str) -> None:
        """Sign the transaction with a private key."""
        if not self.hash:
            self.finalize()
        signature_data = f"{self.hash}:{private_key}"
        self.signature = hashlib.sha256(signature_data.encode()).hexdigest()

    def verify_signature(self, public_key: str) -> bool:
        """Verify the transaction signature."""
        if not self.signature:
            return False
        expected_data = f"{self.hash}:{public_key}"
        expected = hashlib.sha256(expected_data.encode()).hexdigest()
        return self.signature == expected

    def estimate_gas(self) -> int:
        """Estimate gas cost for this transaction."""
        base = 21000
        if self.tx_type == TransactionType.CONTRACT_CALL:
            base += 10000
        elif self.tx_type == TransactionType.CONTRACT_DEPLOY:
            base += 50000
        elif self.tx_type in (TransactionType.TOKEN_MINT, TransactionType.TOKEN_BURN):
            base += 15000
        data_size = len(json.dumps(self.data))
        base += data_size * 100
        return base

    def calculate_fee(self) -> int:
        """Calculate the transaction fee."""
        return self.gas_used * self.gas_price

    def to_dict(self) -> dict[str, Any]:
        return {
            "hash": self.hash,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "tx_type": self.tx_type.value,
            "nonce": self.nonce,
            "gas_price": self.gas_price,
            "gas_limit": self.gas_limit,
            "data": self.data,
            "signature": self.signature,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "block_number": self.block_number,
            "gas_used": self.gas_used,
            "fee": self.fee,
            "logs": self.logs,
            "error": self.error,
        }


class TransactionPool:
    """Mempool for pending transactions."""

    def __init__(self, max_size: int = 10000) -> None:
        self._pool: dict[str, Transaction] = {}
        self._max_size = max_size
        self._nonce_tracker: dict[str, int] = {}

    def add_transaction(self, tx: Transaction) -> None:
        """Add a transaction to the mempool."""
        if not tx.hash:
            tx.finalize()
        if len(self._pool) >= self._max_size:
            raise TransactionError("Transaction pool is full")
        if tx.hash in self._pool:
            raise TransactionError("Transaction already in pool")

        sender_nonce = self._nonce_tracker.get(tx.sender, 0)
        if tx.nonce < sender_nonce:
            raise TransactionError("Transaction nonce too low")

        self._pool[tx.hash] = tx
        self._nonce_tracker[tx.sender] = max(sender_nonce, tx.nonce + 1)

    def remove_transaction(self, tx_hash: str) -> Transaction | None:
        """Remove and return a transaction from the pool."""
        return self._pool.pop(tx_hash, None)

    def get_transaction(self, tx_hash: str) -> Transaction | None:
        """Get a transaction by hash."""
        return self._pool.get(tx_hash)

    def get_pending(self, limit: int | None = None) -> list[Transaction]:
        """Get pending transactions ordered by gas price (highest first)."""
        txs = sorted(self._pool.values(), key=lambda t: t.gas_price, reverse=True)
        if limit is not None:
            return txs[:limit]
        return txs

    def get_pending_for_sender(self, sender: str) -> list[Transaction]:
        """Get pending transactions for a specific sender."""
        return [tx for tx in self._pool.values() if tx.sender == sender]

    def get_nonce_for_sender(self, sender: str) -> int:
        """Get the next expected nonce for a sender."""
        return self._nonce_tracker.get(sender, 0)

    def size(self) -> int:
        """Get the number of transactions in the pool."""
        return len(self._pool)

    def clear(self) -> None:
        """Clear all transactions from the pool."""
        self._pool.clear()
        self._nonce_tracker.clear()


class TransactionTracker:
    """Tracks all transactions with indexing and querying capabilities."""

    def __init__(self) -> None:
        self._transactions: dict[str, Transaction] = {}
        self._by_sender: dict[str, list[str]] = {}
        self._by_receiver: dict[str, list[str]] = {}
        self._by_block: dict[int, list[str]] = {}
        self._by_type: dict[str, list[str]] = {}
        self._by_status: dict[str, list[str]] = {}

    def add_transaction(self, tx: Transaction) -> None:
        """Index a transaction."""
        if not tx.hash:
            tx.finalize()
        self._transactions[tx.hash] = tx

        self._by_sender.setdefault(tx.sender, []).append(tx.hash)
        self._by_receiver.setdefault(tx.receiver, []).append(tx.hash)
        self._by_block.setdefault(tx.block_number, []).append(tx.hash)
        self._by_type.setdefault(tx.tx_type.value, []).append(tx.hash)
        self._by_status.setdefault(tx.status.value, []).append(tx.hash)

    def get_transaction(self, tx_hash: str) -> Transaction | None:
        """Get a transaction by hash."""
        return self._transactions.get(tx_hash)

    def update_status(
        self, tx_hash: str, status: TransactionStatus, block_number: int = 0, gas_used: int = 0
    ) -> None:
        """Update the status of a transaction."""
        tx = self._transactions.get(tx_hash)
        if tx is None:
            raise TransactionError(f"Transaction {tx_hash} not found")

        old_status = tx.status.value
        if old_status in self._by_status:
            self._by_status[old_status] = [h for h in self._by_status[old_status] if h != tx_hash]

        tx.status = status
        tx.block_number = block_number
        tx.gas_used = gas_used
        tx.fee = tx.calculate_fee()
        self._by_status.setdefault(status.value, []).append(tx.hash)

    def get_by_sender(self, sender: str) -> list[Transaction]:
        """Get all transactions from a sender."""
        hashes = self._by_sender.get(sender, [])
        return [self._transactions[h] for h in hashes if h in self._transactions]

    def get_by_receiver(self, receiver: str) -> list[Transaction]:
        """Get all transactions to a receiver."""
        hashes = self._by_receiver.get(receiver, [])
        return [self._transactions[h] for h in hashes if h in self._transactions]

    def get_by_block(self, block_number: int) -> list[Transaction]:
        """Get all transactions in a block."""
        hashes = self._by_block.get(block_number, [])
        return [self._transactions[h] for h in hashes if h in self._transactions]

    def get_by_type(self, tx_type: TransactionType) -> list[Transaction]:
        """Get all transactions of a specific type."""
        hashes = self._by_type.get(tx_type.value, [])
        return [self._transactions[h] for h in hashes if h in self._transactions]

    def get_by_status(self, status: TransactionStatus) -> list[Transaction]:
        """Get all transactions with a specific status."""
        hashes = self._by_status.get(status.value, [])
        return [self._transactions[h] for h in hashes if h in self._transactions]

    def get_all(self) -> list[Transaction]:
        """Get all tracked transactions."""
        return list(self._transactions.values())

    def get_count(self) -> int:
        """Get the total number of tracked transactions."""
        return len(self._transactions)

    def search(
        self,
        sender: str | None = None,
        receiver: str | None = None,
        tx_type: TransactionType | None = None,
        status: TransactionStatus | None = None,
        min_amount: int | None = None,
        max_amount: int | None = None,
    ) -> list[Transaction]:
        """Search transactions with filters."""
        results = list(self._transactions.values())

        if sender is not None:
            results = [tx for tx in results if tx.sender == sender]
        if receiver is not None:
            results = [tx for tx in results if tx.receiver == receiver]
        if tx_type is not None:
            results = [tx for tx in results if tx.tx_type == tx_type]
        if status is not None:
            results = [tx for tx in results if tx.status == status]
        if min_amount is not None:
            results = [tx for tx in results if tx.amount >= min_amount]
        if max_amount is not None:
            results = [tx for tx in results if tx.amount <= max_amount]

        return results

    def get_total_volume(self) -> int:
        """Get the total volume of all confirmed transactions."""
        confirmed = self.get_by_status(TransactionStatus.CONFIRMED)
        return sum(tx.amount for tx in confirmed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_transactions": self.get_count(),
            "total_volume": self.get_total_volume(),
            "by_status": {
                status: len(txs) for status, txs in self._by_status.items()
            },
        }

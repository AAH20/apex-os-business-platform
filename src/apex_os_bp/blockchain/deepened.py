"""Deepened blockchain module: smart contracts, tokens, consensus, bridge, analytics."""
from __future__ import annotations
import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


# ── 1. Smart Contract Deployment ──────────────────────────────────────────────

@dataclass
class SmartContract:
    address: str
    bytecode: str
    state: dict[str, Any] = field(default_factory=dict)
    owner: str = ""
    created_at: float = field(default_factory=time.time)

    def execute(self, method: str, **kwargs) -> Any:
        handler = getattr(self, f"_{method}", None)
        if handler is None:
            raise ValueError(f"Unknown method: {method}")
        return handler(**kwargs)

    def _transfer(self, sender: str, recipient: str, amount: int) -> dict:
        if self.state.get(sender, 0) < amount:
            raise ValueError("Insufficient balance")
        self.state[sender] -= amount
        self.state[recipient] = self.state.get(recipient, 0) + amount
        return {"from": sender, "to": recipient, "amount": amount}


class ContractRegistry:
    def __init__(self):
        self._contracts: dict[str, SmartContract] = {}

    def deploy(self, bytecode: str, owner: str = "", initial_state: dict | None = None) -> SmartContract:
        addr = "0x" + hashlib.sha256(f"{bytecode}{time.time()}".encode()).hexdigest()[:40]
        contract = SmartContract(address=addr, bytecode=bytecode, owner=owner,
                                 state=initial_state or {})
        self._contracts[addr] = contract
        return contract

    def get(self, address: str) -> SmartContract | None:
        return self._contracts.get(address)

    def list_contracts(self) -> list[SmartContract]:
        return list(self._contracts.values())


# ── 2. Token Management (ERC-20) ──────────────────────────────────────────────

@dataclass
class ERC20Token:
    name: str
    symbol: str
    decimals: int = 18
    total_supply: int = 0
    balances: dict[str, int] = field(default_factory=dict)
    allowances: dict[str, dict[str, int]] = field(default_factory=dict)

    def mint(self, to: str, amount: int) -> None:
        self.balances[to] = self.balances.get(to, 0) + amount
        self.total_supply += amount

    def burn(self, from_: str, amount: int) -> None:
        if self.balances.get(from_, 0) < amount:
            raise ValueError("Insufficient balance to burn")
        self.balances[from_] -= amount
        self.total_supply -= amount

    def transfer(self, sender: str, recipient: str, amount: int) -> bool:
        if self.balances.get(sender, 0) < amount:
            return False
        self.balances[sender] -= amount
        self.balances[recipient] = self.balances.get(recipient, 0) + amount
        return True

    def approve(self, owner: str, spender: str, amount: int) -> None:
        self.allowances.setdefault(owner, {})[spender] = amount

    def transfer_from(self, spender: str, sender: str, recipient: str, amount: int) -> bool:
        allowed = self.allowances.get(sender, {}).get(spender, 0)
        if allowed < amount or self.balances.get(sender, 0) < amount:
            return False
        self.allowances[sender][spender] -= amount
        self.balances[sender] -= amount
        self.balances[recipient] = self.balances.get(recipient, 0) + amount
        return True

    def balance_of(self, account: str) -> int:
        return self.balances.get(account, 0)


# ── 3. Consensus Mechanism (PBFT) ─────────────────────────────────────────────

@dataclass
class PBFTMessage:
    view: int
    sequence: int
    digest: str
    node_id: str
    type: str  # PRE-PREPARE, PREPARE, COMMIT
    timestamp: float = field(default_factory=time.time)


class PBFTConsensus:
    def __init__(self, node_id: str, nodes: list[str], f: int = 1):
        self.node_id = node_id
        self.nodes = nodes
        self.f = f  # max faulty nodes
        self.view = 0
        self.sequence = 0
        self.log: dict[int, PBFTMessage] = {}
        self.prepared: set[int] = set()
        self.committed: set[int] = set()

    def _quorum(self) -> int:
        return 2 * self.f + 1

    def propose(self, block_hash: str) -> PBFTMessage:
        self.sequence += 1
        msg = PBFTMessage(self.view, self.sequence, block_hash, self.node_id, "PRE-PREPARE")
        self.log[self.sequence] = msg
        return msg

    def handle_prepare(self, msg: PBFTMessage) -> bool:
        if msg.sequence in self.prepared:
            return True
        self.prepared.add(msg.sequence)
        return len(self.prepared) >= self._quorum()

    def handle_commit(self, msg: PBFTMessage) -> bool:
        if msg.sequence in self.committed:
            return True
        self.committed.add(msg.sequence)
        return len(self.committed) >= self._quorum()

    def is_finalized(self, sequence: int) -> bool:
        return sequence in self.committed


# ── 4. Cross-Chain Bridge ─────────────────────────────────────────────────────

@dataclass
class BridgeLock:
    tx_hash: str
    source_chain: str
    target_chain: str
    sender: str
    recipient: str
    amount: int
    status: str = "locked"  # locked, minted, released
    created_at: float = field(default_factory=time.time)


class CrossChainBridge:
    def __init__(self):
        self._locks: dict[str, BridgeLock] = {}
        self._chains: set[str] = set()

    def register_chain(self, chain_id: str) -> None:
        self._chains.add(chain_id)

    def lock(self, tx_hash: str, source: str, target: str, sender: str,
             recipient: str, amount: int) -> BridgeLock:
        lock = BridgeLock(tx_hash, source, target, sender, recipient, amount)
        self._locks[tx_hash] = lock
        return lock

    def mint_wrapped(self, tx_hash: str) -> BridgeLock:
        lock = self._locks.get(tx_hash)
        if not lock or lock.status != "locked":
            raise ValueError("Invalid or already processed lock")
        lock.status = "minted"
        return lock

    def release(self, tx_hash: str) -> BridgeLock:
        lock = self._locks.get(tx_hash)
        if not lock:
            raise ValueError("Lock not found")
        lock.status = "released"
        return lock

    def get_pending(self) -> list[BridgeLock]:
        return [l for l in self._locks.values() if l.status == "locked"]


# ── 5. Blockchain Analytics ──────────────────────────────────────────────────

@dataclass
class TransactionRecord:
    tx_hash: str
    sender: str
    recipient: str
    amount: int
    fee: int
    block_number: int
    timestamp: float = field(default_factory=time.time)


class BlockchainAnalytics:
    def __init__(self):
        self._txs: dict[str, TransactionRecord] = {}
        self._block_txs: dict[int, list[str]] = {}

    def record(self, tx: TransactionRecord) -> None:
        self._txs[tx.tx_hash] = tx
        self._block_txs.setdefault(tx.block_number, []).append(tx.tx_hash)

    def get_transaction(self, tx_hash: str) -> TransactionRecord | None:
        return self._txs.get(tx_hash)

    def get_block_transactions(self, block_number: int) -> list[TransactionRecord]:
        return [self._txs[h] for h in self._block_txs.get(block_number, [])]

    def total_volume(self) -> int:
        return sum(tx.amount for tx in self._txs.values())

    def total_fees(self) -> int:
        return sum(tx.fee for tx in self._txs.values())

    def address_volume(self, address: str) -> int:
        return sum(tx.amount for tx in self._txs.values()
                   if tx.sender == address or tx.recipient == address)

    def average_tx_amount(self) -> float:
        if not self._txs:
            return 0.0
        return self.total_volume() / len(self._txs)

    def transaction_count(self) -> int:
        return len(self._txs)

"""Smart Contract System.

Provides a sandboxed execution environment for deploying and invoking
smart contracts with event logging, state management, and access control.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class ContractError(Exception):
    """Raised when a contract operation fails."""


class ContractState(Enum):
    """Lifecycle states for a smart contract."""

    CREATED = "created"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


@dataclass
class ContractEvent:
    """An event emitted by a smart contract."""

    name: str
    data: dict[str, Any]
    contract_address: str
    timestamp: float = field(default_factory=time.time)
    block_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data": self.data,
            "contract_address": self.contract_address,
            "timestamp": self.timestamp,
            "block_number": self.block_number,
        }


@dataclass
class Contract:
    """A deployed smart contract with state and callable methods."""

    address: str
    owner: str
    code: str
    state: dict[str, Any] = field(default_factory=dict)
    status: ContractState = ContractState.CREATED
    events: list[ContractEvent] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    block_number: int = 0
    _methods: dict[str, Callable[..., Any]] = field(default_factory=dict, repr=False)

    def register_method(self, name: str, func: Callable[..., Any]) -> None:
        """Register a callable method on this contract."""
        self._methods[name] = func

    def call(self, method_name: str, caller: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a contract method with access control."""
        if self.status == ContractState.TERMINATED:
            raise ContractError(f"Contract {self.address} is terminated")
        if self.status == ContractState.PAUSED:
            raise ContractError(f"Contract {self.address} is paused")
        if method_name not in self._methods:
            raise ContractError(f"Method '{method_name}' not found on contract {self.address}")

        func = self._methods[method_name]
        result = func(self, caller, *args, **kwargs)
        return result

    def emit_event(self, name: str, data: dict[str, Any]) -> ContractEvent:
        """Emit an event from this contract."""
        event = ContractEvent(
            name=name,
            data=data,
            contract_address=self.address,
            block_number=self.block_number,
        )
        self.events.append(event)
        return event

    def get_state(self, key: str, default: Any = None) -> Any:
        """Read a value from contract storage."""
        return self.state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        """Write a value to contract storage."""
        self.state[key] = value

    def pause(self) -> None:
        """Pause the contract, preventing further calls."""
        if self.status == ContractState.TERMINATED:
            raise ContractError("Cannot pause a terminated contract")
        self.status = ContractState.PAUSED

    def resume(self) -> None:
        """Resume a paused contract."""
        if self.status == ContractState.TERMINATED:
            raise ContractError("Cannot resume a terminated contract")
        self.status = ContractState.ACTIVE

    def terminate(self) -> None:
        """Permanently terminate the contract."""
        self.status = ContractState.TERMINATED

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "owner": self.owner,
            "code": self.code,
            "state": self.state,
            "status": self.status.value,
            "created_at": self.created_at,
            "block_number": self.block_number,
            "event_count": len(self.events),
        }


class ContractEngine:
    """Manages deployment, execution, and lifecycle of smart contracts."""

    def __init__(self) -> None:
        self._contracts: dict[str, Contract] = {}
        self._nonce: int = 0

    def _generate_address(self, owner: str) -> str:
        """Generate a unique contract address."""
        self._nonce += 1
        raw = f"{owner}:{self._nonce}:{time.time()}"
        return "0x" + hashlib.sha256(raw.encode()).hexdigest()[:40]

    def deploy(self, owner: str, code: str, initial_state: dict[str, Any] | None = None) -> Contract:
        """Deploy a new smart contract."""
        address = self._generate_address(owner)
        contract = Contract(
            address=address,
            owner=owner,
            code=code,
            state=initial_state or {},
            status=ContractState.ACTIVE,
        )
        self._contracts[address] = contract
        return contract

    def get_contract(self, address: str) -> Contract:
        """Retrieve a contract by address."""
        if address not in self._contracts:
            raise ContractError(f"Contract {address} not found")
        return self._contracts[address]

    def call_contract(
        self, address: str, method_name: str, caller: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Call a method on a deployed contract."""
        contract = self.get_contract(address)
        return contract.call(method_name, caller, *args, **kwargs)

    def list_contracts(self, owner: str | None = None) -> list[Contract]:
        """List all contracts, optionally filtered by owner."""
        contracts = list(self._contracts.values())
        if owner is not None:
            contracts = [c for c in contracts if c.owner == owner]
        return contracts

    def get_events(self, address: str | None = None) -> list[ContractEvent]:
        """Get all events, optionally filtered by contract address."""
        if address is not None:
            contract = self.get_contract(address)
            return list(contract.events)
        all_events: list[ContractEvent] = []
        for contract in self._contracts.values():
            all_events.extend(contract.events)
        return sorted(all_events, key=lambda e: e.timestamp)

    def set_block_number(self, block_number: int) -> None:
        """Update the current block number for all contracts."""
        for contract in self._contracts.values():
            contract.block_number = block_number

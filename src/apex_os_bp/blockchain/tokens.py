"""Token Management System.

Supports fungible tokens (ERC-20 style) and non-fungible tokens (ERC-721 style)
with minting, burning, transfers, allowances, and metadata.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TokenError(Exception):
    """Raised when a token operation fails."""


class TokenType(Enum):
    """Types of tokens supported."""

    FUNGIBLE = "fungible"
    NON_FUNGIBLE = "non_fungible"


@dataclass
class TokenBalance:
    """Represents a balance entry for an account."""

    account: str
    balance: int = 0
    locked: int = 0

    @property
    def available(self) -> int:
        return self.balance - self.locked

    def to_dict(self) -> dict[str, Any]:
        return {
            "account": self.account,
            "balance": self.balance,
            "locked": self.locked,
            "available": self.available,
        }


@dataclass
class Token:
    """A token with supply tracking and balance management."""

    address: str
    name: str
    symbol: str
    token_type: TokenType
    total_supply: int = 0
    max_supply: int | None = None
    decimals: int = 18
    owner: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    balances: dict[str, TokenBalance] = field(default_factory=dict)
    allowances: dict[str, dict[str, int]] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    paused: bool = False

    def _get_balance(self, account: str) -> TokenBalance:
        if account not in self.balances:
            self.balances[account] = TokenBalance(account=account)
        return self.balances[account]

    def mint(self, to: str, amount: int, minter: str | None = None) -> None:
        """Mint new tokens to an account."""
        if self.paused:
            raise TokenError("Token is paused")
        if amount <= 0:
            raise TokenError("Mint amount must be positive")
        if self.max_supply is not None and self.total_supply + amount > self.max_supply:
            raise TokenError("Mint would exceed max supply")

        balance = self._get_balance(to)
        balance.balance += amount
        self.total_supply += amount

    def burn(self, from_: str, amount: int) -> None:
        """Burn tokens from an account."""
        if self.paused:
            raise TokenError("Token is paused")
        if amount <= 0:
            raise TokenError("Burn amount must be positive")
        balance = self._get_balance(from_)
        if balance.available < amount:
            raise TokenError("Insufficient balance to burn")
        balance.balance -= amount
        self.total_supply -= amount

    def transfer(self, from_: str, to: str, amount: int) -> None:
        """Transfer tokens between accounts."""
        if self.paused:
            raise TokenError("Token is paused")
        if amount <= 0:
            raise TokenError("Transfer amount must be positive")
        if from_ == to:
            raise TokenError("Cannot transfer to self")

        sender = self._get_balance(from_)
        if sender.available < amount:
            raise TokenError("Insufficient balance")

        sender.balance -= amount
        receiver = self._get_balance(to)
        receiver.balance += amount

    def approve(self, owner: str, spender: str, amount: int) -> None:
        """Approve a spender to transfer tokens on behalf of owner."""
        if self.paused:
            raise TokenError("Token is paused")
        if amount <= 0:
            raise TokenError("Approval amount must be positive")
        if owner not in self.allowances:
            self.allowances[owner] = {}
        self.allowances[owner][spender] = amount

    def transfer_from(self, spender: str, from_: str, to: str, amount: int) -> None:
        """Transfer tokens using an allowance."""
        if self.paused:
            raise TokenError("Token is paused")
        if amount <= 0:
            raise TokenError("Transfer amount must be positive")

        allowed = self.allowances.get(from_, {}).get(spender, 0)
        if allowed < amount:
            raise TokenError("Allowance exceeded")

        sender = self._get_balance(from_)
        if sender.available < amount:
            raise TokenError("Insufficient balance")

        sender.balance -= amount
        receiver = self._get_balance(to)
        receiver.balance += amount
        self.allowances[from_][spender] -= amount

    def lock(self, account: str, amount: int) -> None:
        """Lock tokens, making them unavailable for transfer."""
        balance = self._get_balance(account)
        if balance.available < amount:
            raise TokenError("Insufficient available balance to lock")
        balance.locked += amount

    def unlock(self, account: str, amount: int) -> None:
        """Unlock previously locked tokens."""
        balance = self._get_balance(account)
        if balance.locked < amount:
            raise TokenError("Insufficient locked balance to unlock")
        balance.locked -= amount

    def balance_of(self, account: str) -> int:
        """Get the total balance of an account."""
        return self._get_balance(account).balance

    def available_balance_of(self, account: str) -> int:
        """Get the available (unlocked) balance of an account."""
        return self._get_balance(account).available

    def allowance(self, owner: str, spender: str) -> int:
        """Get the remaining allowance for a spender."""
        return self.allowances.get(owner, {}).get(spender, 0)

    def pause(self) -> None:
        """Pause all token operations."""
        self.paused = True

    def unpause(self) -> None:
        """Unpause token operations."""
        self.paused = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "name": self.name,
            "symbol": self.symbol,
            "token_type": self.token_type.value,
            "total_supply": self.total_supply,
            "max_supply": self.max_supply,
            "decimals": self.decimals,
            "owner": self.owner,
            "metadata": self.metadata,
            "paused": self.paused,
            "created_at": self.created_at,
        }


class TokenRegistry:
    """Registry for managing multiple tokens."""

    def __init__(self) -> None:
        self._tokens: dict[str, Token] = {}
        self._nonce: int = 0

    def _generate_address(self, symbol: str) -> str:
        self._nonce += 1
        raw = f"{symbol}:{self._nonce}:{time.time()}"
        return "0x" + hashlib.sha256(raw.encode()).hexdigest()[:40]

    def create_token(
        self,
        name: str,
        symbol: str,
        token_type: TokenType = TokenType.FUNGIBLE,
        max_supply: int | None = None,
        decimals: int = 18,
        owner: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Token:
        """Create and register a new token."""
        address = self._generate_address(symbol)
        token = Token(
            address=address,
            name=name,
            symbol=symbol,
            token_type=token_type,
            max_supply=max_supply,
            decimals=decimals,
            owner=owner,
            metadata=metadata or {},
        )
        self._tokens[address] = token
        return token

    def get_token(self, address: str) -> Token:
        """Retrieve a token by address."""
        if address not in self._tokens:
            raise TokenError(f"Token {address} not found")
        return self._tokens[address]

    def list_tokens(self) -> list[Token]:
        """List all registered tokens."""
        return list(self._tokens.values())

    def get_tokens_by_owner(self, owner: str) -> list[Token]:
        """List all tokens owned by an address."""
        return [t for t in self._tokens.values() if t.owner == owner]

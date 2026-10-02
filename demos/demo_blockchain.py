#!/usr/bin/env python3
"""Blockchain demo: wallet, transaction, verification, contract deploy/query.

Self-contained — uses only stdlib (hashlib, json, time, os).
Run: python3 demos/demo_blockchain.py
"""

import hashlib
import json
import os
import time


def sha256(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


class Wallet:
    def __init__(self, name: str):
        self.name = name
        self.private_key = sha256(f"{name}-{os.urandom(16).hex()}")
        self.address = sha256(self.private_key)[:40]
        self.balance = 100.0

    def sign(self, data: str) -> str:
        return sha256(f"{self.private_key}:{data}")

    def __repr__(self):
        return f"Wallet({self.name}, addr={self.address[:12]}…, bal={self.balance})"


class Transaction:
    def __init__(self, sender: Wallet, recipient: str, amount: float):
        self.sender = sender.address
        self.recipient = recipient
        self.amount = amount
        self.timestamp = time.time()
        self.signature = sender.sign(f"{sender.address}:{recipient}:{amount}:{self.timestamp}")

    def verify(self, private_key: str) -> bool:
        data = f"{self.sender}:{self.recipient}:{self.amount}:{self.timestamp}"
        expected = sha256(f"{private_key}:{data}")
        return self.signature == expected

    def to_dict(self):
        return {
            "sender": self.sender[:12] + "…",
            "recipient": self.recipient[:12] + "…",
            "amount": self.amount,
            "signature": self.signature[:16] + "…",
        }


class SmartContract:
    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code
        self.state = {}
        self.address = sha256(f"{name}:{code}")[:40]

    def execute(self, method: str, **kwargs):
        if method == "set":
            self.state[kwargs["key"]] = kwargs["value"]
            return f"set {kwargs['key']}={kwargs['value']}"
        if method == "get":
            return self.state.get(kwargs["key"], None)
        return f"unknown method: {method}"


def demo_create_wallet():
    print("=" * 50)
    print("1. CREATE WALLET")
    print("=" * 50)
    w = Wallet("alice")
    print(f"  Name:       {w.name}")
    print(f"  Address:    {w.address}")
    print(f"  Balance:    {w.balance} APEX")
    print(f"  Private key: {w.private_key[:16]}… (kept secret)")
    return w


def demo_create_transaction(wallet: Wallet):
    print("\n" + "=" * 50)
    print("2. CREATE TRANSACTION")
    print("=" * 50)
    recipient = sha256("bob")[:40]
    tx = Transaction(wallet, recipient, 25.0)
    print(f"  From:    {tx.sender[:12]}…")
    print(f"  To:      {tx.recipient[:12]}…")
    print(f"  Amount:  {tx.amount} APEX")
    print(f"  Signed:  {tx.signature[:16]}…")
    return tx


def demo_verify_transaction(tx: Transaction, wallet: Wallet):
    print("\n" + "=" * 50)
    print("3. VERIFY TRANSACTION")
    print("=" * 50)
    valid = tx.verify(wallet.private_key)
    print(f"  Signature valid: {valid}")
    # Tamper test
    tx.amount = 999.0
    print(f"  After tamper (amount→999): {tx.verify(wallet.private_key)}")
    return valid


def demo_deploy_contract():
    print("\n" + "=" * 50)
    print("4. DEPLOY CONTRACT")
    print("=" * 50)
    code = "def set(k,v): state[k]=v\ndef get(k): return state[k]"
    contract = SmartContract("SimpleStorage", code)
    print(f"  Name:    {contract.name}")
    print(f"  Address: {contract.address}")
    print(f"  Code:    {contract.code[:40]}…")
    return contract


def demo_query_contract(contract: SmartContract):
    print("\n" + "=" * 50)
    print("5. QUERY CONTRACT")
    print("=" * 50)
    print(f"  Execute set('greeting', 'hello chain'): {contract.execute('set', key='greeting', value='hello chain')}")
    print(f"  Execute get('greeting'):              {contract.execute('get', key='greeting')}")
    print(f"  Execute get('missing'):               {contract.execute('get', key='missing')}")
    print(f"  Final state: {contract.state}")


def main():
    print("APEX-OS Blockchain Demo")
    wallet = demo_create_wallet()
    tx = demo_create_transaction(wallet)
    demo_verify_transaction(tx, wallet)
    contract = demo_deploy_contract()
    demo_query_contract(contract)
    print("\n" + "=" * 50)
    print("Demo complete.")


if __name__ == "__main__":
    main()

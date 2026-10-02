"""Comprehensive tests for the APEX-OS Blockchain System."""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from apex_os_bp.blockchain.contracts import (
    Contract,
    ContractEngine,
    ContractEvent,
    ContractError,
    ContractState,
)
from apex_os_bp.blockchain.tokens import (
    Token,
    TokenRegistry,
    TokenBalance,
    TokenError,
    TokenType,
)
from apex_os_bp.blockchain.consensus import (
    ConsensusEngine,
    Validator,
    Block,
    Stake,
    ConsensusError,
    ValidatorStatus,
)
from apex_os_bp.blockchain.wallet import (
    Wallet,
    WalletManager,
    KeyPair,
    WalletError,
)
from apex_os_bp.blockchain.transactions import (
    Transaction,
    TransactionPool,
    TransactionStatus,
    TransactionType,
    TransactionTracker,
    TransactionError,
)


# =============================================================================
# Smart Contract Tests
# =============================================================================


class TestSmartContracts:
    """Tests for the smart contract system."""

    def test_deploy_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1", {"count": 0})
        assert contract.address.startswith("0x")
        assert contract.owner == "owner1"
        assert contract.status == ContractState.ACTIVE
        assert contract.state == {"count": 0}

    def test_get_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        retrieved = engine.get_contract(contract.address)
        assert retrieved.address == contract.address

    def test_get_nonexistent_contract(self):
        engine = ContractEngine()
        with pytest.raises(ContractError):
            engine.get_contract("0xnonexistent")

    def test_call_contract_method(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")

        def increment(contract, caller, amount=1):
            current = contract.get_state("count", 0)
            contract.set_state("count", current + amount)
            return current + amount

        contract.register_method("increment", increment)
        result = engine.call_contract(contract.address, "increment", "caller1", amount=5)
        assert result == 5
        assert contract.get_state("count") == 5

    def test_call_nonexistent_method(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        with pytest.raises(ContractError):
            engine.call_contract(contract.address, "nonexistent", "caller1")

    def test_call_paused_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")

        def noop(contract, caller):
            return True

        contract.register_method("noop", noop)
        contract.pause()
        with pytest.raises(ContractError):
            engine.call_contract(contract.address, "noop", "caller1")

    def test_call_terminated_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")

        def noop(contract, caller):
            return True

        contract.register_method("noop", noop)
        contract.terminate()
        with pytest.raises(ContractError):
            engine.call_contract(contract.address, "noop", "caller1")

    def test_pause_resume_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        contract.pause()
        assert contract.status == ContractState.PAUSED
        contract.resume()
        assert contract.status == ContractState.ACTIVE

    def test_terminate_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        contract.terminate()
        assert contract.status == ContractState.TERMINATED

    def test_cannot_pause_terminated_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        contract.terminate()
        with pytest.raises(ContractError):
            contract.pause()

    def test_cannot_resume_terminated_contract(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        contract.terminate()
        with pytest.raises(ContractError):
            contract.resume()

    def test_emit_event(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        event = contract.emit_event("Transfer", {"from": "a", "to": "b", "amount": 100})
        assert event.name == "Transfer"
        assert event.data["amount"] == 100
        assert event.contract_address == contract.address
        assert len(contract.events) == 1

    def test_get_events(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        contract.emit_event("Event1", {"x": 1})
        contract.emit_event("Event2", {"y": 2})
        events = engine.get_events(contract.address)
        assert len(events) == 2

    def test_list_contracts(self):
        engine = ContractEngine()
        engine.deploy("owner1", "code1")
        engine.deploy("owner1", "code2")
        engine.deploy("owner2", "code3")
        assert len(engine.list_contracts()) == 3
        assert len(engine.list_contracts("owner1")) == 2
        assert len(engine.list_contracts("owner2")) == 1

    def test_set_block_number(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1")
        engine.set_block_number(42)
        assert contract.block_number == 42

    def test_contract_to_dict(self):
        engine = ContractEngine()
        contract = engine.deploy("owner1", "code1", {"key": "value"})
        d = contract.to_dict()
        assert d["owner"] == "owner1"
        assert d["state"] == {"key": "value"}
        assert d["status"] == "active"

    def test_multiple_contracts_unique_addresses(self):
        engine = ContractEngine()
        addresses = set()
        for i in range(10):
            contract = engine.deploy(f"owner{i}", f"code{i}")
            addresses.add(contract.address)
        assert len(addresses) == 10


# =============================================================================
# Token Management Tests
# =============================================================================


class TestTokenManagement:
    """Tests for the token management system."""

    def test_create_fungible_token(self):
        registry = TokenRegistry()
        token = registry.create_token("Test Token", "TEST", TokenType.FUNGIBLE, max_supply=1000000)
        assert token.name == "Test Token"
        assert token.symbol == "TEST"
        assert token.token_type == TokenType.FUNGIBLE
        assert token.max_supply == 1000000
        assert token.total_supply == 0

    def test_create_non_fungible_token(self):
        registry = TokenRegistry()
        token = registry.create_token("NFT Token", "NFT", TokenType.NON_FUNGIBLE)
        assert token.token_type == TokenType.NON_FUNGIBLE

    def test_mint_tokens(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 1000)
        assert token.total_supply == 1000
        assert token.balance_of("account1") == 1000

    def test_mint_exceeds_max_supply(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST", max_supply=100)
        with pytest.raises(TokenError):
            token.mint("account1", 101)

    def test_mint_zero_amount(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        with pytest.raises(TokenError):
            token.mint("account1", 0)

    def test_burn_tokens(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 1000)
        token.burn("account1", 300)
        assert token.total_supply == 700
        assert token.balance_of("account1") == 700

    def test_burn_insufficient_balance(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 100)
        with pytest.raises(TokenError):
            token.burn("account1", 101)

    def test_transfer_tokens(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 1000)
        token.transfer("account1", "account2", 400)
        assert token.balance_of("account1") == 600
        assert token.balance_of("account2") == 400

    def test_transfer_insufficient_balance(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 100)
        with pytest.raises(TokenError):
            token.transfer("account1", "account2", 101)

    def test_transfer_to_self(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 100)
        with pytest.raises(TokenError):
            token.transfer("account1", "account1", 50)

    def test_approve_and_transfer_from(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 1000)
        token.approve("account1", "spender", 500)
        assert token.allowance("account1", "spender") == 500
        token.transfer_from("spender", "account1", "account2", 300)
        assert token.balance_of("account1") == 700
        assert token.balance_of("account2") == 300
        assert token.allowance("account1", "spender") == 200

    def test_transfer_from_exceeds_allowance(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 1000)
        token.approve("account1", "spender", 100)
        with pytest.raises(TokenError):
            token.transfer_from("spender", "account1", "account2", 101)

    def test_lock_tokens(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 1000)
        token.lock("account1", 400)
        assert token.balance_of("account1") == 1000
        assert token.available_balance_of("account1") == 600

    def test_unlock_tokens(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 1000)
        token.lock("account1", 400)
        token.unlock("account1", 200)
        assert token.available_balance_of("account1") == 800

    def test_lock_insufficient_balance(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint("account1", 100)
        with pytest.raises(TokenError):
            token.lock("account1", 101)

    def test_pause_unpause_token(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.pause()
        with pytest.raises(TokenError):
            token.mint("account1", 100)
        token.unpause()
        token.mint("account1", 100)
        assert token.balance_of("account1") == 100

    def test_get_token(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        retrieved = registry.get_token(token.address)
        assert retrieved.address == token.address

    def test_get_nonexistent_token(self):
        registry = TokenRegistry()
        with pytest.raises(TokenError):
            registry.get_token("0xnonexistent")

    def test_list_tokens(self):
        registry = TokenRegistry()
        registry.create_token("Token1", "TK1")
        registry.create_token("Token2", "TK2")
        assert len(registry.list_tokens()) == 2

    def test_get_tokens_by_owner(self):
        registry = TokenRegistry()
        registry.create_token("Token1", "TK1", owner="owner1")
        registry.create_token("Token2", "TK2", owner="owner1")
        registry.create_token("Token3", "TK3", owner="owner2")
        assert len(registry.get_tokens_by_owner("owner1")) == 2
        assert len(registry.get_tokens_by_owner("owner2")) == 1

    def test_token_to_dict(self):
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST", TokenType.FUNGIBLE, max_supply=1000)
        d = token.to_dict()
        assert d["name"] == "Test"
        assert d["symbol"] == "TST"
        assert d["max_supply"] == 1000

    def test_token_balance_available(self):
        balance = TokenBalance(account="acc1", balance=1000, locked=300)
        assert balance.available == 700

    def test_token_balance_to_dict(self):
        balance = TokenBalance(account="acc1", balance=1000, locked=300)
        d = balance.to_dict()
        assert d["balance"] == 1000
        assert d["locked"] == 300
        assert d["available"] == 700


# =============================================================================
# Consensus Tests
# =============================================================================


class TestConsensus:
    """Tests for the Proof-of-Stake consensus system."""

    def test_register_validator(self):
        engine = ConsensusEngine()
        validator = engine.register_validator("val1", "pubkey1", 5000)
        assert validator.address == "val1"
        assert validator.stake == 5000
        assert validator.status == ValidatorStatus.ACTIVE

    def test_register_duplicate_validator(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        with pytest.raises(ConsensusError):
            engine.register_validator("val1", "pubkey2", 3000)

    def test_register_below_min_stake(self):
        engine = ConsensusEngine()
        with pytest.raises(ConsensusError):
            engine.register_validator("val1", "pubkey1", 500)

    def test_register_invalid_commission(self):
        engine = ConsensusEngine()
        with pytest.raises(ConsensusError):
            engine.register_validator("val1", "pubkey1", 5000, commission_rate=1.5)

    def test_deregister_validator(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.deregister_validator("val1")
        assert engine.validators["val1"].status == ValidatorStatus.INACTIVE

    def test_delegate(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        stake = engine.delegate("delegator1", "val1", 2000)
        assert stake.amount == 2000
        assert engine.validators["val1"].stake == 7000

    def test_delegate_to_inactive_validator(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.deregister_validator("val1")
        with pytest.raises(ConsensusError):
            engine.delegate("delegator1", "val1", 1000)

    def test_delegate_zero_amount(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        with pytest.raises(ConsensusError):
            engine.delegate("delegator1", "val1", 0)

    def test_undelegate(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.delegate("delegator1", "val1", 2000)
        engine.undelegate("delegator1", "val1", 1000)
        assert engine.validators["val1"].stake == 6000

    def test_undelegate_insufficient(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.delegate("delegator1", "val1", 1000)
        with pytest.raises(ConsensusError):
            engine.undelegate("delegator1", "val1", 2000)

    def test_select_validator(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.register_validator("val2", "pubkey2", 5000)
        selected = engine.select_validator(seed=42)
        assert selected.address in ("val1", "val2")

    def test_select_validator_no_active(self):
        engine = ConsensusEngine()
        with pytest.raises(ConsensusError):
            engine.select_validator()

    def test_produce_block(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        txs = [{"from": "a", "to": "b", "amount": 100}]
        block = engine.produce_block(txs)
        assert block.index == 0
        assert len(block.transactions) == 1
        assert block.hash != ""
        assert len(engine.blocks) == 1

    def test_produce_multiple_blocks(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        for i in range(5):
            engine.produce_block([{"tx": i}])
        assert len(engine.blocks) == 5
        assert engine.blocks[-1].index == 4

    def test_validate_block(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        block = engine.produce_block([])
        assert engine.validate_block(block) is True

    def test_validate_invalid_block(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        block = engine.produce_block([])
        block.hash = "invalid"
        assert engine.validate_block(block) is False

    def test_slash_validator(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        slashed = engine.slash_validator("val1", "double_sign")
        assert slashed == 250  # 5% of 5000
        assert engine.validators["val1"].stake == 4750
        assert engine.validators["val1"].status == ValidatorStatus.JAILED

    def test_jail_unjail_validator(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.slash_validator("val1", "misbehavior")
        assert engine.validators["val1"].status == ValidatorStatus.JAILED
        engine.validators["val1"].unjail()
        assert engine.validators["val1"].status == ValidatorStatus.ACTIVE

    def test_unjail_non_jailed_validator(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        with pytest.raises(ConsensusError):
            engine.validators["val1"].unjail()

    def test_get_active_validators(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.register_validator("val2", "pubkey2", 3000)
        engine.deregister_validator("val2")
        active = engine.get_active_validators()
        assert len(active) == 1
        assert active[0].address == "val1"

    def test_get_total_stake(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.register_validator("val2", "pubkey2", 3000)
        assert engine.get_total_stake() == 8000

    def test_get_validator_stake(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        assert engine.get_validator_stake("val1") == 5000

    def test_advance_epoch(self):
        engine = ConsensusEngine()
        assert engine.current_epoch == 0
        engine.advance_epoch()
        assert engine.current_epoch == 1

    def test_compute_merkle_root(self):
        engine = ConsensusEngine()
        txs = [{"a": 1}, {"b": 2}, {"c": 3}]
        root = engine._compute_merkle_root(txs)
        assert len(root) == 64

    def test_compute_merkle_root_empty(self):
        engine = ConsensusEngine()
        root = engine._compute_merkle_root([])
        assert len(root) == 64

    def test_block_to_dict(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        block = engine.produce_block([{"tx": 1}])
        d = block.to_dict()
        assert d["index"] == 0
        assert d["validator"] == "val1"
        assert "hash" in d

    def test_validator_to_dict(self):
        engine = ConsensusEngine()
        validator = engine.register_validator("val1", "pubkey1", 5000)
        d = validator.to_dict()
        assert d["address"] == "val1"
        assert d["stake"] == 5000
        assert d["status"] == "active"

    def test_consensus_to_dict(self):
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        d = engine.to_dict()
        assert d["validator_count"] == 1
        assert d["total_stake"] == 5000

    def test_stake_to_dict(self):
        stake = Stake(delegator="del1", amount=1000, validator="val1")
        d = stake.to_dict()
        assert d["delegator"] == "del1"
        assert d["amount"] == 1000

    def test_validator_performance(self):
        engine = ConsensusEngine()
        v = engine.register_validator("val1", "pubkey1", 5000)
        v.blocks_proposed = 10
        v.blocks_signed = 8
        assert v.performance == 0.8

    def test_validator_voting_power(self):
        engine = ConsensusEngine()
        v = engine.register_validator("val1", "pubkey1", 5000)
        assert v.voting_power == 5000


# =============================================================================
# Wallet Tests
# =============================================================================


class TestWallet:
    """Tests for the HD wallet management system."""

    def test_create_wallet(self):
        manager = WalletManager()
        wallet = manager.create_wallet(label="test")
        assert wallet.mnemonic != ""
        assert wallet.seed != ""
        assert wallet.master_key != ""
        assert wallet.label == "test"

    def test_create_wallet_with_mnemonic(self):
        manager = WalletManager()
        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        wallet = manager.create_wallet(mnemonic=mnemonic)
        assert wallet.mnemonic == mnemonic

    def test_import_wallet(self):
        manager = WalletManager()
        mnemonic = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        wallet = manager.import_wallet(mnemonic, label="imported")
        assert wallet.mnemonic == mnemonic
        assert wallet.label == "imported"

    def test_create_account(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        account = wallet.create_account()
        assert account.address.startswith("0x")
        assert account.index == 0
        assert len(wallet.accounts) == 1

    def test_create_multiple_accounts(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        acc1 = wallet.create_account()
        acc2 = wallet.create_account()
        assert acc1.index == 0
        assert acc2.index == 1
        assert acc1.address != acc2.address

    def test_get_account(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        account = wallet.create_account()
        retrieved = wallet.get_account(account.address)
        assert retrieved.address == account.address

    def test_get_nonexistent_account(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        with pytest.raises(WalletError):
            wallet.get_account("0xnonexistent")

    def test_list_accounts(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        wallet.create_account()
        wallet.create_account()
        assert len(wallet.list_accounts()) == 2

    def test_sign_and_verify(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        account = wallet.create_account()
        message = "Hello, Blockchain!"
        signature = wallet.sign(account.address, message)
        assert wallet.verify(account.address, message, signature) is True

    def test_verify_invalid_signature(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        account = wallet.create_account()
        assert wallet.verify(account.address, "message", "invalid_sig") is False

    def test_verify_wrong_message(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        account = wallet.create_account()
        signature = wallet.sign(account.address, "message1")
        assert wallet.verify(account.address, "message2", signature) is False

    def test_export_public(self):
        manager = WalletManager()
        wallet = manager.create_wallet(label="test")
        wallet.create_account()
        exported = wallet.export_public()
        assert exported["label"] == "test"
        assert exported["address_count"] == 1
        assert "accounts" in exported

    def test_get_wallet(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        retrieved = manager.get_wallet(wallet.seed)
        assert retrieved.seed == wallet.seed

    def test_get_nonexistent_wallet(self):
        manager = WalletManager()
        with pytest.raises(WalletError):
            manager.get_wallet("nonexistent_seed")

    def test_list_wallets(self):
        manager = WalletManager()
        manager.create_wallet(label="w1")
        manager.create_wallet(label="w2")
        assert len(manager.list_wallets()) == 2

    def test_delete_wallet(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        manager.delete_wallet(wallet.seed)
        assert len(manager.list_wallets()) == 0

    def test_delete_nonexistent_wallet(self):
        manager = WalletManager()
        with pytest.raises(WalletError):
            manager.delete_wallet("nonexistent")

    def test_generate_address(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        address = manager.generate_address(wallet.seed)
        assert address.startswith("0x")
        assert address in wallet.accounts

    def test_wallet_to_dict(self):
        manager = WalletManager()
        wallet = manager.create_wallet(label="test")
        wallet.create_account()
        d = wallet.to_dict()
        assert d["label"] == "test"
        assert d["address_count"] == 1

    def test_mnemonic_uniqueness(self):
        manager = WalletManager()
        mnemonics = set()
        for _ in range(10):
            wallet = manager.create_wallet()
            mnemonics.add(wallet.mnemonic)
        assert len(mnemonics) == 10

    def test_keypair_to_dict(self):
        manager = WalletManager()
        wallet = manager.create_wallet()
        account = wallet.create_account()
        d = account.to_dict()
        assert "address" in d
        assert "public_key" in d
        assert "index" in d


# =============================================================================
# Transaction Tests
# =============================================================================


class TestTransactions:
    """Tests for the transaction tracking system."""

    def test_create_transaction(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        assert tx.sender == "alice"
        assert tx.receiver == "bob"
        assert tx.amount == 100
        assert tx.status == TransactionStatus.PENDING

    def test_transaction_hash(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tx.finalize()
        assert len(tx.hash) == 64

    def test_transaction_hash_consistency(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        hash1 = tx.compute_hash()
        hash2 = tx.compute_hash()
        assert hash1 == hash2

    def test_sign_transaction(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tx.sign("private_key_123")
        assert tx.signature != ""

    def test_verify_signature(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tx.sign("private_key_123")
        assert tx.verify_signature("private_key_123") is True

    def test_verify_invalid_signature(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tx.sign("private_key_123")
        assert tx.verify_signature("wrong_key") is False

    def test_estimate_gas_transfer(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        gas = tx.estimate_gas()
        assert gas >= 21000

    def test_estimate_gas_contract_call(self):
        tx = Transaction(
            sender="alice",
            receiver="contract",
            amount=0,
            tx_type=TransactionType.CONTRACT_CALL,
        )
        gas = tx.estimate_gas()
        assert gas > 21000

    def test_estimate_gas_contract_deploy(self):
        tx = Transaction(
            sender="alice",
            receiver="",
            amount=0,
            tx_type=TransactionType.CONTRACT_DEPLOY,
        )
        gas = tx.estimate_gas()
        assert gas > 30000

    def test_calculate_fee(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100, gas_price=2)
        tx.gas_used = 21000
        assert tx.calculate_fee() == 42000

    def test_transaction_to_dict(self):
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tx.finalize()
        d = tx.to_dict()
        assert d["sender"] == "alice"
        assert d["receiver"] == "bob"
        assert d["amount"] == 100
        assert d["status"] == "pending"


class TestTransactionPool:
    """Tests for the transaction mempool."""

    def test_add_transaction(self):
        pool = TransactionPool()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        pool.add_transaction(tx)
        assert pool.size() == 1

    def test_add_duplicate_transaction(self):
        pool = TransactionPool()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        pool.add_transaction(tx)
        with pytest.raises(TransactionError):
            pool.add_transaction(tx)

    def test_add_to_full_pool(self):
        pool = TransactionPool(max_size=1)
        tx1 = Transaction(sender="alice", receiver="bob", amount=100)
        tx2 = Transaction(sender="charlie", receiver="dave", amount=200)
        pool.add_transaction(tx1)
        with pytest.raises(TransactionError):
            pool.add_transaction(tx2)

    def test_remove_transaction(self):
        pool = TransactionPool()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        pool.add_transaction(tx)
        removed = pool.remove_transaction(tx.hash)
        assert removed is not None
        assert pool.size() == 0

    def test_remove_nonexistent_transaction(self):
        pool = TransactionPool()
        assert pool.remove_transaction("nonexistent") is None

    def test_get_transaction(self):
        pool = TransactionPool()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        pool.add_transaction(tx)
        retrieved = pool.get_transaction(tx.hash)
        assert retrieved is not None
        assert retrieved.sender == "alice"

    def test_get_pending(self):
        pool = TransactionPool()
        tx1 = Transaction(sender="alice", receiver="bob", amount=100, gas_price=1)
        tx2 = Transaction(sender="charlie", receiver="dave", amount=200, gas_price=5)
        pool.add_transaction(tx1)
        pool.add_transaction(tx2)
        pending = pool.get_pending()
        assert len(pending) == 2
        assert pending[0].gas_price == 5  # Higher gas price first

    def test_get_pending_with_limit(self):
        pool = TransactionPool()
        for i in range(5):
            tx = Transaction(sender=f"sender{i}", receiver="bob", amount=100)
            pool.add_transaction(tx)
        pending = pool.get_pending(limit=3)
        assert len(pending) == 3

    def test_get_pending_for_sender(self):
        pool = TransactionPool()
        tx1 = Transaction(sender="alice", receiver="bob", amount=100, nonce=0)
        tx2 = Transaction(sender="alice", receiver="charlie", amount=200, nonce=1)
        tx3 = Transaction(sender="bob", receiver="alice", amount=50)
        pool.add_transaction(tx1)
        pool.add_transaction(tx2)
        pool.add_transaction(tx3)
        alice_txs = pool.get_pending_for_sender("alice")
        assert len(alice_txs) == 2

    def test_get_nonce_for_sender(self):
        pool = TransactionPool()
        tx = Transaction(sender="alice", receiver="bob", amount=100, nonce=0)
        pool.add_transaction(tx)
        assert pool.get_nonce_for_sender("alice") == 1

    def test_nonce_too_low(self):
        pool = TransactionPool()
        tx1 = Transaction(sender="alice", receiver="bob", amount=100, nonce=5)
        pool.add_transaction(tx1)
        tx2 = Transaction(sender="alice", receiver="charlie", amount=200, nonce=3)
        with pytest.raises(TransactionError):
            pool.add_transaction(tx2)

    def test_clear_pool(self):
        pool = TransactionPool()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        pool.add_transaction(tx)
        pool.clear()
        assert pool.size() == 0


class TestTransactionTracker:
    """Tests for the transaction tracker."""

    def test_add_transaction(self):
        tracker = TransactionTracker()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tracker.add_transaction(tx)
        assert tracker.get_count() == 1

    def test_get_transaction(self):
        tracker = TransactionTracker()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tracker.add_transaction(tx)
        retrieved = tracker.get_transaction(tx.hash)
        assert retrieved is not None
        assert retrieved.sender == "alice"

    def test_get_nonexistent_transaction(self):
        tracker = TransactionTracker()
        assert tracker.get_transaction("nonexistent") is None

    def test_update_status(self):
        tracker = TransactionTracker()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tracker.add_transaction(tx)
        tracker.update_status(tx.hash, TransactionStatus.CONFIRMED, block_number=1, gas_used=21000)
        assert tx.status == TransactionStatus.CONFIRMED
        assert tx.block_number == 1
        assert tx.gas_used == 21000

    def test_update_status_nonexistent(self):
        tracker = TransactionTracker()
        with pytest.raises(TransactionError):
            tracker.update_status("nonexistent", TransactionStatus.CONFIRMED)

    def test_get_by_sender(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="alice", receiver="bob", amount=100)
        tx2 = Transaction(sender="alice", receiver="charlie", amount=200)
        tx3 = Transaction(sender="bob", receiver="alice", amount=50)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        tracker.add_transaction(tx3)
        alice_txs = tracker.get_by_sender("alice")
        assert len(alice_txs) == 2

    def test_get_by_receiver(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="alice", receiver="bob", amount=100)
        tx2 = Transaction(sender="charlie", receiver="bob", amount=200)
        tx3 = Transaction(sender="bob", receiver="alice", amount=50)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        tracker.add_transaction(tx3)
        bob_txs = tracker.get_by_receiver("bob")
        assert len(bob_txs) == 2

    def test_get_by_block(self):
        tracker = TransactionTracker()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tx.block_number = 5
        tracker.add_transaction(tx)
        block_txs = tracker.get_by_block(5)
        assert len(block_txs) == 1

    def test_get_by_type(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="a", receiver="b", amount=100, tx_type=TransactionType.TRANSFER)
        tx2 = Transaction(sender="c", receiver="d", amount=0, tx_type=TransactionType.CONTRACT_CALL)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        transfers = tracker.get_by_type(TransactionType.TRANSFER)
        assert len(transfers) == 1

    def test_get_by_status(self):
        tracker = TransactionTracker()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tracker.add_transaction(tx)
        tracker.update_status(tx.hash, TransactionStatus.CONFIRMED)
        confirmed = tracker.get_by_status(TransactionStatus.CONFIRMED)
        assert len(confirmed) == 1

    def test_get_all(self):
        tracker = TransactionTracker()
        for i in range(5):
            tx = Transaction(sender=f"sender{i}", receiver="bob", amount=100)
            tracker.add_transaction(tx)
        assert len(tracker.get_all()) == 5

    def test_search_by_sender(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="alice", receiver="bob", amount=100)
        tx2 = Transaction(sender="charlie", receiver="bob", amount=200)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        results = tracker.search(sender="alice")
        assert len(results) == 1

    def test_search_by_amount_range(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="a", receiver="b", amount=50)
        tx2 = Transaction(sender="c", receiver="d", amount=150)
        tx3 = Transaction(sender="e", receiver="f", amount=250)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        tracker.add_transaction(tx3)
        results = tracker.search(min_amount=100, max_amount=200)
        assert len(results) == 1
        assert results[0].amount == 150

    def test_search_by_type(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="a", receiver="b", amount=100, tx_type=TransactionType.TRANSFER)
        tx2 = Transaction(sender="c", receiver="d", amount=0, tx_type=TransactionType.CONTRACT_DEPLOY)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        results = tracker.search(tx_type=TransactionType.TRANSFER)
        assert len(results) == 1

    def test_search_combined_filters(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="alice", receiver="bob", amount=100, tx_type=TransactionType.TRANSFER)
        tx2 = Transaction(sender="alice", receiver="charlie", amount=200, tx_type=TransactionType.CONTRACT_CALL)
        tx3 = Transaction(sender="bob", receiver="alice", amount=150, tx_type=TransactionType.TRANSFER)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        tracker.add_transaction(tx3)
        results = tracker.search(sender="alice", tx_type=TransactionType.TRANSFER)
        assert len(results) == 1
        assert results[0].amount == 100

    def test_get_total_volume(self):
        tracker = TransactionTracker()
        tx1 = Transaction(sender="a", receiver="b", amount=100)
        tx2 = Transaction(sender="c", receiver="d", amount=200)
        tracker.add_transaction(tx1)
        tracker.add_transaction(tx2)
        tracker.update_status(tx1.hash, TransactionStatus.CONFIRMED)
        tracker.update_status(tx2.hash, TransactionStatus.CONFIRMED)
        assert tracker.get_total_volume() == 300

    def test_tracker_to_dict(self):
        tracker = TransactionTracker()
        tx = Transaction(sender="alice", receiver="bob", amount=100)
        tracker.add_transaction(tx)
        d = tracker.to_dict()
        assert d["total_transactions"] == 1
        assert "by_status" in d


# =============================================================================
# Integration Tests
# =============================================================================


class TestBlockchainIntegration:
    """Integration tests combining multiple blockchain components."""

    def test_full_transaction_lifecycle(self):
        """Test a complete transaction from creation to confirmation."""
        # Setup
        wallet_mgr = WalletManager()
        wallet = wallet_mgr.create_wallet()
        account = wallet.create_account()

        pool = TransactionPool()
        tracker = TransactionTracker()

        # Create and sign transaction
        tx = Transaction(
            sender=account.address,
            receiver="0xrecipient",
            amount=1000,
            tx_type=TransactionType.TRANSFER,
            nonce=0,
        )
        tx.sign(account.private_key)

        # Add to pool
        pool.add_transaction(tx)
        assert pool.size() == 1

        # Track transaction
        tracker.add_transaction(tx)

        # Confirm transaction
        tracker.update_status(tx.hash, TransactionStatus.CONFIRMED, block_number=1, gas_used=21000)
        assert tx.status == TransactionStatus.CONFIRMED
        assert tx.fee == tx.calculate_fee()

    def test_token_transfer_with_wallet(self):
        """Test token transfer between wallet accounts."""
        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")

        wallet_mgr = WalletManager()
        wallet = wallet_mgr.create_wallet()
        acc1 = wallet.create_account()
        acc2 = wallet.create_account()

        # Mint to first account
        token.mint(acc1.address, 10000)

        # Transfer between accounts
        token.transfer(acc1.address, acc2.address, 3000)
        assert token.balance_of(acc1.address) == 7000
        assert token.balance_of(acc2.address) == 3000

    def test_contract_with_token(self):
        """Test contract interaction with tokens."""
        registry = TokenRegistry()
        token = registry.create_token("Gov", "GOV", owner="contract_owner")

        engine = ContractEngine()
        contract = engine.deploy("contract_owner", "governance_code", {"token": token.address})

        def get_token_address(contract, caller):
            return contract.get_state("token")

        contract.register_method("get_token", get_token_address)
        result = engine.call_contract(contract.address, "get_token", "anyone")
        assert result == token.address

    def test_consensus_with_transactions(self):
        """Test block production with transactions."""
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 10000)

        txs = [
            {"from": "alice", "to": "bob", "amount": 100},
            {"from": "charlie", "to": "dave", "amount": 200},
        ]
        block = engine.produce_block(txs)
        assert len(block.transactions) == 2
        assert engine.validate_block(block)

    def test_validator_staking_flow(self):
        """Test complete staking and block production flow."""
        engine = ConsensusEngine()
        engine.register_validator("val1", "pubkey1", 5000)
        engine.delegate("delegator1", "val1", 3000)

        assert engine.validators["val1"].stake == 8000

        block = engine.produce_block([], validator_addr="val1")
        assert block.validator == "val1"
        assert engine.validators["val1"].blocks_proposed == 1

    def test_multi_wallet_transfer(self):
        """Test transfers between multiple wallets."""
        wallet_mgr = WalletManager()
        w1 = wallet_mgr.create_wallet(label="wallet1")
        w2 = wallet_mgr.create_wallet(label="wallet2")

        a1 = w1.create_account()
        a2 = w2.create_account()

        registry = TokenRegistry()
        token = registry.create_token("Test", "TST")
        token.mint(a1.address, 5000)
        token.transfer(a1.address, a2.address, 2000)

        assert token.balance_of(a1.address) == 3000
        assert token.balance_of(a2.address) == 2000

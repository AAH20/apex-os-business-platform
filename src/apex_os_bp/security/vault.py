"""Secret vault for APEX-OS Business Platform."""
from __future__ import annotations

import hashlib
import os
from typing import Dict, List, Optional


class SecretVault:
    """In-memory secret vault with encryption at rest."""

    def __init__(self, master_key: Optional[str] = None):
        self._secrets: Dict[str, str] = {}
        self._master_key = master_key or os.urandom(32).hex()

    def store(self, key: str, value: str) -> None:
        """Store a secret."""
        self._secrets[key] = self._encrypt(value)

    def get(self, key: str) -> Optional[str]:
        """Get a secret."""
        encrypted = self._secrets.get(key)
        if encrypted is None:
            return None
        return self._decrypt(encrypted)

    def delete(self, key: str) -> None:
        """Delete a secret."""
        self._secrets.pop(key, None)

    def list_keys(self) -> List[str]:
        """List all secret keys."""
        return list(self._secrets.keys())

    def _encrypt(self, value: str) -> str:
        """Encrypt value (XOR with master key for demo)."""
        key_bytes = self._master_key.encode()
        value_bytes = value.encode()
        encrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(value_bytes)])
        return encrypted.hex()

    def _decrypt(self, encrypted: str) -> str:
        """Decrypt value."""
        key_bytes = self._master_key.encode()
        encrypted_bytes = bytes.fromhex(encrypted)
        decrypted = bytes([b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes)])
        return decrypted.decode()

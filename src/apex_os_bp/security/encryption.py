"""Encryption at rest for APEX-OS Business Platform.

Provides authenticated encryption using a password-derived key with
PBKDF2-HMAC-SHA256 key derivation and an HMAC-based stream cipher
for confidentiality and integrity.
"""

import base64
import hashlib
import hmac
import json
import os
import struct
from typing import Union


class EncryptionError(Exception):
    """Base exception for encryption errors."""
    pass


class DecryptionError(EncryptionError):
    """Raised when decryption or authentication fails."""
    pass


class EncryptionManager:
    """Manages encryption and decryption of data at rest.

    Uses PBKDF2-HMAC-SHA256 for key derivation from a master password,
    and an HMAC-SHA256-based stream cipher (counter mode) for encryption.
    Authenticated with HMAC-SHA256 to detect tampering.
    """

    SALT_SIZE = 16
    NONCE_SIZE = 16
    MAC_SIZE = 32
    KEY_ITERATIONS = 100_000

    def __init__(self, master_key: str):
        """Initialize the encryption manager.

        Args:
            master_key: Master password used to derive the encryption key.
        """
        self._master_key = master_key.encode("utf-8")

    def _derive_key(self, salt: bytes) -> bytes:
        """Derive an encryption key from the master key and salt using PBKDF2."""
        return hashlib.pbkdf2_hmac(
            "sha256", self._master_key, salt, self.KEY_ITERATIONS
        )

    def _keystream(self, key: bytes, nonce: bytes, length: int) -> bytes:
        """Generate a keystream using HMAC-SHA256 in counter mode."""
        blocks = []
        counter = 0
        while len(b"".join(blocks)) < length:
            block = hmac.new(
                key, nonce + struct.pack(">Q", counter), hashlib.sha256
            ).digest()
            blocks.append(block)
            counter += 1
        return b"".join(blocks)[:length]

    def encrypt(self, plaintext: Union[str, bytes]) -> str:
        """Encrypt plaintext and return base64-encoded ciphertext.

        Args:
            plaintext: Data to encrypt (string or bytes).

        Returns:
            Base64-encoded ciphertext string.
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode("utf-8")

        salt = os.urandom(self.SALT_SIZE)
        nonce = os.urandom(self.NONCE_SIZE)
        key = self._derive_key(salt)

        keystream = self._keystream(key, nonce, len(plaintext))
        ciphertext = bytes(a ^ b for a, b in zip(plaintext, keystream))

        mac = hmac.new(key, salt + nonce + ciphertext, hashlib.sha256).digest()

        return base64.b64encode(salt + nonce + mac + ciphertext).decode("ascii")

    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt base64-encoded ciphertext.

        Args:
            ciphertext_b64: Base64-encoded ciphertext from encrypt().

        Returns:
            Decrypted plaintext string.

        Raises:
            DecryptionError: If the ciphertext is invalid, tampered with,
                or the key is wrong.
        """
        try:
            data = base64.b64decode(ciphertext_b64.encode("ascii"))
        except Exception as e:
            raise DecryptionError(f"Invalid base64 encoding: {e}")

        min_size = self.SALT_SIZE + self.NONCE_SIZE + self.MAC_SIZE
        if len(data) < min_size:
            raise DecryptionError("Ciphertext too short")

        salt = data[: self.SALT_SIZE]
        nonce = data[self.SALT_SIZE : self.SALT_SIZE + self.NONCE_SIZE]
        mac = data[self.SALT_SIZE + self.NONCE_SIZE : min_size]
        ciphertext = data[min_size:]

        key = self._derive_key(salt)
        expected_mac = hmac.new(
            key, salt + nonce + ciphertext, hashlib.sha256
        ).digest()

        if not hmac.compare_digest(mac, expected_mac):
            raise DecryptionError("MAC verification failed — data may be tampered")

        keystream = self._keystream(key, nonce, len(ciphertext))
        plaintext = bytes(a ^ b for a, b in zip(ciphertext, keystream))

        return plaintext.decode("utf-8")

    def encrypt_dict(self, data: dict) -> str:
        """Encrypt a dictionary by serializing it to JSON first.

        Args:
            data: Dictionary to encrypt.

        Returns:
            Base64-encoded ciphertext string.
        """
        return self.encrypt(json.dumps(data))

    def decrypt_dict(self, ciphertext_b64: str) -> dict:
        """Decrypt ciphertext and deserialize the result as a dictionary.

        Args:
            ciphertext_b64: Base64-encoded ciphertext from encrypt_dict().

        Returns:
            Decrypted dictionary.
        """
        return json.loads(self.decrypt(ciphertext_b64))

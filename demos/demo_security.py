"""
demo_security.py — Security demos for APEX-OS Business Platform.

Run: python demos/demo_security.py
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


# ---------------------------------------------------------------------------
# 1. Create user
# ---------------------------------------------------------------------------

def create_user(username: str, password: str) -> dict[str, Any]:
    """Create a user with a salted, hashed password (PBKDF2-SHA256)."""
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    user = {
        "id": secrets.token_hex(8),
        "username": username,
        "salt": base64.b64encode(salt).decode(),
        "password_hash": base64.b64encode(pwd_hash).decode(),
        "roles": [],
    }
    print(f"[1] Created user: {username} (id={user['id']})")
    return user


# ---------------------------------------------------------------------------
# 2. Assign role
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ["read", "write", "delete", "manage_users"],
    "editor": ["read", "write"],
    "viewer": ["read"],
}


def assign_role(user: dict[str, Any], role: str) -> None:
    """Assign a role to a user."""
    if role not in ROLE_PERMISSIONS:
        raise ValueError(f"Unknown role: {role}")
    if role not in user["roles"]:
        user["roles"].append(role)
    print(f"[2] Assigned role '{role}' to {user['username']}")


# ---------------------------------------------------------------------------
# 3. Check permission
# ---------------------------------------------------------------------------

def has_permission(user: dict[str, Any], permission: str) -> bool:
    """Check if any of the user's roles grants the given permission."""
    for role in user["roles"]:
        if permission in ROLE_PERMISSIONS.get(role, []):
            return True
    return False


def check_permission(user: dict[str, Any], permission: str) -> None:
    """Print the result of a permission check."""
    result = has_permission(user, permission)
    status = "GRANTED" if result else "DENIED"
    print(f"[3] {user['username']} → '{permission}': {status}")


# ---------------------------------------------------------------------------
# 4. Generate JWT
# ---------------------------------------------------------------------------

JWT_SECRET = os.environ.get("APEX_JWT_SECRET", "demo-secret-change-me")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def generate_jwt(user: dict[str, Any], ttl: int = 3600) -> str:
    """Generate a signed JWT (HS256) for the given user."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {
        "sub": user["id"], "username": user["username"],
        "roles": user["roles"], "iat": now, "exp": now + ttl,
    }
    h = _b64url(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(JWT_SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
    token = f"{h}.{p}.{_b64url(sig)}"
    print(f"[4] Generated JWT for {user['username']} (expires in {ttl}s)")
    return token


def verify_jwt(token: str) -> dict[str, Any] | None:
    """Verify a JWT signature and expiry. Returns payload or None."""
    try:
        h, p, s = token.split(".")
        expected = hmac.new(JWT_SECRET.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, base64.urlsafe_b64decode(s + "==")):
            return None
        payload = json.loads(base64.urlsafe_b64decode(p + "=="))
        return None if payload.get("exp", 0) < time.time() else payload
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 5. Encrypt data
# ---------------------------------------------------------------------------

def _derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from a password using PBKDF2."""
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)


def encrypt_data(plaintext: str, password: str) -> dict[str, str]:
    """Encrypt data with a password-derived key (XOR stream + HMAC integrity)."""
    salt = os.urandom(16)
    key = _derive_key(password, salt)
    data = plaintext.encode()
    keystream = hashlib.sha256(key + salt).digest()
    encrypted = bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(data))
    mac = hmac.new(key, encrypted, hashlib.sha256).hexdigest()
    result = {
        "salt": base64.b64encode(salt).decode(),
        "ciphertext": base64.b64encode(encrypted).decode(),
        "mac": mac,
    }
    print(f"[5] Encrypted {len(data)} bytes (MAC={mac[:16]}…)")
    return result


def decrypt_data(enc: dict[str, str], password: str) -> str | None:
    """Decrypt data and verify integrity. Returns plaintext or None."""
    salt = base64.b64decode(enc["salt"])
    encrypted = base64.b64decode(enc["ciphertext"])
    key = _derive_key(password, salt)
    if not hmac.compare_digest(hmac.new(key, encrypted, hashlib.sha256).hexdigest(), enc["mac"]):
        return None
    keystream = hashlib.sha256(key + salt).digest()
    decrypted = bytes(b ^ keystream[i % len(keystream)] for i, b in enumerate(encrypted))
    return decrypted.decode()


# ---------------------------------------------------------------------------
# Main — run all demos
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("APEX-OS Security Demo")
    print("=" * 60)

    # 1. Create user
    user = create_user("alice", "s3cret-pass!")
    print(f"    Salt: {user['salt'][:20]}…")
    print(f"    Hash: {user['password_hash'][:20]}…")

    # 2. Assign role
    assign_role(user, "editor")
    print(f"    Roles: {user['roles']}")

    # 3. Check permission
    check_permission(user, "read")
    check_permission(user, "write")
    check_permission(user, "delete")

    # 4. Generate JWT
    token = generate_jwt(user)
    print(f"    Token: {token[:40]}…")
    verified = verify_jwt(token)
    print(f"    Verified: {verified is not None}")
    if verified:
        print(f"    Payload: {json.dumps(verified, indent=2)}")

    # 5. Encrypt data
    secret_msg = "Launch code: 1234"
    enc = encrypt_data(secret_msg, "s3cret-pass!")
    print(f"    Ciphertext: {enc['ciphertext'][:30]}…")
    dec = decrypt_data(enc, "s3cret-pass!")
    print(f"    Decrypted: {dec}")
    wrong = decrypt_data(enc, "wrong-pass")
    print(f"    Wrong password → {wrong}")

    print("=" * 60)
    print("All demos completed successfully.")


if __name__ == "__main__":
    main()

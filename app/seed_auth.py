"""Password helpers kept separate to avoid circular imports."""

from __future__ import annotations

import hashlib
import secrets


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2:{salt}:{digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _algo, salt, expected = password_hash.split(":", 2)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return secrets.compare_digest(digest.hex(), expected)
    except Exception:
        return False

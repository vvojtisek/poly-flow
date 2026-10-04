"""Secret hashing and session tokens."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()
# Verified against when the user does not exist, so timing does not reveal valid usernames.
_DUMMY_HASH = _hasher.hash("polyflow-dummy-secret")


def hash_secret(secret: str) -> str:
    return _hasher.hash(secret)


def verify_secret(secret_hash: str | None, secret: str) -> bool:
    try:
        return _hasher.verify(secret_hash or _DUMMY_HASH, secret) and secret_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    """Only digests are stored; a DB leak does not yield usable session cookies."""
    return hashlib.sha256(token.encode()).hexdigest()

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

import jwt
from pwdlib import PasswordHash

from backend.app.config.settings import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
)


# =========================================================
# PASSWORD HASHING
# =========================================================

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """
    Hash a password using the recommended pwdlib algorithm.
    """
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """
    Verify a plaintext password against its stored hash.
    """
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


# =========================================================
# JWT CONFIGURATION VALIDATION
# =========================================================

if not JWT_SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not configured."
    )


# =========================================================
# JWT CREATION
# =========================================================

def create_access_token(
    user_id: int,
    email: str,
    role: str,
) -> str:
    """
    Create a signed JWT access token.
    """

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
    }

    return jwt.encode(
        payload,
        JWT_SECRET_KEY,
        algorithm=JWT_ALGORITHM,
    )


# =========================================================
# JWT DECODING
# =========================================================

def decode_access_token(
    token: str,
) -> dict:
    """
    Decode and validate a JWT access token.

    jwt.decode automatically validates:
        - signature
        - algorithm
        - expiration
    """

    return jwt.decode(
        token,
        JWT_SECRET_KEY,
        algorithms=[JWT_ALGORITHM],
    )
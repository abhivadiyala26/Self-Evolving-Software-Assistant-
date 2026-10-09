"""Password, account provisioning, and server-side session helpers."""

import base64
import binascii
import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from services.database import AuthSession, User


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PASSWORD_MIN_LENGTH = 8
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
def _session_ttl_days() -> int:
    try:
        value = int(os.getenv("AUTOSRE_SESSION_TTL_DAYS", "7"))
    except (TypeError, ValueError):
        value = 7
    return min(30, max(1, value))


SESSION_TTL_DAYS = _session_ttl_days()


def normalize_email(email: str) -> str:
    return email.strip().lower()


def valid_email(email: str) -> bool:
    return len(email) <= 254 and bool(EMAIL_PATTERN.fullmatch(email))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    encode = lambda value: base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${encode(salt)}${encode(derived)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n, r, p, encoded_salt, encoded_digest = password_hash.split("$", 5)
        if algorithm != "scrypt" or (int(n), int(r), int(p)) != (SCRYPT_N, SCRYPT_R, SCRYPT_P):
            return False
        decode = lambda value: base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        salt = decode(encoded_salt)
        expected = decode(encoded_digest)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
        return hmac.compare_digest(actual, expected)
    except (TypeError, ValueError, MemoryError, binascii.Error):
        return False


def create_session(db: Session, user: User) -> str:
    raw_token = secrets.token_urlsafe(40)
    db.add(AuthSession(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS),
    ))
    db.commit()
    return raw_token


def authenticate_session(db: Session, raw_token: str | None):
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    row = db.execute(
        select(AuthSession, User)
        .join(User, User.id == AuthSession.user_id)
        .where(AuthSession.token_hash == token_hash)
    ).first()
    if not row:
        return None
    session, user = row
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        return None
    return user, session


def revoke_session(db: Session, raw_token: str | None):
    if not raw_token:
        return
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    db.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))
    db.commit()


def public_account(user: User) -> dict:
    return {"id": user.id, "name": user.name, "email": user.email, "role": user.role}


def provision_configured_admin(db: Session) -> bool:
    """Ensure exactly one configured admin exists without a source-code default."""
    email = normalize_email(os.getenv("AUTOSRE_ADMIN_EMAIL", ""))
    password = os.getenv("AUTOSRE_ADMIN_PASSWORD", "")
    if not email or not password:
        return False
    if not valid_email(email) or not 12 <= len(password) <= 128:
        raise ValueError("AUTOSRE_ADMIN_EMAIL must be valid and AUTOSRE_ADMIN_PASSWORD must be between 12 and 128 characters.")

    configured_admin = db.scalar(select(User).where(User.email == email))
    previous_admins = list(db.scalars(select(User).where(User.role == "admin")))
    for previous in previous_admins:
        if previous.email != email:
            previous.role = "user"
    if previous_admins:
        db.execute(delete(AuthSession).where(AuthSession.user_id.in_([user.id for user in previous_admins])))

    if configured_admin is None:
        configured_admin = User(name="AutoSRE Admin", email=email, password_hash=hash_password(password), role="admin")
        db.add(configured_admin)
    else:
        configured_admin.name = "AutoSRE Admin"
        configured_admin.password_hash = hash_password(password)
        configured_admin.role = "admin"
        db.execute(delete(AuthSession).where(AuthSession.user_id == configured_admin.id))
    db.commit()
    return True

"""Password, account provisioning, and server-side session helpers."""

import base64
import binascii
import hashlib
import hmac
import os
import re
import secrets
import threading
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from uuid import uuid4

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


@dataclass
class DemoAccount:
    """Process-local demo account. Passwords are stored only as scrypt hashes."""

    id: str
    name: str
    email: str
    role: str
    password_hash: str


_demo_lock = threading.RLock()
_demo_accounts: dict[str, DemoAccount] = {}
_demo_sessions: dict[str, tuple[str, datetime]] = {}
_fixed_demo_emails: set[str] = set()
_demo_auth_status = {
    "admin_configured": False,
    "demo_user_configured": False,
    "admin_error": None,
    "demo_user_error": None,
    "public_demo_enabled": False,
}
_public_demo_enabled = False
PUBLIC_DEMO_ACCOUNTS = {
    "user": {"email": "demo.user@autosre-demo.example", "password": "AutoSRE-Demo-User-2026!"},
    "admin": {"email": "demo.admin@autosre-demo.example", "password": "AutoSRE-Demo-Admin-2026!"},
}


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


def configure_demo_accounts(*, allow_public_demo: bool = False) -> dict:
    """Load private demo identities and optionally add public demo-only accounts."""
    global _fixed_demo_emails, _public_demo_enabled
    configured_by_role = {}
    status = {}
    definitions = (
        ("admin", "AUTOSRE_ADMIN_EMAIL", "AUTOSRE_ADMIN_PASSWORD", "AutoSRE Admin", 12),
        ("user", "DEMO_USER_EMAIL", "DEMO_USER_PASSWORD", "ShopSphere Demo User", PASSWORD_MIN_LENGTH),
    )
    for role, email_key, password_key, name, minimum in definitions:
        raw_email = os.getenv(email_key, "").strip()
        password = os.getenv(password_key, "")
        complete = bool(raw_email and password)
        if not complete:
            status[f"{role}_configured" if role == "admin" else "demo_user_configured"] = False
            status[f"{role}_error" if role == "admin" else "demo_user_error"] = None
            continue
        email = normalize_email(raw_email)
        if not valid_email(email) or not minimum <= len(password) <= 128:
            status[f"{role}_configured" if role == "admin" else "demo_user_configured"] = False
            status[f"{role}_error" if role == "admin" else "demo_user_error"] = (
                f"{email_key} must be a valid email and {password_key} must be between {minimum} and 128 characters."
            )
            continue
        configured_by_role[role] = DemoAccount(
            id=str(uuid4()), name=name, email=email, role=role, password_hash=hash_password(password)
        )
        status[f"{role}_configured" if role == "admin" else "demo_user_configured"] = True
        status[f"{role}_error" if role == "admin" else "demo_user_error"] = None

    # If both configured roles use the same email, disable both rather than
    # allowing the selected role to determine that account's privileges.
    configured_admin = configured_by_role.get("admin")
    configured_user = configured_by_role.get("user")
    if configured_admin and configured_user and configured_admin.email == configured_user.email:
        configured_by_role.clear()
        status["admin_configured"] = False
        status["demo_user_configured"] = False
        status["admin_error"] = "Admin and demo user must use different email addresses."
        status["demo_user_error"] = "Admin and demo user must use different email addresses."
    configured = {account.email: account for account in configured_by_role.values()}
    public_accounts_available = bool(allow_public_demo)
    if public_accounts_available:
        for role, credentials in PUBLIC_DEMO_ACCOUNTS.items():
            email = credentials["email"]
            if email in configured:
                public_accounts_available = False
                break
            configured[email] = DemoAccount(
                id=str(uuid4()),
                name="AutoSRE Demo Admin" if role == "admin" else "ShopSphere Demo User",
                email=email,
                role=role,
                password_hash=hash_password(credentials["password"]),
            )
        if not public_accounts_available:
            for credentials in PUBLIC_DEMO_ACCOUNTS.values():
                configured.pop(credentials["email"], None)
        else:
            status["admin_configured"] = True
            status["demo_user_configured"] = True
            status["admin_error"] = None
            status["demo_user_error"] = None
    status["public_demo_enabled"] = public_accounts_available

    with _demo_lock:
        old_fixed_ids = {account.id for email, account in _demo_accounts.items() if email in _fixed_demo_emails}
        _demo_accounts.update(configured)
        for email in _fixed_demo_emails - set(configured):
            _demo_accounts.pop(email, None)
        _demo_sessions_copy = {
            token_hash: session for token_hash, session in _demo_sessions.items()
            if session[0] not in old_fixed_ids
        }
        _demo_sessions.clear()
        _demo_sessions.update(_demo_sessions_copy)
        _fixed_demo_emails = set(configured)
        _public_demo_enabled = public_accounts_available
        _demo_auth_status.update(status)
        return dict(_demo_auth_status)


def demo_auth_status() -> dict:
    with _demo_lock:
        return dict(_demo_auth_status)


def public_demo_credentials() -> dict | None:
    """Return only intentionally public demo credentials, never configured secrets."""
    with _demo_lock:
        if not _public_demo_enabled:
            return None
        return {role: dict(credentials) for role, credentials in PUBLIC_DEMO_ACCOUNTS.items()}


def demo_account_exists(email: str) -> bool:
    normalized = normalize_email(email)
    with _demo_lock:
        return normalized in _demo_accounts


def register_temporary_demo_user(name: str, email: str, password: str) -> DemoAccount:
    normalized = normalize_email(email)
    account = DemoAccount(
        id=str(uuid4()), name=name.strip(), email=normalized, role="user", password_hash=hash_password(password)
    )
    with _demo_lock:
        if normalized in _demo_accounts:
            raise ValueError("An account already exists with this email.")
        _demo_accounts[normalized] = account
    return account


def authenticate_demo_account(email: str, password: str, requested_role: str | None = None):
    normalized = normalize_email(email)
    with _demo_lock:
        account = _demo_accounts.get(normalized)
    if not account or (requested_role and requested_role != account.role):
        return None
    return account if verify_password(password, account.password_hash) else None


def create_demo_session(user: DemoAccount) -> str:
    raw_token = secrets.token_urlsafe(40)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    with _demo_lock:
        _demo_sessions[token_hash] = (user.id, expires_at)
    return raw_token


def authenticate_demo_session(raw_token: str | None):
    if not raw_token:
        return None
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = datetime.now(timezone.utc)
    with _demo_lock:
        session = _demo_sessions.get(token_hash)
        if not session:
            return None
        user_id, expires_at = session
        if expires_at <= now:
            _demo_sessions.pop(token_hash, None)
            return None
        account = next((candidate for candidate in _demo_accounts.values() if candidate.id == user_id), None)
        if account is None:
            _demo_sessions.pop(token_hash, None)
        return account


def revoke_demo_session(raw_token: str | None):
    if raw_token:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        with _demo_lock:
            _demo_sessions.pop(token_hash, None)


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

"""Database models and connection setup for persistent AutoSRE account data."""

import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def _database_url():
    configured = os.getenv("DATABASE_URL") or os.getenv("AUTOSRE_DATABASE_URL")
    if configured:
        if configured.startswith("postgres://"):
            return "postgresql+psycopg://" + configured[len("postgres://"):]
        if configured.startswith("postgresql://"):
            return "postgresql+psycopg://" + configured[len("postgresql://"):]
        return configured

    # Render's filesystem is ephemeral. Refuse to pretend a local SQLite file
    # there is durable; production auth/orders require an explicit PostgreSQL URL.
    if os.getenv("RENDER"):
        return None

    db_file = Path(os.getenv("AUTOSRE_SQLITE_PATH", "data/autosre.db"))
    db_file.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_file.as_posix()}"


DATABASE_URL = _database_url()
DATABASE_CONFIGURED = DATABASE_URL is not None
engine = None
SessionLocal = None

if DATABASE_URL:
    engine_options = {"pool_pre_ping": True}
    if DATABASE_URL.startswith("sqlite:"):
        engine_options["connect_args"] = {"check_same_thread": False}
    engine = create_engine(DATABASE_URL, **engine_options)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    items: Mapped[list] = mapped_column(JSON, nullable=False)
    total_amount: Mapped[float] = mapped_column(nullable=False)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PLACED")
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    delivery_option: Mapped[str] = mapped_column(String(32), nullable=False)
    delivery_estimate: Mapped[str] = mapped_column(String(80), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        # The same request can be retried safely for one account, but cannot
        # create a second order after a timeout or lost response.
        UniqueConstraint("user_id", "idempotency_key", name="uq_order_user_idempotency"),
    )


def initialize_database():
    if engine is None:
        return False
    Base.metadata.create_all(bind=engine)
    return True


def get_db_session():
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Persistent storage is not configured. Set DATABASE_URL to a durable PostgreSQL database.")
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

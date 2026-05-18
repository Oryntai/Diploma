from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import inspect, text
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./iot_monitor.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)
_db_initialized = False


def ensure_db_initialized() -> None:
    global _db_initialized
    if _db_initialized:
        return
    init_db()
    _db_initialized = True


def get_db() -> Generator[Session, None, None]:
    ensure_db_initialized()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from .base import Base
    from ..models import Alert, Device, RegisteredDevice, TelemetryEvent

    _ = Alert, Device, RegisteredDevice, TelemetryEvent
    Base.metadata.create_all(bind=engine)
    _ensure_registered_device_columns()


def _ensure_registered_device_columns() -> None:
    inspector = inspect(engine)
    if "registered_devices" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("registered_devices")}
    statements = []
    if "ip_address" not in columns:
        statements.append("ALTER TABLE registered_devices ADD COLUMN ip_address VARCHAR(45)")
    if "mac_address" not in columns:
        statements.append("ALTER TABLE registered_devices ADD COLUMN mac_address VARCHAR(32)")
    if "device_mode" not in columns:
        statements.append(
            "ALTER TABLE registered_devices ADD COLUMN device_mode VARCHAR(20) DEFAULT 'simulated'"
        )
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

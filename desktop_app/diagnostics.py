from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any


LOG_PATH = Path(__file__).resolve().parents[1] / "logs" / "desktop_diagnostics.log"


def reset_log() -> None:
    logger = logging.getLogger("desktop_diagnostics")
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text("", encoding="utf-8")


def get_logger() -> logging.Logger:
    logger = logging.getLogger("desktop_diagnostics")
    if logger.handlers:
        return logger

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def log_event(event: str, **fields: Any) -> None:
    payload = {
        "ts": datetime.now().astimezone().isoformat(timespec="seconds"),
        "event": event,
        **fields,
    }
    try:
        get_logger().info(json.dumps(payload, ensure_ascii=False, default=str))
    except Exception:
        pass

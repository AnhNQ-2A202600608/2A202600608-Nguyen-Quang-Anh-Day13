from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import structlog
from structlog.contextvars import merge_contextvars

from .pii import scrub_text, scrub_data
import threading
import json
from datetime import datetime, timezone

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))
AUDIT_LOG_PATH = Path(os.getenv("AUDIT_LOG_PATH", "data/audit.jsonl"))
audit_lock = threading.Lock()


class JsonlFileProcessor:
    def __call__(self, logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        rendered = structlog.processors.JSONRenderer()(logger, method_name, event_dict)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(rendered + "\n")
        return event_dict



def scrub_event(_: Any, __: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    safe_keys = {
        "ts", "level", "service", "correlation_id", "user_id_hash",
        "session_id", "feature", "model", "env", "latency_ms",
        "tokens_in", "tokens_out", "cost_usd", "error_type", "tool_name", "event"
    }
    if "correlation_id" not in event_dict:
        event_dict["correlation_id"] = "system"
    for k, v in list(event_dict.items()):
        if k not in safe_keys:
            event_dict[k] = scrub_data(v)
    return event_dict



def configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")))
    structlog.configure(
        processors=[
            merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="ts"),
            scrub_event,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            JsonlFileProcessor(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        cache_logger_on_first_use=True,
    )



def write_audit_log(
    event: str,
    user_id_hash: str | None,
    session_id: str | None,
    correlation_id: str | None,
    payload: dict[str, Any] | None
) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    scrubbed_payload = scrub_data(payload) if payload else {}
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "user_id_hash": user_id_hash,
        "session_id": session_id,
        "correlation_id": correlation_id or "UNKNOWN",
        "payload": scrubbed_payload,
    }
    with audit_lock:
        with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")



def get_logger() -> structlog.typing.FilteringBoundLogger:
    return structlog.get_logger()

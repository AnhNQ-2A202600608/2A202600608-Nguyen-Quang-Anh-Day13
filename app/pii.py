from __future__ import annotations
import hmac

import hashlib
import os
import re
from typing import Any

PII_PATTERNS: dict[str, str] = {
    "email": r"[\w\.-]+@[\w\.-]+\.\w+",
    "phone_vn": r"(?:\+84|0)\d{9,10}\b|(?:\+84|0)[ \.-]?\d{3}[ \.-]?\d{3}[ \.-]?\d{3,4}\b",
    "cccd": r"\b\d{12}\b",
    "credit_card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "passport": r"\b[A-Z]\d{7}\b",
    "address": r"(?:\b(?:số|ngõ|ngách|hẻm)\s+\d+(?:\s+(?:đường|phố)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+)?(?:\s+(?:phường|quận|huyện|tỉnh|thành\s+phố)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+)?)|"
               r"\b(?:đường|phố)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+[,\s]+(?:phường|quận|huyện|tỉnh|thành\s+phố)\s+[A-ZÀ-Ỹa-zà-ỹ0-9\s]+"
}


def scrub_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = re.sub(pattern, f"[REDACTED_{name.upper()}]", safe, flags=re.IGNORECASE)
    return safe


def scrub_data(data: Any) -> Any:
    if isinstance(data, str):
        return scrub_text(data)
    elif isinstance(data, dict):
        return {k: scrub_data(v) for k, v in data.items()}
    elif isinstance(data, (list, tuple)):
        cleaned = [scrub_data(v) for v in data]
        return cleaned if isinstance(data, list) else tuple(cleaned)
    return data


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    secret = os.getenv("APP_HASH_SECRET", "dev-fallback-secret-key-12345")
    h = hmac.new(secret.encode("utf-8"), user_id.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()[:12]

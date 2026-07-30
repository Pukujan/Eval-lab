"""Redaction for span attributes and logged values.

Two rules, because the two failure modes are different:

* **Key-shaped secrets** — anything named like a credential is dropped by name,
  whatever its value.
* **Value-shaped secrets** — anything that *looks* like a key is dropped whatever
  it is called, because the variable someone named ``tmp`` is exactly the one that
  leaks.

Prompts and responses are never recorded raw. They are recorded as a content hash
plus a length, which keeps a pasted credential out of the trace store entirely
(threat model T-5) while still letting you prove two runs sent the same prompt.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

REDACTED = "[redacted]"

_SENSITIVE_KEY_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password|passwd|credential|authorization|auth)",
    re.IGNORECASE,
)

_SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-]{8,}\b", re.IGNORECASE),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
)


def is_sensitive_key(key: str) -> bool:
    return bool(_SENSITIVE_KEY_PATTERN.search(key))


def redact_value(value: Any) -> Any:
    """Replace secret-shaped substrings inside a value."""
    if not isinstance(value, str):
        return value
    redacted = value
    for pattern in _SENSITIVE_VALUE_PATTERNS:
        redacted = pattern.sub(REDACTED, redacted)
    return redacted


def redact_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Scrub a span attribute mapping before it is exported."""
    cleaned: dict[str, Any] = {}
    for key, value in attributes.items():
        if is_sensitive_key(key):
            cleaned[key] = REDACTED
        else:
            cleaned[key] = redact_value(value)
    return cleaned


def content_fingerprint(text: str) -> dict[str, Any]:
    """A recordable stand-in for text we deliberately do not store.

    Enough to prove two payloads were identical; not enough to reconstruct either.
    """
    return {
        "content.sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "content.length": len(text),
    }

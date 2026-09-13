"""Safe serialization for Weave and API traces.

Never call dataclasses.asdict on an arbitrary object — that raises
TypeError: asdict() should be called on dataclass instances.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


def to_plain(value: Any) -> Any:
    """Convert dataclasses, Pydantic models, dicts, and lists to JSON-safe data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {key: to_plain(item) for key, item in asdict(value).items()}
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        return to_plain(model_dump())
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_plain(item) for item in value]
    return str(value)

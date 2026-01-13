"""Defines retry policies for different platforms."""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RetryPolicy:
    """Defines retry behavior for a platform."""
    max_attempts: Optional[int] = None  # None = unlimited

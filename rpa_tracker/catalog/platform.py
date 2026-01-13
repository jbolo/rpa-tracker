"""Defines platform configurations for transaction flows in RPA Tracker."""
from dataclasses import dataclass
from typing import Sequence
from rpa_tracker.retry.policy import RetryPolicy


@dataclass(frozen=True)
class PlatformDefinition:
    """Defines a platform in a transaction flow."""
    code: str
    stages: Sequence[str] = ()
    retry_policy: RetryPolicy = RetryPolicy()
    order: int = 0

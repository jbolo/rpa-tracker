"""Defines platform configurations for transaction flows in RPA Tracker."""
from dataclasses import dataclass, field
from typing import Sequence
from rpa_tracker.constants import DEFAULT_STAGE
from rpa_tracker.retry.policy import RetryPolicy


@dataclass(frozen=True)
class PlatformDefinition:
    """Defines a platform in a transaction flow."""
    code: str
    stages: Sequence[str] = (DEFAULT_STAGE,)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    order: int = 0

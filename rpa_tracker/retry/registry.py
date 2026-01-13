"""Registry for retry policies based on external systems."""
from typing import Dict
from rpa_tracker.retry.policy import RetryPolicy


class RetryPolicyRegistry:
    _policies: Dict[str, RetryPolicy] = {}

    @classmethod
    def register(cls, system: str, policy: RetryPolicy) -> None:
        """Register a retry policy for a given external system."""
        cls._policies[system] = policy

    @classmethod
    def get(cls, system: str) -> RetryPolicy:
        """Retrieve the retry policy for a given external system."""
        return cls._policies.get(system, RetryPolicy())

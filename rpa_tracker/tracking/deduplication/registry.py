"""Registry for deduplication strategies."""
from typing import Dict
from rpa_tracker.tracking.deduplication.base import DeduplicationStrategy


from typing import Optional


class DeduplicationRegistry:
    _registry: Dict[str, DeduplicationStrategy] = {}

    @classmethod
    def register(cls, process_code: str, strategy: DeduplicationStrategy) -> None:
        """Register a deduplication strategy for a given process code."""
        cls._registry[process_code] = strategy

    @classmethod
    def get(cls, process_code: str) -> Optional[DeduplicationStrategy]:
        """Retrieve the deduplication strategy for a given process code."""
        return cls._registry[process_code]

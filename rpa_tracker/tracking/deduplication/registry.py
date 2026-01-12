"""Registry for deduplication strategies."""


class DeduplicationRegistry:
    _registry = {}

    @classmethod
    def register(cls, process_code: str, strategy):
        """Register a deduplication strategy for a given process code."""
        cls._registry[process_code] = strategy

    @classmethod
    def get(cls, process_code: str):
        """Retrieve the deduplication strategy for a given process code."""
        return cls._registry[process_code]

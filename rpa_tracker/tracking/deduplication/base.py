"""Base class for deduplication strategies."""
from abc import abstractmethod
from typing import Any, Optional, Protocol


class DeduplicationStrategy(Protocol):
    version: int

    @abstractmethod
    def calculate_fingerprint(self, payload: Any) -> str:
        """Calculate a unique fingerprint for the given data."""
        ...

    @abstractmethod
    def find_existing_uuid(self, fingerprint: str) -> Optional[str]:
        """Find an existing UUID for the given fingerprint."""
        ...

    @abstractmethod
    def persist_data(self, uuid: str, payload: Any) -> None:
        """Persist deduplication data."""
        ...

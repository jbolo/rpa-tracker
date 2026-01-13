"""Abstract base class for transaction tracking implementations."""
from abc import ABC, abstractmethod
from typing import Any, Optional, Tuple


class TransactionTracker(ABC):

    @abstractmethod
    def start_or_resume(
        self,
        process_code: str,
        payload: Any
    ) -> Tuple[str, bool]:
        """Returns (uuid, is_new_transaction)."""

    @abstractmethod
    def start_stage(self, uuid: str, system: str, stage: Optional[str] = None) -> None:
        """Start a new stage for the given transaction."""

    @abstractmethod
    def log_event(
        self,
        uuid: str,
        system: str,
        attempt: int,
        error_code: int,
        description: Optional[str],
        stage: Optional[str] = None,
    ):
        """Log an event for the given transaction."""
        ...

    @abstractmethod
    def finish_stage(
        self,
        uuid: str,
        system: str,
        state: str,
        error_type: Optional[str],
        description: Optional[str],
        stage: Optional[str] = None,
    ) -> None:
        """Finalize a stage for the given transaction."""
        ...

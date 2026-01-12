"""Abstract base class for transaction tracking implementations."""
from abc import ABC, abstractmethod
from typing import Tuple


class TransactionTracker(ABC):

    @abstractmethod
    def start_or_resume(
        self,
        process_code: str,
        data: dict
    ) -> Tuple[str, bool]:
        """Returns (uuid, is_new_transaction)."""

    @abstractmethod
    def start_stage(self, uuid: str, system: str, stage: str):
        """Start a new stage for the given transaction."""

    @abstractmethod
    def log_event(
        self,
        uuid: str,
        system: str,
        stage: str,
        attempt: int,
        error_code: int,
        description: str | None
    ):
        """Log an event for the given transaction."""
        ...

    @abstractmethod
    def finish_stage(
        self,
        uuid: str,
        system: str,
        stage: str,
        state: str,
        error_type: str | None,
        description: str | None
    ):
        """Finalize a stage for the given transaction."""
        ...

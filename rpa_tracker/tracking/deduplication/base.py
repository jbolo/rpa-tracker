from abc import ABC, abstractmethod
from typing import Optional


class DeduplicationStrategy(ABC):
    version: int

    @abstractmethod
    def calculate_fingerprint(self, data: dict) -> str: ...

    @abstractmethod
    def find_existing_uuid(self, fingerprint: str) -> Optional[str]: ...

    @abstractmethod
    def persist_data(self, uuid: str, data: dict) -> None: ...

"""Fake deduplication strategy for testing purposes."""
from typing import Dict, Optional

from rpa_tracker.tracking.deduplication.base import DeduplicationStrategy
from test.domain.cancel_payload import CancelacionPayload
from test.infra.models.data_repository import DataRepository


class CancelacionDeduplication(DeduplicationStrategy):
    """Deduplicates by 'requerimiento' and persists full data."""
    version = 1

    def __init__(self, data_repo: DataRepository):
        self._store: Dict[str, str] = {}
        self.data_repo = data_repo

    def calculate_fingerprint(self, payload: CancelacionPayload) -> str:
        """Calculate a simple fingerprint based on the 'key' in data."""
        return payload.requerimiento

    def find_existing_uuid(self, fingerprint: str) -> Optional[str]:
        """Find an existing UUID based on the fingerprint."""
        return self._store.get(fingerprint)

    def persist_data(self, uuid: str, payload: CancelacionPayload) -> None:
        """Persist the UUID associated with the data's key."""
        self._store[payload.requerimiento] = uuid
        self.data_repo.save(uuid, payload)

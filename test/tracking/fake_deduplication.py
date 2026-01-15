"""Fake deduplication strategy for testing purposes."""
from typing import List, Optional

from rpa_tracker.tracking.deduplication.base import DeduplicationStrategy
from test.domain.cancel_payload import CancelacionPayload
from test.infra.models.data_repository import DataRepository
from test.infra.models.tx_data import TxData


class CancelacionDeduplication(DeduplicationStrategy):
    """Deduplicates by 'requerimiento' and persists full data."""
    version = 1

    FINGERPRINT_FIELDS: List[str] = ["requerimiento"]
    # Futrure examples:
    # FINGERPRINT_FIELDS = ["requerimiento", "tipo_operacion"]
    # FINGERPRINT_FIELDS = ["requerimiento", "tipo_operacion", "nombre"]

    SEPARATOR = "|"

    def __init__(self, data_repo: DataRepository):
        self.data_repo = data_repo

    def calculate_fingerprint(self, payload: CancelacionPayload) -> str:
        """Calculate fingerprint based on configured fields.

        Examples:
        - ["requerimiento"] -> "FE-0001"
        - ["requerimiento", "tipo_operacion"] -> "FE-0001|ALTA"
        """
        values = [str(getattr(payload, field)) for field in self.FINGERPRINT_FIELDS]
        return self.SEPARATOR.join(values)

    def find_existing_uuid(self, fingerprint: str) -> Optional[str]:
        """Find existing UUID by searching in database.

        Builds query dynamically based on FINGERPRINT_FIELDS.
        """
        # Split fingerprint back to individual values
        values = fingerprint.split(self.SEPARATOR)

        # Build query dynamically
        query = self.data_repo.session.query(TxData.uuid)

        for field_name, value in zip(self.FINGERPRINT_FIELDS, values):
            query = query.filter(getattr(TxData, field_name) == value)

        result = query.first()
        return result[0] if result else None

    def persist_data(self, uuid: str, payload: CancelacionPayload) -> None:
        """Persist the UUID associated with the data's key."""
        self.data_repo.save(uuid, payload)

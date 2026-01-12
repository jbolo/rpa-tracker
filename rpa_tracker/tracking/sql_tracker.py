"""SQL-based implementation of the TransactionTracker."""
import uuid
from rpa_tracker.enums import TransactionState
from rpa_tracker.models.tx_process import TxProcess
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.tracking.transaction_tracker import TransactionTracker
from datetime import datetime


class SqlTransactionTracker(TransactionTracker):

    def __init__(self, session):
        self.session = session

    def start_or_resume(self, process_code, data):
        """Returns (uuid, is_new_transaction)."""
        dedup = DeduplicationRegistry.get(process_code)
        fingerprint = dedup.calculate_fingerprint(data)

        existing = dedup.find_existing_uuid(fingerprint)
        if existing:
            return existing, False

        uuid_tx = str(uuid.uuid4())
        self.session.add(
            TxProcess(
                uuid=uuid_tx,
                process_code=process_code,
                state=TransactionState.PENDING,
                created_at=datetime.now()
            )
        )

        try:
            dedup.persist_data(uuid_tx, data)
            self.session.commit()
            return uuid_tx, True
        except IntegrityError:
            self.session.rollback()
            return dedup.find_existing_uuid(fingerprint), False

import uuid
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.tracking.transaction_tracker import TransactionTracker


class SqlTransactionTracker(TransactionTracker):

    def __init__(self, session):
        self.session = session

    def start_or_resume(self, process_code, data):
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
                created_at=datetime.utcnow()
            )
        )

        try:
            dedup.persist_data(uuid_tx, data)
            self.session.commit()
            return uuid_tx, True
        except IntegrityError:
            self.session.rollback()
            return dedup.find_existing_uuid(fingerprint), False

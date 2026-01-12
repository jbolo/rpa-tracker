from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.enums import TransactionState


def test_transaction_is_created(session):
    dedup = FakeDeduplication()
    DeduplicationRegistry.register("TEST_PROC", dedup)

    tracker = SqlTransactionTracker(session)

    uuid, is_new = tracker.start_or_resume(
        "TEST_PROC",
        {"key": "A"}
    )

    assert is_new is True
    assert uuid is not None

    tx = session.query(tracker.TxProcess).first()
    assert tx.state == TransactionState.PENDING

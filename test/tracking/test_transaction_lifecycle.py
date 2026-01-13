"""Unit tests for transaction lifecycle in RPA tracker."""
from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.models.tx_process import TxProcess
from rpa_tracker.enums import TransactionState

from test.tracking.fake_deduplication import CancelacionDeduplication


def test_transaction_is_created(session):
    """Test that a transaction is created and set to PENDING state."""
    dedup = CancelacionDeduplication()
    DeduplicationRegistry.register("TEST_PROC", dedup)

    tracker = SqlTransactionTracker(session)

    uuid, is_new = tracker.start_or_resume(
        "TEST_PROC",
        {"key": "A"}
    )

    assert is_new is True
    assert uuid is not None

    tx = session.query(TxProcess).first()
    assert tx.state == TransactionState.PENDING

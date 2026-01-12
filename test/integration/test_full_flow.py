"""Integration test for full transaction flow in RPA tracker."""
from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker
from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.enums import TransactionState

from test.tracking.fake_deduplication import FakeDeduplication


def test_full_transaction_flow(session):
    """Test the full transaction flow from start to finish."""
    DeduplicationRegistry.register("FULL_FLOW", FakeDeduplication())

    tracker = SqlTransactionTracker(session)

    uuid, is_new = tracker.start_or_resume(
        "FULL_FLOW",
        {"key": "X"}
    )

    assert is_new

    tracker.start_stage(uuid, "SYS", "STEP1")

    result = ExecutionResult(error_code=0)

    tracker.log_event(
        uuid,
        "SYS",
        "STEP1",
        1,
        result.error_code,
        result.description
    )

    tracker.finish_stage(
        uuid,
        "SYS",
        "STEP1",
        result.state,
        result.error_type,
        result.description
    )

    tx = session.query(tracker.TxProcess).first()
    assert tx.state == TransactionState.COMPLETED

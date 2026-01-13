"""Complex integration test.

- 3 transactions
- 3 platforms (A, B, C)
- retries and business/system errors
- final console report
"""
from datetime import datetime, timedelta
import logging

from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.enums import TransactionState
from rpa_tracker.reporting.transaction_report_repository import (
    TransactionReportRepository,
)

from test.domain.cancel_payload import CancelacionPayload
from test.tracking.fake_deduplication import CancelacionDeduplication
from test.infra.models.data_repository import DataRepository

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_complex_transaction_flow_with_retries_and_report(session):
    """Complex end-to-end flow with retries and final report."""
    # --- Setup ---
    data_repo = DataRepository(session)
    dedup = CancelacionDeduplication(data_repo)
    DeduplicationRegistry.register("COMPLEX_PROC", dedup)

    tracker = SqlTransactionTracker(session)

    # --- Payloads ---
    payloads = [
        CancelacionPayload(
            requerimiento="FE-0001",
            tipo_operacion="ALTA",
            nombre="TX_FAIL_A",
        ),
        CancelacionPayload(
            requerimiento="FE-0002",
            tipo_operacion="ALTA",
            nombre="TX_RETRY_B",
        ),
        CancelacionPayload(
            requerimiento="FE-0003",
            tipo_operacion="ALTA",
            nombre="TX_OK_ALL",
        ),
    ]

    uuids = []

    # --- Register transactions and stages ---
    for payload in payloads:
        uuid, _ = tracker.start_or_resume("COMPLEX_PROC", payload)
        uuids.append(uuid)

        tracker.start_stage(uuid, "A")
        tracker.start_stage(uuid, "B")
        tracker.start_stage(uuid, "C")

    # =========================================================
    # Platform A
    # =========================================================
    pending_a = tracker.get_pending_stages("A")
    assert len(pending_a) == 3

    for stage in pending_a:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-0001":
            result = ExecutionResult(error_code=3)      # business error
        else:
            result = ExecutionResult(error_code=0)      # OK

        tracker.log_event(stage.uuid, "A", result.error_code, result.description)
        tracker.finish_stage(
            stage.uuid,
            "A",
            result.state,
            result.error_type,
            result.description,
        )

    # =========================================================
    # Platform B
    # =========================================================
    pending_b = tracker.get_pending_stages("B")
    assert len(pending_b) == 2  # TX_FAIL_A must not be here

    for stage in pending_b:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-0002":
            # retry 1 → system error
            result1 = ExecutionResult(error_code=-2)
            tracker.log_event(stage.uuid, "B", result1.error_code, result1.description)
            tracker.finish_stage(
                stage.uuid,
                "B",
                result1.state,
                result1.error_type,
                result1.description,
            )

            # retry 2 → business error
            result2 = ExecutionResult(error_code=1)
            tracker.log_event(stage.uuid, "B", result2.error_code, result2.description)
            tracker.finish_stage(
                stage.uuid,
                "B",
                result2.state,
                result2.error_type,
                result2.description,
            )

        else:
            # TX_OK_ALL
            result = ExecutionResult(error_code=0)
            tracker.log_event(stage.uuid, "B", result.error_code, result.description)
            tracker.finish_stage(
                stage.uuid,
                "B",
                result.state,
                result.error_type,
                result.description,
            )

    # =========================================================
    # Platform C
    # =========================================================
    pending_c = tracker.get_pending_stages("C")
    assert len(pending_c) == 1  # only TX_OK_ALL

    stage = pending_c[0]
    result = ExecutionResult(error_code=0)
    tracker.log_event(stage.uuid, "C", result.error_code, result.description)
    tracker.finish_stage(
        stage.uuid,
        "C",
        result.state,
        result.error_type,
        result.description,
    )

    # =========================================================
    # REPORT
    # =========================================================
    repo = TransactionReportRepository(session)

    end = datetime.now()
    start = end - timedelta(days=1)

    txs = repo.transactions_between(start, end)
    summary = repo.summary_by_state(start, end)
    stage_summary = repo.stage_summary_by_system(start, end)

    log.info("=" * 70)
    log.info("FINAL TRANSACTION REPORT")
    log.info("Total transactions: %s", len(txs))

    log.info("SUMMARY BY STATE")
    for state, count in summary:
        log.info("  %-10s : %s", state, count)

    log.info("SUMMARY BY SYSTEM / STATE")
    for system, state, count in stage_summary:
        log.info("  SYSTEM=%s | STATE=%s | COUNT=%s", system, state, count)

    log.info("=" * 70)

    # =========================================================
    # ASSERTIONS
    # =========================================================
    states = {tx.uuid: tx.state for tx in txs}

    assert states[uuids[0]] == TransactionState.REJECTED      # FE-0001
    assert states[uuids[1]] == TransactionState.REJECTED      # FE-0002
    assert states[uuids[2]] == TransactionState.COMPLETED     # FE-0003

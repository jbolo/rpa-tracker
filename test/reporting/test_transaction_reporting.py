"""Tests for transaction reporting in RPA Tracker."""
from datetime import datetime, timedelta
import logging

from rpa_tracker.reporting.transaction_report_repository import (
    TransactionReportRepository,
)
from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.enums import TransactionState

from test.domain.cancel_payload import CancelacionPayload
from test.infra.models.data_repository import DataRepository
from test.tracking.fake_deduplication import CancelacionDeduplication

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_transaction_reporting_console(session):
    """Test transaction reporting functionality with console output."""
    # --- Setup ---
    data_repo = DataRepository(session)
    dedup = CancelacionDeduplication(data_repo)
    DeduplicationRegistry.register("REPORT_PROC", dedup)

    tracker = SqlTransactionTracker(session)

    # --- Create transactions ---
    cases = [
        ("FE-1001", "ALTA", "Tx OK 1", 0),
        ("FE-1002", "BAJA", "Tx REJECTED", 100),
        ("FE-1003", "CAPL", "Tx OK 2", 0),
    ]

    for req, tipo, nombre, error_code in cases:
        payload = CancelacionPayload(
            requerimiento=req,
            tipo_operacion=tipo,
            nombre=nombre,
        )

        uuid, _ = tracker.start_or_resume("REPORT_PROC", payload)
        tracker.start_stage(uuid, "A")

        result = ExecutionResult(error_code=error_code)

        tracker.log_event(uuid, "A", result.error_code, result.description)
        tracker.finish_stage(
            uuid,
            "A",
            result.state,
            result.error_type,
            result.description,
        )

    # --- Reporting window ---
    end = datetime.now()
    start = end - timedelta(days=5)

    repo = TransactionReportRepository(session)

    txs = repo.transactions_between(start, end)
    summary = repo.summary_by_state(start, end)
    stage_summary = repo.stage_summary_by_system(start, end)

    # --- Console output ---
    log.info("=" * 60)
    log.info("TRANSACTION REPORT (last 5 days)")
    log.info("From: %s", start)
    log.info("To  : %s", end)
    log.info("-" * 60)

    log.info("Total transactions: %s", len(txs))

    log.info("SUMMARY BY STATE")
    for state, count in summary:
        log.info("  %-10s : %s", state, count)

    log.info("-" * 60)
    log.info("STAGE SUMMARY BY SYSTEM")
    for system, state, count in stage_summary:
        log.info("  SYSTEM=%s | STATE=%s | COUNT=%s", system, state, count)

    log.info("=" * 60)

    # --- Minimal assertions ---
    assert len(txs) == 3
    assert dict(summary)[TransactionState.COMPLETED] == 2
    assert dict(summary)[TransactionState.REJECTED] == 1

"""Complex integration test.

- 3 transactions
- 3 platforms (A, B, C)
- retries and business/system errors
- final console report
"""
from datetime import datetime, timedelta
import logging

from rpa_tracker.catalog.platform import PlatformDefinition
from rpa_tracker.catalog.registry import PlatformRegistry
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

from rpa_tracker.retry.policy import RetryPolicy

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_complex_transaction_flow_with_platform_retry_and_report(session):
    """Complex end-to-end flow with retries and final report."""
    # =========================================================
    # BOOTSTRAP
    # =========================================================
    data_repo = DataRepository(session)

    DeduplicationRegistry.register(
        "COMPLEX_PROC",
        CancelacionDeduplication(data_repo),
    )

    PlatformRegistry.register(
        PlatformDefinition(
            code="A",
            retry_policy=RetryPolicy(max_attempts=1),
            order=1,
        )
    )

    PlatformRegistry.register(
        PlatformDefinition(
            code="B",
            retry_policy=RetryPolicy(max_attempts=2),
            order=2,
        )
    )

    PlatformRegistry.register(
        PlatformDefinition(
            code="C",
            retry_policy=RetryPolicy(),  # unlimited
            order=3,
        )
    )

    tracker = SqlTransactionTracker(session)

    # =========================================================
    # TRANSACTIONS
    # =========================================================
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

    for payload in payloads:
        uuid, is_new = tracker.start_or_resume("COMPLEX_PROC", payload)
        assert is_new
        uuids.append(uuid)

        # Register stages using catalog
        for platform in PlatformRegistry.all():
            tracker.start_stage(uuid, platform.code)

    # =========================================================
    # PLATFORM A
    # =========================================================
    platform = PlatformRegistry.get("A")
    pending_a = tracker.get_pending_stages(platform.code)
    assert len(pending_a) == 3

    for stage in pending_a:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-0001":
            result = ExecutionResult(error_code=3)   # business error
        else:
            result = ExecutionResult(error_code=0)   # OK

        tracker.log_event(stage.uuid, platform.code, result.error_code, result.description)
        tracker.finish_stage(
            stage.uuid,
            platform.code,
            result.state,
            result.error_type,
            result.description,
        )

    # =========================================================
    # PLATFORM B
    # =========================================================
    platform = PlatformRegistry.get("B")
    pending_b = tracker.get_pending_stages(platform.code)
    assert len(pending_b) == 2  # TX_FAIL_A is excluded

    for stage in pending_b:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-0002":
            # attempt 1 -> system error (retry allowed)
            result1 = ExecutionResult(error_code=-2)
            tracker.log_event(stage.uuid, platform.code, result1.error_code, result1.description)
            tracker.finish_stage(
                stage.uuid,
                platform.code,
                result1.state,
                result1.error_type,
                result1.description,
            )

            # attempt 2 -> business error (retry limit reached)
            result2 = ExecutionResult(error_code=1)
            tracker.log_event(stage.uuid, platform.code, result2.error_code, result2.description)
            tracker.finish_stage(
                stage.uuid,
                platform.code,
                result2.state,
                result2.error_type,
                result2.description,
            )

        else:
            # TX_OK_ALL
            result = ExecutionResult(error_code=0)
            tracker.log_event(stage.uuid, platform.code, result.error_code, result.description)
            tracker.finish_stage(
                stage.uuid,
                platform.code,
                result.state,
                result.error_type,
                result.description,
            )

    # =========================================================
    # PLATFORM C
    # =========================================================
    platform = PlatformRegistry.get("C")
    pending_c = tracker.get_pending_stages(platform.code)
    assert len(pending_c) == 1  # only TX_OK_ALL

    stage = pending_c[0]
    result = ExecutionResult(error_code=0)
    tracker.log_event(stage.uuid, platform.code, result.error_code, result.description)
    tracker.finish_stage(
        stage.uuid,
        platform.code,
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

    log.info("SUMMARY BY PLATFORM / STATE")
    for system, state, count in stage_summary:
        log.info("  SYSTEM=%s | STATE=%s | COUNT=%s", system, state, count)

    log.info("=" * 70)

    # =========================================================
    # ASSERTIONS
    # =========================================================
    states = {tx.uuid: tx.state for tx in txs}

    assert states[uuids[0]] == TransactionState.REJECTED     # FE-0001
    assert states[uuids[1]] == TransactionState.REJECTED     # FE-0002
    assert states[uuids[2]] == TransactionState.COMPLETED    # FE-0003

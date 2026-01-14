"""Complex integration test.

- 3 transactions
- 3 platforms (A, B, C) with multiple stages
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
    # BOOTSTRAP - Define platforms with stages
    # =========================================================
    data_repo = DataRepository(session)

    DeduplicationRegistry.register(
        "COMPLEX_PROC",
        CancelacionDeduplication(data_repo),
    )

    # Platform A: Single stage "validar"
    PlatformRegistry.register(
        PlatformDefinition(
            code="A",
            stages=("validar",),
            retry_policy=RetryPolicy(max_attempts=1),
            order=1,
        )
    )

    # Platform B: Two stages "procesar" and "confirmar"
    PlatformRegistry.register(
        PlatformDefinition(
            code="B",
            stages=("procesar", "confirmar"),
            retry_policy=RetryPolicy(max_attempts=2),
            order=2,
        )
    )

    # Platform C: Default stage (no stages specified)
    PlatformRegistry.register(
        PlatformDefinition(
            code="C",
            retry_policy=RetryPolicy(),  # unlimited
            order=3,
        )
    )

    tracker = SqlTransactionTracker(session)

    # =========================================================
    # TRANSACTIONS - Create and register all stages
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

        # Register all stages for all platforms
        for platform in PlatformRegistry.all():
            for stage_name in platform.stages:
                tracker.start_stage(uuid, platform.code, stage=stage_name)

    # =========================================================
    # PLATFORM A - Stage: "validar"
    # =========================================================
    platform = PlatformRegistry.get("A")
    stage_name = platform.stages[0]  # "validar"

    pending_a = tracker.get_pending_stages(platform.code, stage=stage_name)
    assert len(pending_a) == 3

    log.info("=" * 70)
    log.info("PROCESSING PLATFORM A - Stage: %s", stage_name)

    for stage in pending_a:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-0001":
            result = ExecutionResult(error_code=3)   # business error
            log.info("  [%s] %s -> BUSINESS ERROR (code=3)", stage_name, data.nombre)
        else:
            result = ExecutionResult(error_code=0)   # OK
            log.info("  [%s] %s -> SUCCESS", stage_name, data.nombre)

        tracker.log_event(
            stage.uuid,
            platform.code,
            result.error_code,
            result.description,
            stage=stage_name
        )
        tracker.finish_stage(
            stage.uuid,
            platform.code,
            result.state,
            result.error_type,
            result.description,
            stage=stage_name,
        )

        session.commit()

    # =========================================================
    # PLATFORM B - Stage 1: "procesar"
    # =========================================================
    platform = PlatformRegistry.get("B")
    stage_name = platform.stages[0]  # "procesar"

    pending_b_proc = tracker.get_pending_stages(platform.code, stage=stage_name)
    assert len(pending_b_proc) == 2  # TX_FAIL_A is excluded

    log.info("=" * 70)
    log.info("PROCESSING PLATFORM B - Stage: %s", stage_name)

    for stage in pending_b_proc:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-0002":
            # attempt 1 -> system error (retry allowed)
            result1 = ExecutionResult(error_code=-2)
            log.info("  [%s] %s -> SYSTEM ERROR attempt 1 (retry)", stage_name, data.nombre)
            tracker.log_event(
                stage.uuid,
                platform.code,
                result1.error_code,
                result1.description,
                stage=stage_name
            )
            tracker.finish_stage(
                stage.uuid,
                platform.code,
                result1.state,
                result1.error_type,
                result1.description,
                stage=stage_name,
            )

            session.commit()

            # attempt 2 -> business error (retry limit reached)
            result2 = ExecutionResult(error_code=1)
            log.info("  [%s] %s -> BUSINESS ERROR attempt 2 (rejected)", stage_name, data.nombre)
            tracker.log_event(
                stage.uuid,
                platform.code,
                result2.error_code,
                result2.description,
                stage=stage_name
            )
            tracker.finish_stage(
                stage.uuid,
                platform.code,
                result2.state,
                result2.error_type,
                result2.description,
                stage=stage_name,
            )

            session.commit()

        else:
            # TX_OK_ALL
            result = ExecutionResult(error_code=0)
            log.info("  [%s] %s -> SUCCESS", stage_name, data.nombre)
            tracker.log_event(
                stage.uuid,
                platform.code,
                result.error_code,
                result.description,
                stage=stage_name
            )
            tracker.finish_stage(
                stage.uuid,
                platform.code,
                result.state,
                result.error_type,
                result.description,
                stage=stage_name,
            )

            session.commit()

    # =========================================================
    # PLATFORM B - Stage 2: "confirmar"
    # =========================================================
    stage_name = platform.stages[1]  # "confirmar"

    pending_b_conf = tracker.get_pending_stages(platform.code, stage=stage_name)
    assert len(pending_b_conf) == 1  # Only TX_OK_ALL (FE-0002 was rejected)

    log.info("=" * 70)
    log.info("PROCESSING PLATFORM B - Stage: %s", stage_name)

    for stage in pending_b_conf:
        data = data_repo.get_by_uuid(stage.uuid)

        result = ExecutionResult(error_code=0)
        log.info("  [%s] %s -> SUCCESS", stage_name, data.nombre)

        tracker.log_event(
            stage.uuid,
            platform.code,
            result.error_code,
            result.description,
            stage=stage_name
        )
        tracker.finish_stage(
            stage.uuid,
            platform.code,
            result.state,
            result.error_type,
            result.description,
            stage=stage_name,
        )

        session.commit()

    # =========================================================
    # PLATFORM C - Default stage
    # =========================================================
    platform = PlatformRegistry.get("C")
    stage_name = platform.stages[0]  # "default"

    pending_c = tracker.get_pending_stages(platform.code, stage=stage_name)
    assert len(pending_c) == 1  # only TX_OK_ALL

    log.info("=" * 70)
    log.info("PROCESSING PLATFORM C - Stage: %s", stage_name)

    stage = pending_c[0]
    data = data_repo.get_by_uuid(stage.uuid)

    result = ExecutionResult(error_code=0)
    log.info("  [%s] %s -> SUCCESS", stage_name, data.nombre)

    tracker.log_event(
        stage.uuid,
        platform.code,
        result.error_code,
        result.description,
        stage=stage_name
    )
    tracker.finish_stage(
        stage.uuid,
        platform.code,
        result.state,
        result.error_type,
        result.description,
        stage=stage_name,
    )

    session.commit()

    # =========================================================
    # REPORT
    # =========================================================
    repo = TransactionReportRepository(session)

    end = datetime.now()
    start = end - timedelta(days=1)

    txs = repo.transactions_between(start, end)
    summary = repo.summary_by_state(start, end)
    stage_summary = repo.stage_summary_by_system(start, end)
    stage_detail = repo.stage_summary_by_system_and_stage(start, end)

    log.info("=" * 70)
    log.info("FINAL TRANSACTION REPORT")
    log.info("Total transactions: %s", len(txs))

    log.info("\nSUMMARY BY STATE")
    for state, count in summary:  # 👈 Ya está correcto (tuplas)
        log.info("  %-15s : %s", state, count)

    log.info("\nSUMMARY BY PLATFORM / STATE")
    for system, state, count in stage_summary:
        log.info("  SYSTEM=%-5s | STATE=%-15s | COUNT=%s", system, state, count)

    log.info("\nDETAILED SUMMARY BY PLATFORM / STAGE / STATE")
    for system, stage, state, count in stage_detail:
        log.info("  SYSTEM=%-5s | STAGE=%-15s | STATE=%-15s | COUNT=%s",
                 system, stage, state, count)

    log.info("=" * 70)

    # =========================================================
    # ASSERTIONS
    # =========================================================
    states = {tx.uuid: tx.state for tx in txs}

    assert states[uuids[0]] == TransactionState.REJECTED     # FE-0001 (failed at A.validar)
    assert states[uuids[1]] == TransactionState.REJECTED     # FE-0002 (failed at B.procesar)
    assert states[uuids[2]] == TransactionState.COMPLETED    # FE-0003 (completed all stages)

    # Verify stage counts
    summary_dict = {state: count for state, count in summary}  # Convertir a dict
    assert summary_dict["REJECTED"] == 2  # 👈 String directo
    assert summary_dict["COMPLETED"] == 1  # 👈 String directo

    log.info("\n✅ All assertions passed!")

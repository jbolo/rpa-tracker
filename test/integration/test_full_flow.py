"""Integration test for full transaction flow in RPA tracker."""
from rpa_tracker.models.tx_process import TxProcess
from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker
from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.catalog.registry import PlatformRegistry  # 👈 Agregar
from rpa_tracker.catalog.platform import PlatformDefinition  # 👈 Agregar
from rpa_tracker.retry.policy import RetryPolicy  # 👈 Agregar
from rpa_tracker.enums import TransactionState

from test.infra.models.data_repository import DataRepository
from test.tracking.fake_deduplication import CancelacionDeduplication
from test.domain.cancel_payload import CancelacionPayload
from sqlalchemy.orm import Session

import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_full_transaction_flow(session: Session):
    """Full end-to-end flow.

    - two transactions
    - three platforms
    - one rejected in A
    - only one reaches B and C
    """
    # =========================================================
    # BOOTSTRAP - Setup platforms and deduplication
    # =========================================================
    data_repo = DataRepository(session)
    dedup = CancelacionDeduplication(data_repo)
    DeduplicationRegistry.register("CANC_PROC", dedup)

    # 👇 Register platforms with order
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
            retry_policy=RetryPolicy(max_attempts=1),
            order=2,
        )
    )

    PlatformRegistry.register(
        PlatformDefinition(
            code="C",
            retry_policy=RetryPolicy(max_attempts=1),
            order=3,
        )
    )

    tracker = SqlTransactionTracker(session)

    # =========================================================
    # TRANSACTIONS - Create two transactions
    # =========================================================

    # --- Transaction 1 (will be REJECTED in A) ---
    payload_1 = CancelacionPayload(
        requerimiento="FE-4872673",
        tipo_operacion="ALTA",
        nombre="Jonathan Bolo",
    )

    uuid_1, is_new_1 = tracker.start_or_resume("CANC_PROC", payload_1)
    assert is_new_1
    log.info("Created transaction 1: %s (will fail in A)", uuid_1)

    # --- Transaction 2 (will COMPLETE) ---
    payload_2 = CancelacionPayload(
        requerimiento="FE-567567",
        tipo_operacion="CAPL",
        nombre="Global Bolo",
    )

    uuid_2, is_new_2 = tracker.start_or_resume("CANC_PROC", payload_2)
    assert is_new_2
    log.info("Created transaction 2: %s (will complete)", uuid_2)

    # --- Register platforms (stages) ---
    for uuid in (uuid_1, uuid_2):
        tracker.start_stage(uuid, "A")
        tracker.start_stage(uuid, "B")
        tracker.start_stage(uuid, "C")

    session.commit()  # 👈 Commit después de crear transacciones

    # =========================================================
    # PLATFORM A - Execute
    # =========================================================
    log.info("=" * 70)
    log.info("PROCESSING PLATFORM A")

    pending_a = tracker.get_pending_stages("A")
    assert len(pending_a) == 2

    for stage in pending_a:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-4872673":
            result = ExecutionResult(error_code=100)  # business error
            log.info("  [A] %s -> REJECTED (business error)", data.nombre)
        else:
            result = ExecutionResult(error_code=0)
            log.info("  [A] %s -> SUCCESS", data.nombre)

        tracker.log_event(
            stage.uuid,
            "A",
            result.error_code,
            result.description,
        )

        tracker.finish_stage(
            stage.uuid,
            "A",
            result.state,
            result.error_type,
            result.description,
        )

    session.commit()  # 👈 Commit después de Platform A

    # =========================================================
    # PLATFORM B - Execute
    # =========================================================
    log.info("=" * 70)
    log.info("PROCESSING PLATFORM B")

    pending_b = tracker.get_pending_stages("B")

    # 👇 Solo uuid_2 (uuid_1 fue rechazado en A)
    assert len(pending_b) == 1
    assert pending_b[0].uuid == uuid_2
    log.info("  Pending: 1 transaction (uuid_1 excluded due to A rejection)")

    for stage in pending_b:
        data = data_repo.get_by_uuid(stage.uuid)

        result = ExecutionResult(error_code=0)  # 👈 Procesar B
        log.info("  [B] %s -> SUCCESS", data.nombre)

        tracker.log_event(
            stage.uuid,
            "B",
            result.error_code,
            result.description,
        )

        tracker.finish_stage(
            stage.uuid,
            "B",
            result.state,
            result.error_type,
            result.description,
        )

    session.commit()  # 👈 Commit después de Platform B

    # =========================================================
    # PLATFORM C - Execute
    # =========================================================
    log.info("=" * 70)
    log.info("PROCESSING PLATFORM C")

    pending_c = tracker.get_pending_stages("C")

    # 👇 Solo uuid_2 (uuid_1 fue rechazado en A)
    assert len(pending_c) == 1
    assert pending_c[0].uuid == uuid_2
    log.info("  Pending: 1 transaction (uuid_1 excluded due to A rejection)")

    for stage in pending_c:
        data = data_repo.get_by_uuid(stage.uuid)

        result = ExecutionResult(error_code=0)  # 👈 Procesar C
        log.info("  [C] %s -> SUCCESS", data.nombre)

        tracker.log_event(
            stage.uuid,
            "C",
            result.error_code,
            result.description,
        )

        tracker.finish_stage(
            stage.uuid,
            "C",
            result.state,
            result.error_type,
            result.description,
        )

    session.commit()  # 👈 Commit final

    # =========================================================
    # ASSERTIONS - Final global state check
    # =========================================================
    log.info("=" * 70)
    log.info("FINAL STATE VERIFICATION")

    txs = session.query(TxProcess).all()
    states = {tx.uuid: tx.state for tx in txs}

    # 👇 uuid_1 rechazado en A
    assert states[uuid_1] == TransactionState.REJECTED.value
    log.info("  Transaction 1: %s", TransactionState.REJECTED.value)

    # 👇 uuid_2 completado (pasó A, B, C)
    assert states[uuid_2] == TransactionState.COMPLETED.value  # 👈 COMPLETED, no IN_PROGRESS
    log.info("  Transaction 2: %s", TransactionState.COMPLETED.value)

    log.info("\n✅ All assertions passed!")

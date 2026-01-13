"""Integration test for full transaction flow in RPA tracker."""
from rpa_tracker.models.tx_process import TxProcess
from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker
from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
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
    # --- Infra / process setup ---
    data_repo = DataRepository(session)
    dedup = CancelacionDeduplication(data_repo)
    DeduplicationRegistry.register("CANC_PROC", dedup)

    tracker = SqlTransactionTracker(session)

    # --- Transaction 1 (will be REJECTED in A) ---
    payload_1 = CancelacionPayload(
        requerimiento="FE-4872673",
        tipo_operacion="ALTA",
        nombre="Jonathan Bolo",
    )

    uuid_1, is_new_1 = tracker.start_or_resume("CANC_PROC", payload_1)
    assert is_new_1

    # --- Transaction 2 (will COMPLETE) ---
    payload_2 = CancelacionPayload(
        requerimiento="FE-567567",
        tipo_operacion="CAPL",
        nombre="Global Bolo",
    )

    uuid_2, is_new_2 = tracker.start_or_resume("CANC_PROC", payload_2)
    assert is_new_2

    # --- Register platforms (stages) ---
    for uuid in (uuid_1, uuid_2):
        tracker.start_stage(uuid, "A")
        tracker.start_stage(uuid, "B")
        tracker.start_stage(uuid, "C")

    # --- Execute platform A ---
    pending_a = tracker.get_pending_stages("A")
    assert len(pending_a) == 2

    for stage in pending_a:
        data = data_repo.get_by_uuid(stage.uuid)

        if data.requerimiento == "FE-4872673":
            result = ExecutionResult(error_code=100)  # business error
        else:
            result = ExecutionResult(error_code=0)

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

    # --- Platform B ---
    pending_b = tracker.get_pending_stages("B")
    assert len(pending_b) == 1
    assert pending_b[0].uuid == uuid_2

    # --- Platform C ---
    pending_c = tracker.get_pending_stages("C")
    assert len(pending_c) == 1
    assert pending_c[0].uuid == uuid_2

    # --- Final global state check ---
    txs = session.query(TxProcess).all()
    states = {tx.uuid: tx.state for tx in txs}

    assert states[uuid_1] == TransactionState.REJECTED
    assert states[uuid_2] == TransactionState.COMPLETED

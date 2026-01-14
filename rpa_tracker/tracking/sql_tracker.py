"""SQL-based implementation of the TransactionTracker."""
import uuid
from typing import Any, Optional, Tuple
from sqlalchemy.orm import Session
from rpa_tracker.enums import TransactionState
from rpa_tracker.models.tx_event import TxEvent
from rpa_tracker.models.tx_process import TxProcess
from rpa_tracker.models.tx_stage import TxStage
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry
from rpa_tracker.tracking.transaction_tracker import TransactionTracker
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from rpa_tracker.constants import DEFAULT_STAGE
from rpa_tracker.retry.registry import RetryPolicyRegistry


class SqlTransactionTracker(TransactionTracker):

    def __init__(self, session: Session):
        self.session = session

    def start_or_resume(self, process_code: str, payload: Any) -> Tuple[str, bool]:
        """Returns (uuid, is_new_transaction)."""
        dedup = DeduplicationRegistry.get(process_code)
        fingerprint = dedup.calculate_fingerprint(payload)

        existing = dedup.find_existing_uuid(fingerprint)
        if existing:
            return existing, False

        uuid_tx = str(uuid.uuid4())
        self.session.add(
            TxProcess(
                uuid=uuid_tx,
                process_code=process_code,
                state=TransactionState.PENDING,
                created_at=datetime.now()
            )
        )

        try:
            dedup.persist_data(uuid_tx, payload)
            self.session.commit()
            return uuid_tx, True
        except IntegrityError:
            self.session.rollback()
            return dedup.find_existing_uuid(fingerprint), False

    def start_stage(self, uuid: str, system: str, stage: Optional[str] = None) -> None:
        """Registers the start of a stage for a transaction."""
        stage = stage or DEFAULT_STAGE
        existing = (
            self.session.query(TxStage)
            .filter_by(uuid=uuid, system=system, stage=stage)
            .first()
        )

        if existing:
            return

        self.session.add(
            TxStage(
                uuid=uuid,
                system=system,
                stage=stage,
                state=TransactionState.PENDING,
                attempt=0,
                last_attempt_at=None,
                error_type=None,
                error_description=None,
            )
        )
        self.session.commit()

    def log_event(
        self,
        uuid: str,
        system: str,
        error_code: int,
        description: Optional[str],
        stage: Optional[str] = None
    ):
        """Logs an event for a transaction stage."""
        stage = stage or DEFAULT_STAGE
        stage_row = (
            self.session.query(TxStage)
            .filter_by(uuid=uuid, system=system, stage=stage)
            .one()
        )

        attempt = stage_row.attempt + 1

        self.session.add(
            TxEvent(
                uuid=uuid,
                system=system,
                stage=stage,
                attempt=attempt,
                error_code=error_code,
                description=description,
                event_at=datetime.now(),
                processed_at=datetime.now(),
            )
        )

        self.session.commit()

    def finish_stage(
        self,
        uuid: str,
        system: str,
        state: str,
        error_type: Optional[str],
        description: Optional[str],
        stage: Optional[str] = None
    ):
        """Marks a transaction stage as finished and updates global transaction state."""
        stage = stage or DEFAULT_STAGE
        stage_row = (
            self.session.query(TxStage)
            .filter_by(uuid=uuid, system=system, stage=stage)
            .one()
        )

        stage_row.state = state
        stage_row.error_type = error_type
        stage_row.error_description = description
        stage_row.attempt += 1
        stage_row.last_attempt_at = datetime.now()

        # 🔴 NUEVO: actualizar estado global del proceso
        process = (
            self.session.query(TxProcess)
            .filter_by(uuid=uuid)
            .one()
        )

        process.state = state
        process.updated_at = datetime.now()

        self.session.commit()

    def get_executable_stages(self, uuid: str) -> list[TxStage]:
        """Returns stages that can be executed (PENDING or REJECTED).

        Unless the transaction is already REJECTED.
        """
        process = self.session.query(TxProcess).filter_by(uuid=uuid).one()

        if process.state == TransactionState.REJECTED:
            return []

        return (
            self.session.query(TxStage)
            .filter(
                TxStage.uuid == uuid,
                TxStage.state.in_(
                    [TransactionState.PENDING, TransactionState.REJECTED]
                )
            )
            .all()
        )

    def get_pending_stages(self, system: str, stage: Optional[str] = None):
        """Returns stages that are eligible for execution for a given system.

        Only stages in PENDING or TERMINATED state are returned, and only if the parent transaction is not REJECTED.

        Args:
            system: Platform system code
            stage: Optional stage name to filter by specific stage
        """
        policy = RetryPolicyRegistry.get(system)
        query = (
            self.session.query(TxStage)
            .join(TxProcess, TxStage.uuid == TxProcess.uuid)
            .filter(
                TxStage.system == system,
                TxStage.state.in_(
                    [TransactionState.PENDING, TransactionState.TERMINATED]
                ),
                TxProcess.state != TransactionState.REJECTED,
            )
        )

        # 👇 NUEVO: Filtrar por stage si se proporciona
        if stage is not None:
            query = query.filter(TxStage.stage == stage)

        if policy.max_attempts is not None:
            query = query.filter(TxStage.attempt < policy.max_attempts)

        return query.all()

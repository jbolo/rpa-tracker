"""SQL-based implementation of the TransactionTracker."""
import uuid
from typing import Any, List, Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session
from rpa_tracker.catalog.registry import PlatformRegistry
from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.enums import TransactionState, ErrorType
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

    def start_or_resume(self,
                        process_code: str,
                        payload: Any) -> Tuple[str, bool]:
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
                state=TransactionState.PENDING.value,
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

    def start_stage(self,
                    uuid: str,
                    system: str,
                    stage: str = DEFAULT_STAGE) -> None:
        """Registers the start of a stage for a transaction."""
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
                state=TransactionState.PENDING.value,
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
        stage: str = DEFAULT_STAGE
    ) -> None:
        """Logs an event for a transaction stage."""
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
        state: TransactionState,
        error_type: Optional[ErrorType] = None,
        description: Optional[str] = None,
        stage: str = DEFAULT_STAGE
    ) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """Finish a stage and update process state accordingly.

        Logic:
        - COMPLETED stage -> Check if all stages completed -> Update process
        - REJECTED stage -> Update process to REJECTED (stop flow)
        - TERMINATED stage -> Update process to TERMINATED (retry later)
        """
        # Optimistic update: only update if still PENDING
        updated = (
            self.session.query(TxStage)
            .filter(
                TxStage.uuid == uuid,
                TxStage.system == system,
                TxStage.stage == stage,
                TxStage.state.in_([
                    TransactionState.PENDING.value,
                    TransactionState.TERMINATED.value
                ])
            )
            .update(
                {
                    "state": state.value,
                    "error_type": error_type.value if error_type else None,
                    "error_description": description,
                    "last_attempt_at": datetime.now(),
                    "attempt": TxStage.attempt + 1  # Increment attempt
                },
                synchronize_session=False
            )
        )

        if updated == 0:
            # Another worker already processed this stage
            # This is normal in concurrent scenarios, just skip
            return

        self._update_process_state(uuid, state, error_type, description)

        self.session.commit()

        return (state.value, error_type.value if error_type else None, description)

    def _update_process_state(
        self,
        uuid: str,
        stage_state: TransactionState,
        error_type: Optional[ErrorType],
        description: Optional[str],
    ) -> None:
        """Update process state based on stage completion."""
        process = (
            self.session.query(TxProcess)
            .filter_by(uuid=uuid)
            .with_for_update()
            .one())

        if stage_state == TransactionState.REJECTED:
            # Business error -> Stop process
            process.state = TransactionState.REJECTED.value
            process.error_type = error_type.value if error_type else None
            process.error_description = description

            # Cancel all pending stages
            self._cancel_pending_stages(uuid)

        elif stage_state == TransactionState.TERMINATED:
            # System error -> Mark for retry (only if not already rejected)
            if process.state != TransactionState.REJECTED.value:
                process.state = TransactionState.TERMINATED.value
                process.error_type = error_type.value if error_type else None
                process.error_description = description

        elif stage_state == TransactionState.COMPLETED:
            # Check if all stages are completed
            all_stages_completed = self._are_all_stages_completed(uuid)

            if all_stages_completed:
                # All stages completed -> Process completed
                process.state = TransactionState.COMPLETED.value
                process.error_type = None
                process.error_description = None
            else:
                # Still has pending stages -> Keep as IN_PROGRESS
                if process.state == TransactionState.PENDING.value:
                    process.state = TransactionState.IN_PROGRESS.value

    def _cancel_pending_stages(self, uuid: str) -> None:
        """Cancel all PENDING stages for a transaction.

        Uses optimistic update to avoid locking all stages.
        """
        # Update all PENDING stages to CANCELLED (atomic operation)
        updated_count = (
            self.session.query(TxStage)
            .filter(
                TxStage.uuid == uuid,
                TxStage.state == TransactionState.PENDING.value
            )
            .update(
                {
                    "state": TransactionState.CANCELLED.value,
                    "error_description": "Cancelled due to previous platform rejection"
                },
                synchronize_session=False
            )
        )

        return updated_count

    def _are_all_stages_completed(self, uuid: str) -> bool:
        """Check if all stages for a transaction are completed."""
        # Count pending stages
        pending_count = (
            self.session.query(func.count(TxStage.uuid))
            .filter(
                TxStage.uuid == uuid,
                TxStage.state.in_([
                    TransactionState.PENDING.value,
                    TransactionState.IN_PROGRESS.value,
                ])
            )
            .scalar()
        )

        return pending_count == 0

    def get_executable_stages(self, uuid: str) -> List[TxStage]:
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

    def get_pending_stages(self,
                           system: str,
                           stage: str = DEFAULT_STAGE) -> List[TxStage]:
        """Returns stages that are eligible for execution for a given system.

        Only returns stages where:
        1. Stage is PENDING
        2. Process is PENDING, IN_PROGRESS, or TERMINATED
        3. All previous platforms have completed successfully
        """
        policy = RetryPolicyRegistry.get(system)

        # Get platform order
        platform = PlatformRegistry.get(system)
        current_order = platform.order

        query = (
            self.session.query(TxStage)
            .join(TxProcess, TxStage.uuid == TxProcess.uuid)
            .filter(
                TxStage.system == system,
                TxStage.stage == stage,
                TxStage.state == TransactionState.PENDING.value,
                TxProcess.state.in_([
                    TransactionState.PENDING.value,
                    TransactionState.IN_PROGRESS.value,
                    TransactionState.TERMINATED.value,  # 👈 Include for retry
                ])
            )
        )

        if policy.max_attempts is not None:
            query = query.filter(TxStage.attempt < policy.max_attempts)

        pending_stages = query.all()

        # 👇 NUEVA LÓGICA: Filter by previous platforms completion
        eligible_stages = []

        for stage_obj in pending_stages:
            if self._are_previous_platforms_completed(stage_obj.uuid, current_order):
                eligible_stages.append(stage_obj)

        return eligible_stages

    def _are_previous_platforms_completed(self, uuid: str, current_order: int) -> bool:
        """Check if all platforms with lower order are completed for this transaction.

        A platform is considered "completed" if ALL its stages are COMPLETED.

        Args:
            uuid: Transaction UUID
            current_order: Order of current platform

        Returns:
            True if all previous platforms completed, False otherwise
        """
        if current_order == 1:
            # First platform, no previous platforms to check
            return True

        # First, check if process is REJECTED (should not continue)
        process = self.session.query(TxProcess).filter_by(uuid=uuid).first()
        if not process or process.state == TransactionState.REJECTED.value:
            return False

        # Get all platforms with lower order
        previous_platforms = [
            p for p in PlatformRegistry.all()
            if p.order < current_order
        ]

        for prev_platform in previous_platforms:
            # Count completed stages for this platform
            completed_count = (
                self.session.query(func.count(TxStage.uuid))
                .filter(
                    TxStage.uuid == uuid,
                    TxStage.system == prev_platform.code,
                    TxStage.state == TransactionState.COMPLETED.value
                )
                .scalar()
            )

            # All stages of the platform must be completed
            expected_stages = len(prev_platform.stages)

            if completed_count < expected_stages:
                # Not all stages completed for this platform
                return False

        return True

    def complete_stage(
        self,
        uuid: str,
        system: str,
        result: ExecutionResult,
        stage: str = DEFAULT_STAGE,
        auto_commit: bool = False
    ) -> Optional[Tuple[str, Optional[str], Optional[str]]]:
        """Complete a stage by logging event and finishing it.

        Convenience method that combines log_event + finish_stage.

        Args:
            uuid: Transaction UUID
            system: Platform code
            result: ExecutionResult with state, error_type, etc.
            stage: Stage name (default: "default")
            auto_commit: If True, commits automatically after finishing

        Example:
            result = ExecutionResult(error_code=0)
            tracker.complete_stage(uuid, "A", result, stage="validar")
            session.commit()  # Manual commit

            # Or with auto-commit:
            tracker.complete_stage(uuid, "A", result, auto_commit=True)
        """
        # Log event
        self.log_event(
            uuid=uuid,
            system=system,
            error_code=result.error_code,
            description=result.description,
            stage=stage,
        )

        # Finish stage
        ret = self.finish_stage(
            uuid=uuid,
            system=system,
            state=result.state,
            error_type=result.error_type,
            description=result.description,
            stage=stage,
        )

        # Optional auto-commit
        if auto_commit:
            self.session.commit()

        return ret

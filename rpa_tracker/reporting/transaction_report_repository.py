"""Repository for transaction reports."""
from datetime import datetime
from sqlalchemy import func
from sqlalchemy.orm import Session
from rpa_tracker.models.tx_process import TxProcess
from rpa_tracker.models.tx_stage import TxStage


class TransactionReportRepository:
    def __init__(self, session: Session):
        self.session = session

    def transactions_between(self, start: datetime, end: datetime):
        """Returns all transactions created in a time window."""
        return (
            self.session.query(TxProcess)
            .filter(
                TxProcess.created_at >= start,
                TxProcess.created_at <= end,
            )
            .all()
        )

    def summary_by_state(self, start: datetime, end: datetime):
        """Returns count of transactions grouped by state."""
        return (
            self.session.query(
                TxProcess.state,
                func.count(TxProcess.uuid),
            )
            .filter(
                TxProcess.created_at >= start,
                TxProcess.created_at <= end,
            )
            .group_by(TxProcess.state)
            .all()
        )

    def stage_summary_by_system(self, start: datetime, end: datetime):
        """Returns count of stages per system and state."""
        return (
            self.session.query(
                TxStage.system,
                TxStage.state,
                func.count(),
            )
            .join(TxProcess, TxProcess.uuid == TxStage.uuid)
            .filter(
                TxProcess.created_at >= start,
                TxProcess.created_at <= end,
            )
            .group_by(TxStage.system, TxStage.state)
            .all()
        )

    def stage_summary_by_system_and_stage(
        self,
        start: datetime,
        end: datetime,
    ) -> list[tuple[str, str, str, int]]:
        """Return summary of stages by system, stage name, and state.

        Returns:
            List of tuples: (system, stage, state, count)
        """
        return (
            self.session.query(
                TxStage.system,
                TxStage.stage,
                TxStage.state,
                func.count().label("count"),
            )
            .join(TxProcess, TxStage.uuid == TxProcess.uuid)
            .filter(
                TxProcess.created_at >= start,
                TxProcess.created_at <= end,
            )
            .group_by(TxStage.system, TxStage.stage, TxStage.state)
            .order_by(TxStage.system, TxStage.stage, TxStage.state)
            .all()
        )

"""Repository for transaction data management."""
from typing import Optional
from test.domain.cancel_payload import CancelacionPayload
from test.infra.models.tx_data import TxData
from sqlalchemy.orm import Session


class DataRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, uuid: str, payload: CancelacionPayload):
        """Save transaction data associated with a UUID."""
        self.session.add(
            TxData(
                uuid=uuid,
                requerimiento=payload.requerimiento,
                tipo_operacion=payload.tipo_operacion,
                nombre=payload.nombre,
            )
        )
        self.session.commit()

    def get_by_uuid(self, uuid: str) -> TxData:
        """Retrieve transaction data by UUID."""
        return (
            self.session.query(TxData)
            .filter_by(uuid=uuid)
            .one()
        )

    def find_by_requerimiento(self, requerimiento: str) -> Optional[TxData]:
        """Find transaction by requerimiento field."""
        return (
            self.session.query(TxData)
            .filter_by(requerimiento=requerimiento)
            .first()
        )

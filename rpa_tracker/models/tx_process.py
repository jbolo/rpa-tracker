"""SQLAlchemy model for transaction processes."""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class TxProcess(Base):
    __tablename__ = "RPA_TX_PROCESS"

    uuid = Column(String(36), primary_key=True)

    process_code = Column(String(50), nullable=False)

    state = Column(String(20), nullable=False)
    error_type = Column(String(20), nullable=True)
    error_description = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        """String representation of the TxProcess."""
        return (
            f"<TxProcess(uuid={self.uuid}, "
            f"process_code={self.process_code}, "
            f"state={self.state})>"
        )

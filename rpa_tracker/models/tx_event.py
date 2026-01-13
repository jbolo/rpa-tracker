"""SQLAlchemy model for transaction events."""
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class TxEvent(Base):
    __tablename__ = "RPA_TX_EVENT"

    id = Column(Integer, primary_key=True, autoincrement=True)

    uuid = Column(String(36), nullable=False)
    system = Column(String(50), nullable=False)
    stage = Column(String(50), nullable=False)

    attempt = Column(Integer, nullable=False)

    error_code = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)

    event_at = Column(DateTime, nullable=False, default=datetime.now)
    processed_at = Column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self):
        """String representation of the TxEvent."""
        return (
            f"<TxEvent(id={self.id}, "
            f"uuid={self.uuid}, "
            f"system={self.system}, "
            f"stage={self.stage}, "
            f"attempt={self.attempt}, "
            f"error_code={self.error_code})>"
        )

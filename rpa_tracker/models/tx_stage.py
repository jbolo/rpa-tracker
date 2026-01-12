"""SQLAlchemy model for transaction stages."""
from sqlalchemy import Column, String, DateTime, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TxStage(Base):
    __tablename__ = "RPA_TX_STAGE"

    uuid = Column(String(36), primary_key=True)
    system = Column(String(50), primary_key=True)
    stage = Column(String(50), primary_key=True)

    state = Column(String(20), nullable=False)

    attempt = Column(Integer, nullable=False, default=0)

    last_attempt_at = Column(DateTime, nullable=True)

    error_type = Column(String(20), nullable=True)
    error_description = Column(String(255), nullable=True)

    def __repr__(self):
        """String representation of the TxStage."""
        return (
            f"<TxStage(uuid={self.uuid}, "
            f"system={self.system}, "
            f"stage={self.stage}, "
            f"state={self.state}, "
            f"attempt={self.attempt})>"
        )

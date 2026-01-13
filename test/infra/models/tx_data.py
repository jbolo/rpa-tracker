"""SQLAlchemy model for RPA transaction data."""
from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TxData(Base):
    __tablename__ = "RPA_TX_DATA"

    uuid = Column(String(36), primary_key=True)
    requerimiento = Column(String(50), nullable=False)
    tipo_operacion = Column(String(20), nullable=False)
    nombre = Column(String(100), nullable=False)

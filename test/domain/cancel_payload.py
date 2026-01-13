"""Domain model for transaction payloads."""
from pydantic import BaseModel


class CancelacionPayload(BaseModel):
    requerimiento: str
    tipo_operacion: str
    nombre: str

"""Domain model for execution result representation."""
from pydantic import BaseModel, field_validator
from typing import Optional


class ExecutionResult(BaseModel):
    error_code: int
    description: Optional[str] = None

    state: str = None
    error_type: Optional[str] = None
    retryable: bool = None

    @field_validator("state", mode="before")
    @classmethod
    def resolve_state(cls, _, info):
        code = info.data["error_code"]
        if code == 0:
            return "COMPLETED"
        elif code > 0:
            return "REJECTED"
        return "FAILED"

    @field_validator("error_type", mode="before")
    @classmethod
    def resolve_error_type(cls, _, info):
        code = info.data["error_code"]
        if code > 0:
            return "BUSINESS"
        elif code < 0:
            return "SYSTEM"
        return None

    @field_validator("retryable", mode="before")
    @classmethod
    def resolve_retryable(cls, _, info):
        return info.data["error_code"] <= 0

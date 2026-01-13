"""Domain model for execution results in RPA tracker."""
from pydantic import BaseModel, model_validator
from typing import Optional

from rpa_tracker.enums import TransactionState, ErrorType


class ExecutionResult(BaseModel):
    error_code: int
    description: Optional[str] = None

    state: Optional[str] = None
    error_type: Optional[str] = None
    retryable: Optional[bool] = None

    @model_validator(mode="after")
    def compute_derived_fields(self):
        """Compute derived fields based on error_code."""
        if self.error_code == 0:
            self.state = TransactionState.COMPLETED
            self.error_type = None
            self.retryable = True

        elif self.error_code > 0:
            self.state = TransactionState.REJECTED
            self.error_type = ErrorType.BUSINESS
            self.retryable = False

        else:
            self.state = TransactionState.TERMINATED
            self.error_type = ErrorType.SYSTEM
            self.retryable = True

        return self

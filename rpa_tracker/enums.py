"""Enums for transaction states and error types in RPA tracking."""
from enum import Enum


class TransactionState(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"          # system error (retryable)
    REJECTED = "REJECTED"      # business error (non-retryable)
    IN_PROGRESS = "IN_PROGRESS"  # in progress
    CANCELLED = "CANCELLED"    # 👈 NUEVO: cancelled due to previous failure


class ErrorType(str, Enum):
    SYSTEM = "SYSTEM"
    BUSINESS = "BUSINESS"

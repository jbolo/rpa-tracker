"""Enums for transaction states and error types in RPA tracking."""


class TransactionState:
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"          # system error (retryable)
    REJECTED = "REJECTED"      # business error (non-retryable)


class ErrorType:
    SYSTEM = "SYSTEM"
    BUSINESS = "BUSINESS"

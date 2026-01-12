from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.enums import TransactionState, ErrorType


def test_execution_result_ok():
    r = ExecutionResult(error_code=0)
    assert r.state == TransactionState.COMPLETED
    assert r.error_type is None
    assert r.retryable is True


def test_execution_result_business_error():
    r = ExecutionResult(error_code=100)
    assert r.state == TransactionState.REJECTED
    assert r.error_type == ErrorType.BUSINESS
    assert r.retryable is False


def test_execution_result_system_error():
    r = ExecutionResult(error_code=-5)
    assert r.state == TransactionState.FAILED
    assert r.error_type == ErrorType.SYSTEM
    assert r.retryable is True

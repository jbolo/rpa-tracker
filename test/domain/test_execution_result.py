"""Unit tests for ExecutionResult in RPA tracker."""
from rpa_tracker.domain.execution_result import ExecutionResult
from rpa_tracker.enums import TransactionState, ErrorType
import logging

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def test_execution_result_ok():
    """Test ExecutionResult for successful execution."""
    r = ExecutionResult(error_code=0)
    log.info(r)
    assert r.state == TransactionState.COMPLETED
    assert r.error_type is None
    assert r.retryable is True


def test_execution_result_business_error():
    """Test ExecutionResult for business error."""
    r = ExecutionResult(error_code=100)
    assert r.state == TransactionState.REJECTED
    assert r.error_type == ErrorType.BUSINESS
    assert r.retryable is False


def test_execution_result_system_error():
    """Test ExecutionResult for system error."""
    r = ExecutionResult(error_code=-5)
    assert r.state == TransactionState.TERMINATED
    assert r.error_type == ErrorType.SYSTEM
    assert r.retryable is True


if __name__ == "__main__":
    test_execution_result_ok()
    # test_execution_result_business_error()
    # test_execution_result_system_error()

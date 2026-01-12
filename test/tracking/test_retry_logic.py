from rpa_tracker.domain.execution_result import ExecutionResult


def test_failed_stage_is_retryable():
    r = ExecutionResult(error_code=-1)
    assert r.retryable is True


def test_rejected_stage_is_not_retryable():
    r = ExecutionResult(error_code=10)
    assert r.retryable is False

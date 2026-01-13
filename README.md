# rpa-tracker

**rpa-tracker** is a lightweight Python library for transaction tracking, retry control, deduplication and auditability in RPA and backend automation workflows.

It is designed for long-running, multi-platform processes where:
- a single transaction touches multiple systems
- retries must be controlled and observable
- business errors must stop the flow
- system errors may be retried
- full traceability is required for operations and reporting

This library focuses on governance and execution control, not on orchestration engines or schedulers.

---

## Key Concepts

### Transaction
A logical unit of work identified by a UUID.  
A transaction may pass through multiple platforms and stages.

### Platform
A system involved in the transaction flow.  
Platforms are defined in a central catalog with execution order and retry policy.

### Stage
The execution of a transaction in a specific platform.

### Execution Result
Derived from an error code:
- `0` → success  
- `< 0` → system error (retryable)  
- `> 0` → business error (non-retryable)

---

## Core Features

- Transaction lifecycle tracking
- Platform-based execution flow
- Configurable retry policies per platform
- Unlimited or limited retries
- Business vs system error handling
- Deduplication strategies per process
- Full audit trail (events, attempts, timestamps)
- SQLAlchemy-based persistence
- Reporting-ready data model
- Designed for batch / hourly RPA execution

---

## Architecture Overview

```
Process / Job
   |
   |-- DeduplicationStrategy (process-specific)
   |-- PlatformRegistry (catalog)
   |-- RetryPolicy (per platform)
   |
   |-- SqlTransactionTracker
           |
           |-- TxProcess   (transaction)
           |-- TxStage     (platform execution)
           |-- TxEvent     (attempts / audit)
```

The tracker does not decide business rules.  
It only applies the configuration provided by the process.

---

## Installation

```bash
pip install rpa-tracker
```

---

## Basic Usage

### 1. Define Platforms and Retry Policies

```python
from rpa_tracker.catalog.platform import PlatformDefinition
from rpa_tracker.catalog.registry import PlatformRegistry
from rpa_tracker.retry.policy import RetryPolicy

PlatformRegistry.register(
    PlatformDefinition(
        code="A",
        retry_policy=RetryPolicy(max_attempts=1),
        order=1,
    )
)

PlatformRegistry.register(
    PlatformDefinition(
        code="B",
        retry_policy=RetryPolicy(max_attempts=2),
        order=2,
    )
)

PlatformRegistry.register(
    PlatformDefinition(
        code="C",
        retry_policy=RetryPolicy(),  # unlimited retries
        order=3,
    )
)
```

---

### 2. Register Deduplication Strategy

```python
from rpa_tracker.tracking.deduplication.registry import DeduplicationRegistry

DeduplicationRegistry.register(
    "MY_PROCESS",
    MyDeduplicationStrategy(...)
)
```

---

### 3. Start or Resume a Transaction

```python
tracker = SqlTransactionTracker(session)

uuid, is_new = tracker.start_or_resume(
    "MY_PROCESS",
    payload
)

if is_new:
    for platform in PlatformRegistry.all():
        tracker.start_stage(uuid, platform.code)
```

---

### 4. Hourly / Batch Execution per Platform

```python
from rpa_tracker.domain.execution_result import ExecutionResult

for platform in PlatformRegistry.all():
    pending = tracker.get_pending_stages(platform.code)

    for stage in pending:
        error_code = execute_platform(stage)
        result = ExecutionResult(error_code=error_code)

        tracker.log_event(
            stage.uuid,
            platform.code,
            result.error_code,
            result.description,
        )

        tracker.finish_stage(
            stage.uuid,
            platform.code,
            result.state,
            result.error_type,
            result.description,
        )
```

---

## Retry Behavior

- Business errors (`error_code > 0`)  
  → transaction is **REJECTED** and stops

- System errors (`error_code < 0`)  
  → stage is **TERMINATED** and retried based on policy

- Retry limits are platform-specific  
- Unlimited retries are supported  
- Exceeded retries simply stop appearing in pending queries

---

## Reporting

```python
from rpa_tracker.reporting.transaction_report_repository import (
    TransactionReportRepository
)

repo = TransactionReportRepository(session)

repo.transactions_between(start, end)
repo.summary_by_state(start, end)
repo.stage_summary_by_system(start, end)
```

Reporting output can be printed, exported to CSV,
or consumed by BI tools.

---

## Design Principles

- Explicit configuration over magic
- Process-driven policies
- No orchestration assumptions
- SQL-first, audit-friendly
- Conservative, production-oriented design

---

## When to Use rpa-tracker

- Multi-platform RPA processes
- Hourly or batch execution models
- Strong audit and traceability requirements
- Controlled retries and failure handling

## When NOT to Use It

- Real-time streaming systems
- Stateless microservices
- One-step scripts

---

## License

GNU General Public License v3 (GPLv3)

---

## Author

Jonathan Bolo  
Senior Software & RPA Architect

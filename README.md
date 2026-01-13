# rpa-tracker

![Python](https://img.shields.io/pypi/pyversions/rpa-tracker)
![PyPI](https://img.shields.io/pypi/v/rpa-tracker)
![License](https://img.shields.io/pypi/l/rpa-tracker)
![Status](https://img.shields.io/badge/status-stable-success)

**rpa-tracker** is a lightweight Python library for **transaction tracking, retry control, deduplication and auditability**
in RPA and backend automation workflows.

---

## Install

```bash
pip install rpa-tracker
```

---

## Why rpa-tracker?

It is designed for **long-running, multi-platform processes** where:

- a single transaction touches multiple systems
- retries must be controlled and observable
- business errors must stop the flow
- system errors may be retried
- full traceability is required for operations and reporting

This library focuses on **governance and execution control**, not orchestration engines or schedulers.

---

## Key Concepts

### Transaction
A logical unit of work identified by a UUID.

### Platform
A system involved in the transaction flow, defined in a central catalog
with execution order and retry policy.

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

The tracker does **not** decide business rules.  
It only applies the configuration provided by the process.

---

## Minimal Example

```python
from rpa_tracker.catalog.platform import PlatformDefinition
from rpa_tracker.catalog.registry import PlatformRegistry
from rpa_tracker.retry.policy import RetryPolicy
from rpa_tracker.tracking.sql_tracker import SqlTransactionTracker

PlatformRegistry.register(
    PlatformDefinition(code="A", retry_policy=RetryPolicy(max_attempts=1), order=1)
)

tracker = SqlTransactionTracker(session)
uuid, is_new = tracker.start_or_resume("MY_PROCESS", payload)
```

---

## Retry Behavior

- Business errors (`error_code > 0`)  
  → transaction is **REJECTED** and stops

- System errors (`error_code < 0`)  
  → stage is **TERMINATED** and retried based on policy

- Retry limits are **platform-specific**
- Unlimited retries are supported

---

## Reporting

```python
from rpa_tracker.reporting.transaction_report_repository import (
    TransactionReportRepository
)

repo = TransactionReportRepository(session)
repo.summary_by_state(start, end)
```

---

## Design Principles

- Explicit configuration over magic
- Process-driven policies
- No orchestration assumptions
- SQL-first, audit-friendly
- Conservative, production-oriented design

---

## When to Use

- Multi-platform RPA processes
- Hourly or batch execution models
- Strong audit and traceability requirements
- Controlled retries and failure handling

## When NOT to Use

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

---

[![JBoloDev](https://raw.githubusercontent.com/jbolo/rpa-tracker/refs/heads/master/ext/jbolodev.png)](https://jbolo.dev)
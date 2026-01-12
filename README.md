# rpa-tracker
RPA Tracker is a lightweight transaction tracking framework designed for Python-based RPA
and backend automation processes.

It provides:
- Transaction lifecycle tracking
- Step/stage state management
- Retry semantics (system vs business errors)
- Deduplication via pluggable strategies
- Append-only event logging for audit and troubleshooting

RPA Tracker is framework-agnostic and does not depend on any specific RPA tool.
It can be used with scrapers, API integrations, legacy system automation, or backend workflows.

Business data models remain outside the framework.
Only tracking and orchestration concerns live inside RPA Tracker.

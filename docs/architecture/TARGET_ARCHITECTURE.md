# Target architecture

Drive supplies immutable policy and release artifacts. Python loads policy, requests typed AI recommendations only when required, validates output with deterministic rules and readiness gates, requires human authorization where policy requires it, invokes adapters, performs readback, and records evidence in the authoritative system. SQLite holds only temporary retry, outbox, cache, lease, and pending-capture state.


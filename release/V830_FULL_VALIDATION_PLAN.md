# v8.3.0 Full Validation Plan

The exact candidate workflow must pass Ruff, strict MyPy, architecture/dev/legacy/documentation/dependency/vulnerability gates, the complete test suite with at least 85% branch coverage and zero skips, scoped secret scanning, independent PyPI and OSV audits, build-once source/wheel packaging, clean source/wheel installation, v8.2.1 restoration, v8.2.0 continuity, checksum verification, and retained artifact creation.

Event-specific gates cover raw-body webhook signatures, unsupported/malformed events, durable-before-ack acceptance, exact/semantic deduplication, leases, retry/backoff/dead letter, monitor-only zero writes, policy allow/approve/block behavior, approval expiry and precondition invalidation, Universal Inbox limits, backstop convergence, feedback-loop matching, snapshot re-read, readback/receipt behavior, operator kill switch, and rollback/W04 boundaries.

Production validation writes to GitHub candidate branches only. Notion and Todoist business-provider writes, webhook activation, production deployment, release publication, and authority activation must remain zero.
